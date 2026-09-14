#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
start.launch.py — СЛОЙ ЖЕЛЕЗА: датчики, приводы, TF-дерево, мультиплексор.

Этот файл сознательно НЕ содержит локализацию и навигацию. Раньше он поднимал
всё сразу, и отладить что-то одно было невозможно. Теперь стек разделён на три
слоя, каждый из которых можно запустить и проверить отдельно:

    project_start/start.launch.py            <- железо (этот файл)
    robot_navigation/localization.launch.py  <- EKF + GPS + курс
    robot_navigation/navigation.launch.py    <- Nav2

Всё сразу поднимает robot_navigation/bringup.launch.py.

ЧТО ЗДЕСЬ ЗАПУСКАЕТСЯ
---------------------
  elrs_receiver      пульт -> /cmd_vel/manual, /control_mode
  nmea_navsat_driver GNSS  -> /gps/fix
  kolesa_control     моторы: /cmd_vel -> VESC, энкодеры -> /joint_states
  astra_odometry     камера Astra + RTAB-Map rgbd_odometry -> /odom
                     (ВИЗУАЛЬНАЯ одометрия: поза + курс + скорости)
  robot_state_publisher  URDF -> статические TF датчиков
  cmd_switcher       приоритеты источников команд -> /cmd_vel
  ydlidar            лидар -> /scan
  relay_reliable     /scan -> /scan_reliable (смена QoS на RELIABLE)

ЗАМЕНА ИСТОЧНИКА ОДОМЕТРИИ
-------------------------
Колёсная одометрия (robot_odom), гироскоп/акселерометр (mpu6050_control) и
магнитометр (compass_control) УБРАНЫ. Вместо них /odom публикует визуальная
одометрия RTAB-Map по RGB-D камере Orbbec Astra (пакет astra_odometry).
Одометрия визуальная даёт и позу, и курс (yaw), поэтому отдельный датчик
курса (IMU + компас) больше не нужен.

КЛЮЧЕВОЕ ПРАВИЛО ПРО TF
-----------------------
Ни один узел этого слоя НЕ публикует odom -> base_link. Этот трансформ
принадлежит фильтру ekf_filter_node_odom. Если включить publish_tf у
kolesa_control или у rgbd_odometry (astra_odometry), трансформ начнут
публиковать двое, и робот в RViz будет прыгать между двумя позициями.
Поэтому у визуальной одометрии publish_tf:=false (задан в
astra_odometry/launch/rgbd_odometry.launch.py) и менять его нельзя.

ПОЧЕМУ ЗДЕСЬ OpaqueFunction, А НЕ ПРОСТОЙ СПИСОК ДЕЙСТВИЙ
---------------------------------------------------------
У TimerAction есть неочевидная ловушка: значение period вычисляется НЕ в
момент разбора launch-файла, а позже, в асинхронной задаче. Если передать
туда LaunchConfiguration, а сам launch-файл подключён через
IncludeLaunchDescription внутри GroupAction (именно так делает
bringup.launch.py), то к моменту вычисления область видимости группы уже
закрыта, и запуск падает с ошибкой:

    SubstitutionFailure: launch configuration 'lidar_delay' does not exist

Внешне это выглядит безобидно — остальные узлы стартуют, — но лидар
не поднимается, и Nav2 остаётся без данных о препятствиях.

