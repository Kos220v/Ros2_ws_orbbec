#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'astra_odometry'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'),
            glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@example.com',
    description='Визуальная одометрия RTAB-Map (rgbd_odometry) с камеры Orbbec '
                'Astra. Замена колёсной одометрии + IMU + компаса.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'odom_monitor = astra_odometry.odom_monitor:main',
        ],
    },
)
