#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
visual_odometry.launch.py — камера Astra + RTAB-Map rgbd_odometry в одном месте.

Это ЗАМЕНА связки robot_odom (колёсная одометрия) + mpu6050_control +
compass_control + imu_filter_madgwick + mag_declination_node. Публикует /odom
(поза + курс + скорости) от визуальной одометрии.

Запускается слоем железа (project_start/start.launch.py) вместо старых узлов.
Можно запустить и отдельно для проверки:
    ros2 launch astra_odometry visual_odometry.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_share = get_package_share_directory('astra_odometry')

    use_sim_time = LaunchConfiguration('use_sim_time')
    driver_launch = LaunchConfiguration('driver_launch')

    camera = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'astra_camera.launch.py')),
        launch_arguments={'driver_launch': driver_launch}.items(),
    )

    odometry = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'rgbd_odometry.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            # TF odom->base_link принадлежит EKF, не VO
            'publish_tf': 'false',
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'odom_topic': '/odom',
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('driver_launch', default_value='astra.launch.xml'),
        camera,
        odometry,
    ])
