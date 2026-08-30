# rgbd_odometry.launch.py
#
# RTAB-Map visual odometry (rgbd_odometry) fed by the Astra RGB-D stream.
# ONLY odometry is produced here -- no mapping, no SLAM.
#
# Subscribes (remapped from the astra_camera topics):
#   rgb/image        <- /camera/color/image_raw
#   depth/image      <- /camera/depth/image_raw   (registered to color)
#   rgb/camera_info  <- /camera/color/camera_info
#
# Publishes:
#   /odom            nav_msgs/Odometry
#   TF: odom -> base_footprint   (when publish_tf:=true)
#
# Args:
#   use_sim_time (bool)
#   publish_tf   (bool)  publish odom->base TF               [default true]
#   frame_id     (str)   robot base frame                     [default base_footprint]
#   odom_frame_id(str)   odometry frame                       [default odom]
#   approx_sync  (bool)  approximate time sync of rgb/depth   [default true]
#   qos          (int)   image QoS (0 system default,1 reliable,2 best effort)
#   rgb_topic / depth_topic / camera_info_topic remaps

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    publish_tf = LaunchConfiguration('publish_tf')
    frame_id = LaunchConfiguration('frame_id')
    odom_frame_id = LaunchConfiguration('odom_frame_id')
    approx_sync = LaunchConfiguration('approx_sync')
    qos = LaunchConfiguration('qos')

    rgb_topic = LaunchConfiguration('rgb_topic')
    depth_topic = LaunchConfiguration('depth_topic')
    camera_info_topic = LaunchConfiguration('camera_info_topic')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('publish_tf', default_value='true'),
        DeclareLaunchArgument('frame_id', default_value='base_footprint'),
        DeclareLaunchArgument('odom_frame_id', default_value='odom'),
        DeclareLaunchArgument('approx_sync', default_value='true'),
        DeclareLaunchArgument('qos', default_value='2'),
        DeclareLaunchArgument('rgb_topic', default_value='/camera/color/image_raw'),
        DeclareLaunchArgument('depth_topic', default_value='/camera/depth/image_raw'),
        DeclareLaunchArgument('camera_info_topic',
                              default_value='/camera/color/camera_info'),

        Node(
            package='rtabmap_odom',
            executable='rgbd_odometry',
            name='rgbd_odometry',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'frame_id': frame_id,
                'odom_frame_id': odom_frame_id,
                'publish_tf': publish_tf,
                'approx_sync': approx_sync,
                'qos': qos,
                'qos_camera_info': qos,
                'wait_for_transform': 0.2,
                'subscribe_rgbd': False,
                # --- RTAB-Map odometry tuning (feature-based F2M) ---
                'Odom/Strategy': '0',          # 0=Frame-to-Map, 1=Frame-to-Frame
                'Vis/FeatureType': '6',        # 6=GFTT/BRIEF (fast, robust)
                'OdomF2M/MaxSize': '1000',
                'Vis/MaxFeatures': '600',
                'Odom/ResetCountdown': '1',    # auto-reset after lost tracking
                'Odom/GuessMotion': 'true',
            }],
            remappings=[
                ('rgb/image', rgb_topic),
                ('depth/image', depth_topic),
                ('rgb/camera_info', camera_info_topic),
                ('odom', '/odom'),
            ],
        ),
    ])
