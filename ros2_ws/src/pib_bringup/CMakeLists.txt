cmake_minimum_required(VERSION 3.8)
project(pib_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(pib_bringup)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  pib_bringup/test_client_pickup.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME test_client_pickup
)

install(PROGRAMS
  pib_bringup/test_client_putdown.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME test_client_putdown
)

install(PROGRAMS
  pib_bringup/test_client_pickup_v5.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME test_client_pickup_v5
)

install(PROGRAMS
  pib_bringup/test_client_putdown_v5.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME test_client_putdown_v5
)

ament_package()
