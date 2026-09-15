#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rgbd_odometry.launch.py — ВИЗУАЛЬНАЯ одометрия RTAB-Map по RGB-D с Astra.

НАГРУЗКА НА RASPBERRY PI 4
--------------------------
rgbd_odometry по умолчанию обрабатывает КАЖДЫЙ пришедший кадр. С камеры на
30 к/с и 1000 признаков на кадр это занимает целое ядро Pi 4 и раздувает
задержку остальных узлов (пульт, мультиплексор, привод начинают пропускать
свои тайм-ауты — робот дёргается). Здесь одометрия сознательно «облегчена»:

  * max_update_rate = 10 Гц — лишние кадры пропускаются внутри узла ещё до
    обработки (для EKF на 20 Гц этого более чем достаточно, а Nav2 читает
    уже отфильтрованный /odometry/local);
  * Odom/ImageDecimation = 2 — признаки ищутся на картинке 320x240,
    полученной из 640x480 (глубина при этом остаётся в масштабе);
  * Vis/MaxFeatures = 500, OdomF2M/MaxSize = 500 — вдвое меньше точек в
    кадре и в локальной карте одометрии.

Если понадобится вернуть «тяжёлые» настройки для тестов:
    ros2 launch astra_odometry visual_odometry.launch.py \
        odom_max_update_rate:=0.0 image_decimation:=1 vis_max_features:=1000
"""

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
    # Ограничение частоты обработки кадров (0.0 = обрабатывать все).
    odom_max_update_rate = ParameterValue(
        LaunchConfiguration('odom_max_update_rate'), value_type=float)
    # RTAB-Map ждёт свои параметры СТРОКАМИ, поэтому форсируем тип.
    vis_max_features = ParameterValue(
        LaunchConfiguration('vis_max_features'), value_type=str)
    vis_min_inliers = ParameterValue(
        LaunchConfiguration('vis_min_inliers'), value_type=str)
    image_decimation = ParameterValue(
        LaunchConfiguration('image_decimation'), value_type=str)
    f2m_max_size = ParameterValue(
        LaunchConfiguration('f2m_max_size'), value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_tf', default_value='false'),
        DeclareLaunchArgument('frame_id', default_value='base_link'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('approx_sync', default_value='true'),
        DeclareLaunchArgument('approx_sync_max_interval', default_value='0.05'),
        DeclareLaunchArgument('qos', default_value='2'),
        DeclareLaunchArgument(
            'odom_max_update_rate', default_value='10.0',
            description='Макс. частота обработки кадров одометрией, Гц '
                        '(0.0 = все кадры). 10 Гц достаточно для EKF/Nav2.'),
        DeclareLaunchArgument(
            'image_decimation', default_value='2',
            description='Odom/ImageDecimation: 2 = искать признаки на '
                        'картинке вдвое меньшего размера (в 4 раза меньше '
                        'пикселей).'),
        DeclareLaunchArgument('vis_max_features', default_value='500'),
        DeclareLaunchArgument('vis_min_inliers', default_value='15'),
        DeclareLaunchArgument(
            'f2m_max_size', default_value='500',
            description='OdomF2M/MaxSize: размер локальной карты признаков.'),
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
                # Пропускать кадры, приходящие чаще этой частоты
                # (экономит CPU: пропущенный кадр вообще не обрабатывается).
                'max_update_rate': odom_max_update_rate,
                'Odom/Strategy': '0',
                'Odom/ImageDecimation': image_decimation,
                'Vis/FeatureType': '6',
                'OdomF2M/MaxSize': f2m_max_size,
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
