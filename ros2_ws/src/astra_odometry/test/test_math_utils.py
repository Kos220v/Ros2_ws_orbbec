#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Юнит-тесты чистой математики одометрии (без ROS-графа)."""

import math

import pytest

from astra_odometry.math_utils import yaw_from_quaternion


class Q:
    """Заглушка кватерниона с полями geometry_msgs/Quaternion."""

    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.x, self.y, self.z, self.w = x, y, z, w


def quat_from_yaw(yaw):
    return Q(0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def test_yaw_identity():
    assert yaw_from_quaternion(Q()) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize('yaw_deg', [-179, -90, -45, 0, 30, 90, 170])
def test_yaw_roundtrip(yaw_deg):
    yaw = math.radians(yaw_deg)
    assert yaw_from_quaternion(quat_from_yaw(yaw)) == pytest.approx(yaw, abs=1e-6)


def test_yaw_wraps_at_pi():
    q = quat_from_yaw(math.pi)
    assert abs(yaw_from_quaternion(q)) == pytest.approx(math.pi, abs=1e-6)
