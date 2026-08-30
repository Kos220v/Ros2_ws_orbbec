# simulation.launch.py
#
# FULL virtual test of the Astra visual-odometry pipeline in Gazebo Harmonic --
# no real robot and no real camera required.
#
# Brings up:
#   1. Gazebo Harmonic with a feature-rich world
#   2. robot_state_publisher with the URDF (use_gazebo:=true -> sensors+plugins)
#   3. The robot spawned into the world
#   4. ros_gz_bridge (clock, cmd_vel, camera, wheel/ground-truth odometry)
#   5. RTAB-Map rgbd_odometry -> /odom + TF odom->base_footprint (VISUAL VO)
#   6. (optional) RViz2
#
# Drive the robot with, in another terminal:
#   ros2 run teleop_twist_keyboard teleop_twist_keyboard
#
# Compare:
#   /odom                 -> visual odometry (RTAB-Map)  [what we test]
#   /wheel/odometry       -> wheel odometry (Gazebo diff-drive)  [reference]
#   /ground_truth/odometry-> exact pose from the simulator       [truth]

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_gz = get_package_share_directory('astra_gazebo')
    pkg_desc = get_package_share_directory('astra_description')
    pkg_odom = get_package_share_directory('astra_odometry')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_file = os.path.join(pkg_gz, 'worlds', 'astra_world.sdf')
    bridge_config = os.path.join(pkg_gz, 'config', 'bridge.yaml')
    xacro_file = os.path.join(pkg_desc, 'urdf', 'astra_robot.urdf.xacro')
    rviz_file = os.path.join(pkg_gz, 'rviz', 'simulation.rviz')

    use_rviz = LaunchConfiguration('use_rviz')
    world = LaunchConfiguration('world')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    z = LaunchConfiguration('z')
    yaw = LaunchConfiguration('yaw')

    # Robot description with Gazebo sensors/plugins enabled
    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' use_gazebo:=true']),
        value_type=str,
    )

    # 1. Gazebo Harmonic
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': [world, ' -r -v 3']}.items(),
    )

    # 2. robot_state_publisher (also feeds the spawner via /robot_description)
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    # 3. Spawn the robot from the /robot_description topic
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_astra_robot',
        output='screen',
        arguments=[
            '-topic', '/robot_description',
            '-name', 'astra_robot',
            '-x', x, '-y', y, '-z', z, '-Y', yaw,
        ],
    )

    # 4. ros <-> gz bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{
            'config_file': bridge_config,
            'use_sim_time': True,
        }],
    )

    # 5. RTAB-Map visual odometry (reuse the odometry package's launch)
    odometry = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_odom, 'launch', 'rgbd_odometry.launch.py')),
        launch_arguments={
            'use_sim_time': 'true',
            'publish_tf': 'true',
            'frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'approx_sync': 'true',
            'qos': '2',
        }.items(),
    )

    # 6. RViz (optional)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(use_rviz),
    )

    # Start odometry only after the robot is spawned (camera exists)
    odom_after_spawn = RegisterEventHandler(
        OnProcessExit(target_action=spawn, on_exit=[odometry])
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('world', default_value=world_file),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.08'),
        DeclareLaunchArgument('yaw', default_value='0.0'),

        gz_sim,
        rsp,
        bridge,
        spawn,
        odom_after_spawn,
        rviz,
    ])
