cmake_minimum_required(VERSION 3.8)
project(astra_odometry)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclpy REQUIRED)

# Install the python package (astra_odometry/)
ament_python_install_package(${PROJECT_NAME})

# Console-script style entry point: `ros2 run astra_odometry odom_monitor`
install(PROGRAMS
  astra_odometry/odom_monitor.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME odom_monitor
)

# Shell helper: `ros2 run astra_odometry check_odometry.sh` (or run directly)
install(PROGRAMS
  scripts/check_odometry.sh
  DESTINATION lib/${PROJECT_NAME}
)

# Launch / config / rviz resources
install(DIRECTORY
  launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  find_package(ament_lint_auto REQUIRED)

  # pure-python unit + lint tests
  ament_add_pytest_test(odom_monitor_test test/test_odom_monitor.py
    TIMEOUT 60
  )
  ament_add_pytest_test(flake8_test test/test_flake8.py TIMEOUT 60)
  ament_add_pytest_test(pep257_test test/test_pep257.py TIMEOUT 60)
endif()

ament_package()
