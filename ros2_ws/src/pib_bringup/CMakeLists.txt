cmake_minimum_required(VERSION 3.8)
project(pib_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(pib_bringup)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  pib_bringup/test_client.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
