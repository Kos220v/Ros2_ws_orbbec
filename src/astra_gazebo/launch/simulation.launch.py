#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
simulation.launch.py — ПОЛНАЯ проверка стека в Gazebo Harmonic БЕЗ реального
робота и без реальной камеры.

Поднимает ту же цепочку, что и на роботе, но источники — виртуальные:

    Gazebo (робот + Astra + лидар + GPS)
        │
        ├─ ros_gz_bridge  ─ camera/scan/gps/cmd_vel/clock ─┐
        │                                                  │
    robot_state_publisher (sim URDF) ─ TF датчиков         │
        │                                                  │
    rgbd_odometry (astra_odometry) ─ /odom (ВИЗУАЛЬНАЯ)    │
        │                                                  │
    relay_reliable ─ /scan -> /scan_reliable               │
    cmd_switcher   ─ приоритеты -> /cmd_vel ───────────────┘
        │
    localization (dual-EKF + navsat_transform) ─ map->odom->base_link
        │
    Nav2 (опционально) ─ /follow_gps_waypoints

Управление роботом (в отдельном терминале):
    ros2 run teleop_twist_keyboard teleop_twist_keyboard \\
        --ros-args -r /cmd_vel:=/cmd_vel/app_manual

Сравнение одометрии:
    /odom                  визуальная одометрия (RTAB-Map) — что проверяем
    /wheel/odometry        колёсная (Gazebo) — референс
    /ground_truth/odometry точная поза симулятора — эталон
    /odometry/local        выход локального EKF (VO)
    /odometry/global       выход глобального EKF (VO + GPS)

Аргументы:
    use_rviz        (true)  открыть RViz2
    use_navigation  (false) поднимать ли Nav2 (тяжёлый; для проверки VO не нужен)
    world           путь к SDF-миру
    x y z yaw       стартовая поза робота
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler, TimerAction)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_gz = get_package_share_directory('astra_gazebo')
    pkg_odom = get_package_share_directory('astra_odometry')
    pkg_nav = get_package_share_directory('robot_navigation')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    default_world = os.path.join(pkg_gz, 'worlds', 'outdoor.sdf')
    bridge_config = os.path.join(pkg_gz, 'config', 'bridge.yaml')
    xacro_file = os.path.join(pkg_gz, 'urdf', 'tracked_robot_sim.urdf.xacro')
    rviz_file = os.path.join(pkg_gz, 'rviz', 'simulation.rviz')

    use_rviz = LaunchConfiguration('use_rviz')
    use_navigation = LaunchConfiguration('use_navigation')
    odom_source = LaunchConfiguration('odom_source')
    world = LaunchConfiguration('world')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    z = LaunchConfiguration('z')
    yaw = LaunchConfiguration('yaw')

    # Камеру в URDF включаем ТОЛЬКО когда одометрия визуальная
    # (odom_source:=visual). В ground_truth тяжёлый RGB-D рендер не нужен и
    # только тормозит симуляцию -> Nav2 не успевает и цели отваливаются.
    enable_camera = PythonExpression(
        ["'true' if '", odom_source, "' == 'visual' else 'false'"])
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' enable_camera:=', enable_camera]),
        value_type=str)

    # 1. Gazebo Harmonic
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': [world, ' -r -v 3']}.items(),
    )

    # 2. robot_state_publisher (sim URDF, use_sim_time)
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description,
                     'use_sim_time': True}],
    )

    # 3. Спавн робота из /robot_description
    spawn = Node(
        package='ros_gz_sim', executable='create', name='spawn_robot',
        output='screen',
        arguments=['-topic', '/robot_description', '-name', 'tracked_robot',
                   '-x', x, '-y', y, '-z', z, '-Y', yaw],
    )

    # 4. Мост ros <-> gz
    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='ros_gz_bridge', output='screen',
        parameters=[{'config_file': bridge_config, 'use_sim_time': True}],
    )

    # 5. /scan -> /scan_reliable
    relay = Node(
        package='relay_reliable', executable='relay_node',
        name='relay_reliable', output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # 6. Мультиплексор команд (как на роботе)
    cmd_mux = Node(
        package='cmd_switcher', executable='cmd_mux_node',
        name='cmd_switcher', output='screen',
        parameters=[{'use_sim_time': True}],
    )

    # 7a. Визуальная одометрия RTAB-Map -> /odom (odom_source:=visual)
    #     Настоящая VO по картинке виртуальной Astra. На синтетике капризна
    #     (бедная текстура), поэтому по умолчанию НЕ используется.
    odometry_visual = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_odom, 'launch', 'rgbd_odometry.launch.py')),
        condition=IfCondition(PythonExpression(
            ["'", odom_source, "' == 'visual'"])),
        launch_arguments={
            'use_sim_time': 'true',
            'publish_tf': 'false',
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'odom_topic': '/odom',
        }.items(),
    )

    # 7b. Эталонная одометрия из симулятора -> /odom (odom_source:=ground_truth)
    #     Идеальная поза: позволяет проверить EKF->GPS->Nav2 детерминированно,
    #     не завися от капризов VO на синтетике. Режим по умолчанию.
    odometry_gt = Node(
        package='astra_gazebo', executable='ground_truth_to_odom.py',
        name='ground_truth_to_odom', output='screen',
        condition=IfCondition(PythonExpression(
            ["'", odom_source, "' == 'ground_truth'"])),
        parameters=[{
            'use_sim_time': True,
            'input_topic': '/ground_truth/odometry',
            'output_topic': '/odom',
            'odom_frame': 'odom',
            'base_frame': 'base_link',
        }],
    )

    # 8. Локализация (dual-EKF + navsat_transform) — тот же файл, что на роботе
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'localization.launch.py')),
        launch_arguments={'use_sim_time': 'true'}.items(),
    )

    # 9. Nav2 (опционально)
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'navigation.launch.py')),
        condition=IfCondition(use_navigation),
        launch_arguments={'use_sim_time': 'true', 'autostart': 'true'}.items(),
    )

    # 10. RViz
    rviz = Node(
        package='rviz2', executable='rviz2', name='rviz2', output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(use_rviz),
    )

    # Одометрию, локализацию и навигацию поднимаем ПОСЛЕ спавна робота
    # (когда камера/лидар/GPS уже существуют и мост отдаёт данные).
    after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn, on_exit=[
            odometry_visual,
            odometry_gt,
            TimerAction(period=3.0, actions=[localization]),
            TimerAction(period=8.0, actions=[navigation]),
        ])
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_navigation', default_value='false'),
        DeclareLaunchArgument(
            'odom_source', default_value='ground_truth',
            description="Источник /odom: 'ground_truth' (эталон симулятора, "
                        "по умолчанию) или 'visual' (настоящая VO по камере)."),
        DeclareLaunchArgument('world', default_value=default_world),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.2'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        gz_sim,
        rsp,
        bridge,
        relay,
        cmd_mux,
        spawn,
        after_spawn,
        rviz,
    ])
