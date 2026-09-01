#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ground_truth_to_odom.py — ретранслятор эталонной одометрии в /odom.

Берёт точную позу робота из симулятора (/ground_truth/odometry, публикует
плагин gz OdometryPublisher) и переопубликовывает её в /odom с корректными
именами фреймов (frame_id=odom, child_frame_id=base_link), которые ждёт EKF.

Нужен для режима odom_source:=ground_truth: позволяет проверить всю связку
EKF -> GPS -> navsat -> Nav2 на ИДЕАЛЬНОЙ одометрии, не завися от капризов
визуальной одометрии на синтетической картинке. TF odom->base_link НЕ
публикуется — он принадлежит ekf_filter_node_odom (как и с настоящей VO).

Ковариацию ставим маленькой, но НЕнулевой, иначе EKF ругается на вырожденную
матрицу.
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry


class GroundTruthToOdom(Node):
    def __init__(self):
        super().__init__('ground_truth_to_odom')
        self.declare_parameter('input_topic', '/ground_truth/odometry')
        self.declare_parameter('output_topic', '/odom')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('base_frame', 'base_link')

        in_topic = self.get_parameter('input_topic').value
        out_topic = self.get_parameter('output_topic').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.base_frame = self.get_parameter('base_frame').value

        self.pub = self.create_publisher(Odometry, out_topic, 10)
        self.sub = self.create_subscription(
            Odometry, in_topic, self.cb, 10)
        self.get_logger().info(
            'ground_truth_to_odom: %s -> %s (frame=%s child=%s)'
            % (in_topic, out_topic, self.odom_frame, self.base_frame))

    def cb(self, msg):
        out = Odometry()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = self.odom_frame
        out.child_frame_id = self.base_frame
        out.pose = msg.pose
        out.twist = msg.twist

        # Небольшая ненулевая ковариация (эталон почти точный)
        pose_cov = [0.0] * 36
        twist_cov = [0.0] * 36
        for i, idx in enumerate((0, 7, 14, 21, 28, 35)):
            pose_cov[idx] = 1e-4
            twist_cov[idx] = 1e-4
        out.pose.covariance = pose_cov
        out.twist.covariance = twist_cov

        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = GroundTruthToOdom()
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
