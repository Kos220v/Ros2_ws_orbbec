#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
localization.launch.py — оценка положения робота на местности.

ИСТОЧНИКИ разделены: kolesa_control публикует /wheel/odometry с расстоянием
и продольной скоростью, а новый STM32 IMU публикует /imu/data с курсом и
угловой скоростью. Визуальная одометрия и камера полностью удалены. Поэтому mag_declination_node и
imu_filter_madgwick здесь БОЛЬШЕ НЕ ЗАПУСКАЮТСЯ.

Остаётся три узла:

    /odom (визуальная одометрия) ─┐
                                  ├─> ekf_filter_node_odom
                                  │     ─> TF odom -> base_link, /odometry/local
                                  │
                                  ├─> ekf_filter_node_map
                                  │     ─> TF map -> odom,       /odometry/global
                                  │            ^
                                  │            |
                                  │      /odometry/gps
                                  │            ^
                                  │            |
    /gps/fix + /odometry/global ─────> navsat_transform ─> /odometry/gps

Курс navsat_transform берёт из STM32 IMU, а не из колёсной одометрии. Запускается отдельно от навигации намеренно: локализацию нужно
уметь проверять без Nav2.

Источник /wheel/odometry и /imu/data поднимается слоем железа
(project_start/start.launch.py), а не здесь.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robot_navigation')
    config_dir = os.path.join(pkg_share, 'config')

    ekf_params = os.path.join(config_dir, 'dual_ekf_navsat.yaml')

    # ------------------------------------------------------------- аргументы
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time', default_value='false',
        description='Использовать /clock вместо системного времени',
    )

    use_sim_time = LaunchConfiguration('use_sim_time')

    # -------------------------------------------------------- локальный EKF
    ekf_odom_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_odom',
        output='screen',
        parameters=[ekf_params, {'use_sim_time': use_sim_time}],
        remappings=[
            # Оба EKF публикуют в /odometry/filtered и
            # затирали бы друг друга. Разводим их по разным топикам.
            ('odometry/filtered', 'odometry/local'),
            ('accel/filtered', 'accel/local'),
            ('/set_pose', '/set_pose_local'),
        ],
    )

    # -------------------------------------------------------- глобальный EKF
    ekf_map_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node_map',
        output='screen',
        parameters=[ekf_params, {'use_sim_time': use_sim_time}],
        remappings=[
            ('odometry/filtered', 'odometry/global'),
            ('accel/filtered', 'accel/global'),
            ('/set_pose', '/set_pose_global'),
        ],
    )

    # ------------------------------------------------------ WGS84 -> метры
    navsat_transform_node = Node(
        package='robot_localization',
        executable='navsat_transform_node',
        name='navsat_transform',
        output='screen',
        parameters=[ekf_params, {'use_sim_time': use_sim_time}],
        remappings=[
            # Входы: курс и угловая скорость нового STM32 IMU.
            ('imu/data', 'imu/data'),
            ('gps/fix', 'gps/fix'),
            ('odometry/filtered', 'odometry/global'),
            # Выходы
            ('odometry/gps', 'odometry/gps'),
            ('gps/filtered', 'gps/filtered'),
        ],
    )

    return LaunchDescription([
        use_sim_time_arg,
        ekf_odom_node,
        ekf_map_node,
        navsat_transform_node,
    ])
