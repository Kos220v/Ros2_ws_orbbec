# robot_odometry.launch.py
#
# TOP-LEVEL launch for the real robot. Brings up everything needed to get
# visual odometry from the Astra camera mounted on the diff-drive robot:
#
#   1. Robot description + TF (astra_description)
#   2. Astra OpenNI camera driver (astra_camera)
#   3. RTAB-Map rgbd_odometry -> /odom and odom->base_footprint TF
#   4. (optional) RViz2 preconfigured to show odometry + TF + point cloud
#
# Usage:
#   ros2 launch astra_odometry robot_odometry.launch.py
#   ros2 launch astra_odometry robot_odometry.launch.py use_rviz:=true
#
# Args (forwarded to sub-launches):
#   use_sim_time (bool)   [false]
#   use_rviz     (bool)   [false]
#   publish_tf   (bool)   publish odom->base_footprint [true]
#   driver_launch(str)    astra_camera launch file [astra.launch.xml]

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            GroupAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_odom = get_package_share_directory('astra_odometry')
    pkg_desc = get_package_share_directory('astra_description')

    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('use_rviz')
    publish_tf = LaunchConfiguration('publish_tf')
    driver_launch = LaunchConfiguration('driver_launch')

    rviz_file = os.path.join(pkg_odom, 'rviz', 'odometry.rviz')

    # 1. Robot description + TF
    description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_desc, 'launch', 'description.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
    )

    # 2. Astra OpenNI driver
    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_odom, 'launch', 'astra_camera.launch.py')),
        launch_arguments={'driver_launch': driver_launch}.items(),
    )

    # 3. RTAB-Map visual odometry
    odometry = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_odom, 'launch', 'rgbd_odometry.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'publish_tf': publish_tf,
            'frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
        }.items(),
    )

    # 4. RViz (optional)
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_rviz', default_value='false'),
        DeclareLaunchArgument('publish_tf', default_value='true'),
        DeclareLaunchArgument('driver_launch', default_value='astra.launch.xml'),

        GroupAction([
            description,
            camera,
            odometry,
            rviz,
        ]),
    ])
