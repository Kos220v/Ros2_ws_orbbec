#!/usr/bin/env python3
"""Pure-python math helpers for odometry (no ROS dependencies).

Kept ROS-free so it can be unit-tested with plain pytest.
"""
import math


def yaw_from_quaternion(q) -> float:
    """Extract yaw (rotation about Z) from anything with .x/.y/.z/.w fields.

    Works with geometry_msgs/Quaternion as well as any simple object or a
    duck-typed stand-in used in tests.
    """
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)
