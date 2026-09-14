#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Чистые математические помощники для одометрии (без зависимостей от ROS)."""

import math


def yaw_from_quaternion(q) -> float:
    """Извлекает курс (yaw, поворот вокруг Z) из объекта с полями .x/.y/.z/.w.

    Работает с geometry_msgs/Quaternion и с любым duck-typed объектом в тестах.
    """
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)
