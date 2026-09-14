cmake_minimum_required(VERSION 3.8)
project(astra_gazebo)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch worlds config rviz urdf
  DESTINATION share/${PROJECT_NAME}
)

# Python-скрипты (ретранслятор эталонной одометрии и пр.)
install(
  PROGRAMS
    scripts/ground_truth_to_odom.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
