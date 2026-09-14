#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
astra_camera.launch.py — драйвер камеры Orbbec Astra (OpenNI / astra_camera).

Включает depth->color registration, чтобы RGB и depth пиксели совпадали
(обязательно для RGB-D визуальной одометрии). Публикует те же топики, что
ожидает rgbd_odometry:
    /camera/color/image_raw, /camera/color/camera_info, /camera/depth/image_raw

Драйвер astra_camera ставится из исходников:
    github.com/orbbec/ros2_astra_camera
Если у вас другой launch-файл драйвера, задайте driver_launch:=...
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    driver_launch = LaunchConfiguration('driver_launch')

    astra_launch_path = PathJoinSubstitution([
        FindPackageShare('astra_camera'), 'launch', driver_launch
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'driver_launch', default_value='astra.launch.xml',
            description='Launch-файл внутри пакета astra_camera '
                        '(например astra.launch.xml, astra_mini.launch.xml).'),

        LogInfo(msg=['[astra_camera.launch.py] Драйвер astra_camera: ',
                     driver_launch]),

        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(astra_launch_path),
            launch_arguments={
                'depth_registration': 'true',
                'enable_colored_point_cloud': 'false',
                'enable_point_cloud': 'false',
                'camera_name': 'camera',
            }.items(),
        ),
    ])
