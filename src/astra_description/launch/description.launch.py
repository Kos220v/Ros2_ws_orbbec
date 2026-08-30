# description.launch.py
# Publishes the robot_description (URDF from xacro), robot_state_publisher and
# (optionally) joint_state_publisher_gui. Can also open RViz2.
#
# Args:
#   use_sim_time (bool)  : use /clock                       [default: false]
#   use_gui      (bool)  : run joint_state_publisher_gui    [default: false]
#   use_rviz     (bool)  : open RViz2 with the robot config [default: false]

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('astra_description')
    xacro_file = os.path.join(pkg_share, 'urdf', 'astra_robot.urdf.xacro')
    rviz_file = os.path.join(pkg_share, 'rviz', 'description.rviz')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_gui = LaunchConfiguration('use_gui')
    use_rviz = LaunchConfiguration('use_rviz')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]), value_type=str
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                              description='Use simulation (Gazebo) clock'),
        DeclareLaunchArgument('use_gui', default_value='false',
                              description='Run joint_state_publisher_gui'),
        DeclareLaunchArgument('use_rviz', default_value='false',
                              description='Open RViz2'),

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': use_sim_time,
            }],
        ),

        # Static joint states (wheels) unless the GUI is requested
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=UnlessCondition(use_gui),
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(use_gui),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_file],
            parameters=[{'use_sim_time': use_sim_time}],
            condition=IfCondition(use_rviz),
        ),
    ])
