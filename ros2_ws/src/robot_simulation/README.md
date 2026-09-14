# robot_simulation

Gazebo Harmonic simulation for the current navigation architecture. It does not
start any real USB-UART, VESC, GPS, IMU or LiDAR hardware.

## Run on Ubuntu 24.04 / ROS 2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select robot_simulation
source install/setup.bash
ros2 launch robot_simulation gazebo_test.launch.py
```

Check `/imu/data`, `/gps/fix`, `/wheel/odometry`, `/scan` and the Nav2 lifecycle
nodes before testing a route. The default simulation route is in
`config/sim_route.yaml`.
