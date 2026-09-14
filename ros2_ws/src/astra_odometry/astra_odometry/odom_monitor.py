#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""odom_monitor — ручная проверка визуальной одометрии с Astra.

Подписывается на /odom (nav_msgs/Odometry) и печатает компактную сводку:
поза (x, y, z, yaw), линейная/угловая скорости, пройденный путь, частота и
предупреждение, если поза перестала обновляться (VO потеряла трекинг).

Запуск:
    ros2 run astra_odometry odom_monitor
    ros2 run astra_odometry odom_monitor --ros-args -p odom_topic:=/odom
"""

import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from nav_msgs.msg import Odometry

from astra_odometry.math_utils import yaw_from_quaternion


class OdomMonitor(Node):
    def __init__(self):
        super().__init__('odom_monitor')

        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('report_period', 1.0)
        self.declare_parameter('stall_timeout', 2.0)

        odom_topic = self.get_parameter('odom_topic').value
        self.report_period = float(self.get_parameter('report_period').value)
        self.stall_timeout = float(self.get_parameter('stall_timeout').value)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self.sub = self.create_subscription(Odometry, odom_topic, self.cb, qos)

        self.count = 0
        self.total_distance = 0.0
        self.last_pos = None
        self.last_msg = None
        self.last_msg_time = None
        self.window_start = time.monotonic()
        self.window_count = 0

        self.timer = self.create_timer(self.report_period, self.report)
        self.get_logger().info(
            "odom_monitor слушает '%s'. Двигайте робота/камеру и смотрите позу."
            % odom_topic)

    def cb(self, msg: Odometry):
        self.count += 1
        self.window_count += 1
        self.last_msg = msg
        self.last_msg_time = time.monotonic()

        p = msg.pose.pose.position
        if self.last_pos is not None:
            dx = p.x - self.last_pos[0]
            dy = p.y - self.last_pos[1]
            dz = p.z - self.last_pos[2]
            self.total_distance += math.sqrt(dx * dx + dy * dy + dz * dz)
        self.last_pos = (p.x, p.y, p.z)

    def report(self):
        now = time.monotonic()
        elapsed = now - self.window_start
        hz = self.window_count / elapsed if elapsed > 0 else 0.0
        self.window_start = now
        self.window_count = 0

        if self.last_msg is None:
            self.get_logger().warn(
                'Нет сообщений /odom. Запущены ли rgbd_odometry и камера '
                '(есть ли rgb+depth)?')
            return

        if self.last_msg_time is not None and \
                (now - self.last_msg_time) > self.stall_timeout:
            self.get_logger().warn(
                'Нет обновления одометрии %.1f с -> визуальная одометрия, '
                'возможно, ПОТЕРЯНА (пустая стена / слишком быстро / темно).'
                % (now - self.last_msg_time))

        m = self.last_msg
        p = m.pose.pose.position
        yaw = yaw_from_quaternion(m.pose.pose.orientation)
        v = m.twist.twist.linear
        w = m.twist.twist.angular
        speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)

        self.get_logger().info(
            'pose x=%+.3f y=%+.3f z=%+.3f yaw=%+6.1f | '
            'vel lin=%.3f m/s ang=%+.3f rad/s | dist=%.3f m | %4.1f Hz | msgs=%d'
            % (p.x, p.y, p.z, math.degrees(yaw), speed, w.z,
               self.total_distance, hz, self.count))


def main(args=None):
    rclpy.init(args=args)
    node = OdomMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
