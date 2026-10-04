"""
pib_grasp — Isaac-Lab-Greifaufgabe der realen linken pib-v5-Hand (Proof of Concept).

Registriert die Gym-Tasks. Nur String-Einstiegspunkte: dieses Modul wird vor dem Start
der Isaac-Sim-App importiert (isaac_lab/train.py), die Configs erst danach.
"""
import gymnasium as gym

gym.register(
    id="Pib-Grasp-Hand-Left-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "pib_grasp.env_cfg:PibGraspEnvCfg",
        "rsl_rl_cfg_entry_point": "pib_grasp.agents.rsl_rl_ppo_cfg:PibGraspPPORunnerCfg",
    },
)

gym.register(
    id="Pib-Grasp-Hand-Left-Play-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": "pib_grasp.env_cfg:PibGraspEnvCfg_PLAY",
        "rsl_rl_cfg_entry_point": "pib_grasp.agents.rsl_rl_ppo_cfg:PibGraspPPORunnerCfg",
    },
)
