#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rgbd_odometry.launch.py — ВИЗУАЛЬНАЯ одометрия RTAB-Map по RGB-D с Astra."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_tf = LaunchConfiguration('publish_tf')
    frame_id = LaunchConfiguration('frame_id')
    odom_frame_id = LaunchConfiguration('odom_frame_id')
    approx_sync = LaunchConfiguration('approx_sync')
    approx_sync_max_interval = LaunchConfiguration('approx_sync_max_interval')
    qos = LaunchConfiguration('qos')
    rgb_topic = LaunchConfiguration('rgb_topic')
    depth_topic = LaunchConfiguration('depth_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')
    odom_topic = LaunchConfiguration('odom_topic')
    # RTAB-Map ждёт эти параметры СТРОКАМИ, поэтому форсируем тип.
    vis_max_features = ParameterValue(
        LaunchConfiguration('vis_max_features'), value_type=str)
    vis_min_inliers = ParameterValue(
        LaunchConfiguration('vis_min_inliers'), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_tf', default_value='false'),
        DeclareLaunchArgument('frame_id', default_value='base_link'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('approx_sync', default_value='true'),
        DeclareLaunchArgument('approx_sync_max_interval', default_value='0.05'),
        DeclareLaunchArgument('qos', default_value='2'),
        DeclareLaunchArgument('vis_max_features', default_value='1000'),
        DeclareLaunchArgument('vis_min_inliers', default_value='15'),
        DeclareLaunchArgument('rgb_topic', default_value='/camera/color/image_raw'),
        DeclareLaunchArgument('depth_topic', default_value='/camera/depth/image_raw'),
        DeclareLaunchArgument('camera_info_topic', default_value='/camera/color/camera_info'),
        DeclareLaunchArgument('odom_topic', default_value='/odom'),

        Node(
            package='rtabmap_odom',
            executable='rgbd_odometry',
            name='rgbd_odometry',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'frame_id': frame_id,
                'odom_frame_id': odom_frame_id,
                'publish_tf': publish_tf,
                'approx_sync': approx_sync,
                'approx_sync_max_interval': approx_sync_max_interval,
                'qos': qos,
                'qos_camera_info': qos,
                'wait_for_transform': 0.2,
                'subscribe_rgbd': False,
                'Odom/Strategy': '0',
                'Vis/FeatureType': '6',
                'OdomF2M/MaxSize': '1000',
                'Vis/MaxFeatures': vis_max_features,
                'Vis/MinInliers': vis_min_inliers,
                'OdomF2M/MaxNewFeatures': '0',
                'Odom/ResetCountdown': '1',
                'Odom/GuessMotion': 'true',
            }],
            remappings=[
                ('rgb/image', rgb_topic),
                ('depth/image', depth_topic),
                ('rgb/camera_info', camera_info_topic),
                ('odom', odom_topic),
            ],
        ),
    ])
