"""
pib_sim_v5.launch.py — Startet den kompletten ros2_control-Stack für Isaac Sim (v5-Hand).

Identisch zu pib_sim.launch.py, nur gegen pib_description_v5/controllers_v5.yaml statt
der v4-Pendants — siehe dort für Details. Nicht gleichzeitig mit pib_sim.launch.py starten,
beide nutzen dieselben /pib/hw/*-Topics (immer nur eine Isaac-Sim-Stage — v4 oder v5 — aktiv).

Voraussetzung: Isaac Sim läuft, pib_upperbody_v5.usd (mit Action Graph) geladen,
start.py ausgeführt, Play gedrückt.

Start:
  source /opt/ros/jazzy/setup.bash
  source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
  ros2 launch pib_bringup pib_sim_v5.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


def generate_launch_description():
    # URDF einlesen
    urdf_path = os.path.join(
        get_package_share_directory("pib_description_v5"),
        "urdf", "pib_upperbody_v5.urdf"
    )
    with open(urdf_path, "r") as f:
        robot_description = f.read()

    # Controller-Konfiguration
    controllers_yaml = os.path.join(
        get_package_share_directory("pib_bringup"),
        "config", "controllers_v5.yaml"
    )

    # robot_state_publisher — publiziert URDF auf /robot_description Topic
    # (Jazzy: controller_manager subscribed Topic statt Parameter zu lesen)
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    # Controller Manager
    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            {"robot_description": robot_description},
            controllers_yaml,
        ],
        output="screen",
    )

    # JointStateBroadcaster spawnen
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )

    # JointTrajectoryController spawnen — erst nach JointStateBroadcaster
    joint_trajectory_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller"],
    )

    delay_jtc = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[joint_trajectory_controller_spawner],
        )
    )

    return LaunchDescription([
        robot_state_publisher,
        controller_manager,
        joint_state_broadcaster_spawner,
        delay_jtc,
    ])
