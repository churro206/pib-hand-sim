# config/server_config.py — ROS2-Server-Konfiguration
#
# Wird von isaac_sim/ros2_server.py via _load_mod geladen.
# Änderungen wirken nach erneutem Ausführen von ros2_server.py (hot-reload).

CONTROL_MODE = "direct"   # "direct" | "servo" | "nn"
SIDE         = "right"    # für servo/nn: "left" | "right"

# Winkeleinheit für ROS2-Topics.
# ROS2-Standard (sensor_msgs/JointState, trajectory_msgs/JointTrajectory) ist "rad".
# "deg" als Platzhalter bis Abstimmung mit IK-Team.
ANGLE_UNIT = "deg"        # "deg" | "rad"

# Topics
TOPIC_JOINT_TRAJECTORY = "/pib/joint_trajectory"
TOPIC_SET_MODE         = "/pib/set_mode"
TOPIC_JOINT_STATES     = "/pib/joint_states"
TOPIC_GRASP_STATE      = "/pib/grasp_state"

# Publish-Rate für /pib/joint_states und /pib/grasp_state
PUBLISH_HZ = 30.0
