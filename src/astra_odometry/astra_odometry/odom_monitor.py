#!/usr/bin/env python3
"""odom_monitor.py

Manual test helper: subscribes to /odom (nav_msgs/Odometry) and prints a
compact, human-readable summary of the visual odometry produced by
rtabmap rgbd_odometry.

Reports, at a throttled rate:
  * current pose  (x, y, z, yaw)
  * linear / angular velocity
  * total distance travelled since start
  * effective odometry publish rate (Hz)
  * a warning when the pose stops updating (VO likely lost)

Run:
  ros2 run astra_odometry odom_monitor
  ros2 run astra_odometry odom_monitor --ros-args -p odom_topic:=/odom -p report_period:=1.0
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
            f"odom_monitor listening on '{odom_topic}'. Move the camera/robot "
            f"and watch the pose change.")

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
                'No /odom messages received yet. Is rgbd_odometry running and '
                'is the camera publishing rgb+depth?')
            return

        if self.last_msg_time is not None and (now - self.last_msg_time) > self.stall_timeout:
            self.get_logger().warn(
                f'No odometry update for {now - self.last_msg_time:.1f}s '
                f'-> visual odometry may be LOST (blank wall / too fast / dark).')

        m = self.last_msg
        p = m.pose.pose.position
        yaw = yaw_from_quaternion(m.pose.pose.orientation)
        v = m.twist.twist.linear
        w = m.twist.twist.angular
        speed = math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)

        self.get_logger().info(
            f"pose x={p.x:+.3f} y={p.y:+.3f} z={p.z:+.3f} yaw={math.degrees(yaw):+6.1f}deg | "
            f"vel lin={speed:.3f} m/s ang={w.z:+.3f} rad/s | "
            f"dist={self.total_distance:.3f} m | rate={hz:4.1f} Hz | msgs={self.count}")


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
