# teleop.launch.py
# Convenience launcher for keyboard teleop of the simulated robot.
# Publishes geometry_msgs/Twist on /cmd_vel (bridged to Gazebo diff-drive).
#
# NOTE: teleop_twist_keyboard needs a real terminal for key input, so this is
# launched in its own xterm. If you don't have xterm, just run instead:
#   ros2 run teleop_twist_keyboard teleop_twist_keyboard

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
            remappings=[('/cmd_vel', '/cmd_vel')],
        ),
    ])