Решение: OpaqueFunction получает context и позволяет вычислить аргумент
СРАЗУ, превратив его в обычное число ещё до создания TimerAction.
"""

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _first_existing(*paths):
    """Возвращает первый существующий путь (udev-алиас или обычный ttyUSB)."""
    for p in paths:
        if p and os.path.exists(p):
            return p
    return paths[0] if paths else None


def launch_setup(context, *args, **kwargs):
    """Собирает список узлов. context позволяет вычислить аргументы сразу."""

    project_start_share = get_package_share_directory('project_start')

    # Порты USB. Настоятельно рекомендуется прописать udev-правила по VID/PID,
    # иначе после перезагрузки лидар и GPS могут поменяться номерами:
    #   лидар CP210x (10c4:ea60) -> /dev/lidar
    #   GPS   PL2303  (067b:2303) -> /dev/gps
    lidar_port = _first_existing('/dev/lidar', '/dev/ttyUSB0')
    gps_port = _first_existing('/dev/gps', '/dev/ttyUSB1')

    # Вычисляем задержку ПРЯМО СЕЙЧАС и получаем обычный float.
    # Дальше в TimerAction уходит число, а не подстановка.
    lidar_delay = float(
        LaunchConfiguration('lidar_delay').perform(context))



    # ------------------------------------------------------------ пульт ELRS
    elrs_node = Node(
        package='elrs_receiver',
        executable='elrs_node',
        name='elrs_receiver',
        output='screen',
        parameters=[{
            'port': '/dev/ttyAMA2',
            'baudrate': 420000,
            'deadzone': 0.02,
            'throttle_channel': 1,
            'steering_channel': 0,
            'invert_throttle': False,
            'invert_steering': False,
            'channel_min': 172,
            'channel_center': 992,
            'channel_max': 1811,
        }],
    )

    # ------------------------------------------------------------------ GNSS
    gps_node = Node(
        package='nmea_navsat_driver',
        executable='nmea_serial_driver',
        name='nmea_navsat_driver',
        output='screen',
        parameters=[{
            'port': gps_port,
            'baud': 115200,
            # Фрейм обязан совпадать с именем звена в URDF: navsat_transform
            # ищет смещение антенны относительно base_link именно по нему.
            'frame_id': 'gps_link',
            'useRMC': False,
        }],
        remappings=[
            ('fix', 'gps/fix'),
        ],
    )

    # --------------------------------------------------------------- приводы
    kolesa_control_node = Node(
        package='kolesa_control',
        executable='kolesa_control',
        name='kolesa_control',
        output='screen',
        parameters=[{
            'left_port': '/dev/ttyAMA4',
            'right_port': '/dev/ttyAMA5',
            'baud': 115200,
            'wheel_radius': 0.0723,
            'wheel_separation': 0.48,
            'gear_ratio': 19.5,
            'pole_pairs': 2,
            'invert_left': False,
            'invert_right': True,
            'encoder_invert_left': False,
            'encoder_invert_right': True,
            'left_wheel_joint': 'left_track_joint',
            'right_wheel_joint': 'right_track_joint',
            'invert_angular': False,
        }],
    )

    # ------------------------------------------- ВИЗУАЛЬНАЯ одометрия (Astra)
    # Замена robot_odom + mpu6050_control + compass_control.
    # Камера Orbbec Astra + RTAB-Map rgbd_odometry публикуют /odom
    # (поза X/Y + курс yaw + линейная/угловая скорости).
    # TF odom -> base_link здесь НЕ публикуется (publish_tf:=false внутри),
    # он принадлежит ekf_filter_node_odom.
    astra_odometry_share = get_package_share_directory('astra_odometry')
    visual_odometry = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(astra_odometry_share, 'launch',
                         'visual_odometry.launch.py')),
        launch_arguments={
            'driver_launch': LaunchConfiguration('astra_driver_launch'),
        }.items(),
    )

    # ------------------------------------------------------------- TF из URDF
    urdf_file = os.path.join(
        get_package_share_directory('tracked_robot_description'),
        'urdf', 'tracked_robot.urdf.xacro'
    )
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]), value_type=str)

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False,
        }],
    )

    # ------------------------------------------------- приоритеты команд
    cmd_mux_node = Node(
        package='cmd_switcher',
        executable='cmd_mux_node',
        name='cmd_switcher',
        output='screen',
    )

    # ------------------------------------------------------------------ лидар
    # ВНИМАНИЕ: файл лежит в params/, а НЕ в config/ — прежняя версия
    # launch-файла искала его в config/ и молча запускала лидар с
    # настройками по умолчанию (неверный порт и модель).
    ydlidar_params = os.path.join(project_start_share, 'params',
                                  'ydlidar_params.yaml')

    # Запускаем драйвер напрямую, а не через ydlidar_launch.py из пакета
    # производителя. Две причины:
    #
    #  1. Тот launch-файл принимает ТОЛЬКО путь к params_file, и порт в нём
    #     жёстко прописан как /dev/lidar. Без udev-правила такого устройства
    #     нет, лидар не открывается, а сообщение об ошибке тонет в общем
    #     потоке логов. Здесь порт подставляется автоматически:
    #     /dev/lidar, если правило настроено, иначе /dev/ttyUSB0.
    #
    #  2. Там узел объявлен как LifecycleNode, хотя в исходниках драйвера это
    #     обычный rclcpp::Node (ydlidar_ros2_driver_node.cpp, строка 38).
    #     Несоответствие безобидно, но сбивает с толку: кажется, будто узел
    #     нужно вручную переводить в active, хотя он публикует сразу.
    #
    # Имя узла обязано совпадать с ключом в ydlidar_params.yaml,
    # иначе параметры из файла не применятся.
    ydlidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_ros2_driver_node',
        output='screen',
        emulate_tty=True,
        parameters=[
            ydlidar_params,
            {'port': lidar_port},   # переопределяет port из файла
        ],
    )

    # period — обычное число, вычисленное выше. Подстановку сюда класть нельзя
    # (см. большой комментарий в начале файла).
    ydlidar_delayed = TimerAction(
        period=lidar_delay,
        actions=[
            LogInfo(msg=f'Запуск лидара на порту {lidar_port}'),
            ydlidar_node,
        ],
    )

    # /scan публикуется с QoS BEST_EFFORT; costmap Nav2 это устраивает, но
    # relay даёт RELIABLE-копию, которая надёжнее ходит по Wi-Fi на пульт
    # оператора и через rosbridge.
    relay_node = Node(
        package='relay_reliable',
        executable='relay_node',
        name='relay_reliable',
        output='screen',
    )

    return [
        elrs_node,
        gps_node,
        kolesa_control_node,
        visual_odometry,
        robot_state_publisher_node,
        cmd_mux_node,
        relay_node,
        ydlidar_delayed,
    ]


def generate_launch_description():
    lidar_delay_arg = DeclareLaunchArgument(
        'lidar_delay', default_value='10.0',
        description='Задержка старта лидара, сек: снижает вибрацию во время '
                    'инициализации остальных узлов',
    )

    astra_driver_arg = DeclareLaunchArgument(
        'astra_driver_launch', default_value='astra.launch.xml',
        description='Launch-файл драйвера внутри пакета astra_camera '
                    '(например astra.launch.xml, astra_mini.launch.xml)',
    )

    return LaunchDescription([
        lidar_delay_arg,
        astra_driver_arg,
        OpaqueFunction(function=launch_setup),
    ])
