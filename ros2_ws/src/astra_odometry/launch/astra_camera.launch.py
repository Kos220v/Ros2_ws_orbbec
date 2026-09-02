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

НАГРУЗКА НА RASPBERRY PI 4 (почему здесь не значения драйвера по умолчанию)
---------------------------------------------------------------------------
По умолчанию драйвер отдаёт color + depth + ir 640x480 @ 30 к/с и, кроме
того, каждые 100 мс заново публикует свои (статические!) трансформы в /tf.
На Pi 4 это давало постоянную нагрузку от захвата, копирования и передачи
~45 МБ/с картинок через DDS, а rgbd_odometry пыталась обработать все 30
кадров и занимала целое ядро. Остальные узлы (пульт, мультиплексор,
привод) начинали пропускать свои тайм-ауты — робот ехал рывками.

Поэтому:
  * color_fps / depth_fps = 15. Если камера не поддерживает 15 к/с в этом
    разрешении, драйвер сам напишет WARN и откатится к поддерживаемой
    частоте (обычно 30) — стек не сломается.
  * enable_ir = false — ИК-поток одометрии не нужен (при включённом color
    драйвер и так его отключает, но лучше не полагаться на это).
  * tf_publish_rate = 0 — трансформы камеры публикуются ОДИН раз как
    статические (/tf_static). Имена фреймов те же, зато tf2 больше не ждёт
    «свежую» трансформацию под каждый кадр, и лишнего трафика в /tf нет.
  * при желании можно снизить разрешение: color_width:=320 color_height:=240
    depth_width:=320 depth_height:=240 — одометрии этого достаточно.
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

        # --- частота и разрешение потоков (см. шапку файла) ---------------
        DeclareLaunchArgument('color_width', default_value='640'),
        DeclareLaunchArgument('color_height', default_value='480'),
        DeclareLaunchArgument('color_fps', default_value='15',
                              description='Кадров/с цветного потока. '
                                          '15 достаточно для одометрии.'),
        DeclareLaunchArgument('depth_width', default_value='640'),
        DeclareLaunchArgument('depth_height', default_value='480'),
        DeclareLaunchArgument('depth_fps', default_value='15',
                              description='Кадров/с потока глубины. '
                                          'Держите равным color_fps.'),
        DeclareLaunchArgument('enable_ir', default_value='false',
                              description='ИК-поток одометрии не нужен.'),
        # 0 = опубликовать трансформы камеры один раз как статические.
        DeclareLaunchArgument('tf_publish_rate', default_value='0.0',
                              description='Гц повторной публикации TF камеры; '
                                          '0 — статические трансформы.'),

        LogInfo(msg=['[astra_camera.launch.py] Драйвер astra_camera: ',
                     driver_launch,
                     '  color ', LaunchConfiguration('color_width'), 'x',
                     LaunchConfiguration('color_height'), '@',
                     LaunchConfiguration('color_fps'),
                     '  depth ', LaunchConfiguration('depth_width'), 'x',
                     LaunchConfiguration('depth_height'), '@',
                     LaunchConfiguration('depth_fps')]),

        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(astra_launch_path),
            launch_arguments={
                'depth_registration': 'true',
                'enable_colored_point_cloud': 'false',
                'enable_point_cloud': 'false',
                'camera_name': 'camera',
                'color_width': LaunchConfiguration('color_width'),
                'color_height': LaunchConfiguration('color_height'),
                'color_fps': LaunchConfiguration('color_fps'),
                'depth_width': LaunchConfiguration('depth_width'),
                'depth_height': LaunchConfiguration('depth_height'),
                'depth_fps': LaunchConfiguration('depth_fps'),
                'enable_ir': LaunchConfiguration('enable_ir'),
                'publish_tf': 'true',
                'tf_publish_rate': LaunchConfiguration('tf_publish_rate'),
            }.items(),
        ),
    ])
