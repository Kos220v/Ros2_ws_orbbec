# astra_camera.launch.py
#
# Thin wrapper that starts the Orbbec Astra (OpenNI) driver from the
# `astra_camera` package and makes sure depth<->color registration is on so
# that RGB and depth pixels line up (required for RGB-D visual odometry).
#
# The upstream driver (github.com/orbbec/ros2_astra_camera) ships an
# `astra.launch.xml`. We include it and override the parameters we care about.
# If your driver package uses a different launch file name, set `driver_launch`.
#
# Published topics (default `camera` namespace):
#   /camera/color/image_raw          sensor_msgs/Image
#   /camera/color/camera_info        sensor_msgs/CameraInfo
#   /camera/depth/image_raw          sensor_msgs/Image   (registered to color)
#   /camera/depth/camera_info        sensor_msgs/CameraInfo

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import AnyLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Path to the upstream astra driver launch file.
    driver_launch = LaunchConfiguration('driver_launch')

    astra_launch_path = PathJoinSubstitution([
        FindPackageShare('astra_camera'), 'launch', driver_launch
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'driver_launch',
            default_value='astra.launch.xml',
            description='Launch file inside the astra_camera package to include '
                        '(e.g. astra.launch.xml, astra_mini.launch.xml).'),

        LogInfo(msg=['[astra_camera.launch.py] Including astra_camera driver: ',
                     driver_launch]),

        IncludeLaunchDescription(
            AnyLaunchDescriptionSource(astra_launch_path),
            launch_arguments={
                # Align depth to color so pixels correspond (needed for RGB-D VO)
                'depth_registration': 'true',
                'enable_colored_point_cloud': 'false',
                'enable_point_cloud': 'false',
                # keep frame names consistent with our URDF
                'camera_name': 'camera',
            }.items(),
        ),
    ])
