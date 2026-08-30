#!/usr/bin/env python3
"""Unit tests for astra_odometry helpers (no ROS graph required).

These verify the pure-python math used by the odometry monitor so the package
has meaningful, fast, hardware-free tests (`colcon test`).
"""
import math

import pytest

from astra_odometry.math_utils import yaw_from_quaternion


class Q:
    """Minimal quaternion stand-in matching geometry_msgs/Quaternion fields."""
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x, self.y, self.z, self.w = x, y, z, w


def quat_from_yaw(yaw):
    return Q(0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def test_yaw_identity():
    assert yaw_from_quaternion(Q()) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize('yaw_deg', [-179, -90, -45, 0, 30, 90, 170])
def test_yaw_roundtrip(yaw_deg):
    yaw = math.radians(yaw_deg)
    q = quat_from_yaw(yaw)
    assert yaw_from_quaternion(q) == pytest.approx(yaw, abs=1e-6)


def test_yaw_wraps_at_pi():
    # +180 and -180 degrees are the same orientation
    q = quat_from_yaw(math.pi)
    assert abs(yaw_from_quaternion(q)) == pytest.approx(math.pi, abs=1e-6)
