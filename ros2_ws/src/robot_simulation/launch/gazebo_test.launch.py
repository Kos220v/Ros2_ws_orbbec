import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    sim = get_package_share_directory('robot_simulation')
    nav = get_package_share_directory('robot_navigation')
    route = LaunchConfiguration('waypoints_file')
    world = os.path.join(sim, 'worlds', 'outdoor_test.sdf')
    bridge = os.path.join(sim, 'config', 'bridge.yaml')
    urdf = os.path.join(sim, 'urdf', 'sim_robot.urdf')
    with open(urdf, encoding='utf-8') as f:
        description = f.read()
    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': ['-r ', world]}.items())
    bridge_node = Node(package='ros_gz_bridge', executable='parameter_bridge', name='sim_bridge', output='screen', parameters=[{'config_file': bridge}])
    rsp = Node(package='robot_state_publisher', executable='robot_state_publisher', name='robot_state_publisher_sim', parameters=[{'robot_description': description, 'use_sim_time': True}])
    mux = Node(package='cmd_switcher', executable='cmd_mux_node', name='cmd_switcher_sim', output='screen')
    localization = IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(nav, 'launch', 'localization.launch.py')), launch_arguments={'use_sim_time': 'true'}.items())
    navigation = IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(nav, 'launch', 'navigation.launch.py')), launch_arguments={'use_sim_time': 'true'}.items())
    commander = Node(package='robot_navigation', executable='gps_waypoint_commander', name='gps_waypoint_commander', output='screen', parameters=[{'waypoints_file': route, 'autostart': True, 'use_rc_mode': False, 'require_gps_fix': True}])
    return LaunchDescription([
        DeclareLaunchArgument('waypoints_file', default_value=os.path.join(sim, 'config', 'sim_route.yaml')),
        gz, bridge_node, rsp, mux,
        TimerAction(period=5.0, actions=[localization]),
        TimerAction(period=10.0, actions=[navigation]),
        TimerAction(period=20.0, actions=[commander]),
    ])
