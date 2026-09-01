#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
teleop.launch.py — управление роботом в симуляции с клавиатуры.

Публикует в /cmd_vel/app_manual, чтобы команды прошли через cmd_switcher
(тот же путь, что у ручного управления на реальном роботе). Требует xterm;
если его нет — запустите вручную:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard \\
        --ros-args -r /cmd_vel:=/cmd_vel/app_manual
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='teleop_twist_keyboard',
            executable='teleop_twist_keyboard',
            name='teleop_twist_keyboard',
            output='screen',
            prefix='xterm -e',
            remappings=[('/cmd_vel', '/cmd_vel/app_manual')],
            parameters=[{'use_sim_time': True}],
        ),
    ])
