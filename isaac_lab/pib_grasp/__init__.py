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

# Trainingsvarianten für Experimente (Bewertung immer in Pib-Grasp-Hand-Left-v0, eval-v1)
for _name, _cfg in (("FingerCount", "PibGraspEnvCfg_FingerCount"), ("Heavy", "PibGraspEnvCfg_Heavy"),
                   ("HeavyDexsuite", "PibGraspEnvCfg_HeavyDexsuite"), ("HeavyMulti", "PibGraspEnvCfg_HeavyMulti"),
                   ("HeavyMultiRand", "PibGraspEnvCfg_HeavyMultiRand"), ("HeavyMultiADR", "PibGraspEnvCfg_HeavyMultiADR")):
    gym.register(
        id=f"Pib-Grasp-Hand-Left-{_name}-v0",
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"pib_grasp.env_cfg:{_cfg}",
            "rsl_rl_cfg_entry_point": "pib_grasp.agents.rsl_rl_ppo_cfg:PibGraspPPORunnerCfg",
        },
    )

# ADR-022 (EXP-019–022): je Variante Env-Konfiguration × Agenten-Konfiguration (Clip = Aktionen auf [−1, 1])
for _name, _cfg, _agent in (("HeavyMultiProgress", "PibGraspEnvCfg_HeavyMultiProgress", "PibGraspPPORunnerCfg"),
                            ("HeavyMultiClip", "PibGraspEnvCfg_HeavyMulti", "PibGraspPPORunnerCfg_Clip"),
                            ("HeavyMultiPriv", "PibGraspEnvCfg_HeavyMultiPriv", "PibGraspPPORunnerCfg"),
                            ("HeavyMultiProgressClip", "PibGraspEnvCfg_HeavyMultiProgress", "PibGraspPPORunnerCfg_Clip"),
                            ("HeavyMultiProgressClipXY", "PibGraspEnvCfg_HeavyMultiProgressXY", "PibGraspPPORunnerCfg_Clip"),
                            # Nachtlauf 2026-10-11 (EXP-024–026): je eine Änderung ggü. EXP-022
                            ("HeavyMultiProgressClipFilter", "PibGraspEnvCfg_HeavyMultiProgressFilter", "PibGraspPPORunnerCfg_Clip"),
                            ("HeavyMultiProgressClipTorque", "PibGraspEnvCfg_HeavyMultiProgressTorque", "PibGraspPPORunnerCfg_Clip"),
                            ("HeavyMultiProgressClipFingers", "PibGraspEnvCfg_HeavyMultiProgressFingers", "PibGraspPPORunnerCfg_Clip")):
    gym.register(
        id=f"Pib-Grasp-Hand-Left-{_name}-v0",
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"pib_grasp.env_cfg:{_cfg}",
            "rsl_rl_cfg_entry_point": f"pib_grasp.agents.rsl_rl_ppo_cfg:{_agent}",
        },
    )

# Greifart „von oben“ (Stufe 4b, docs/plan-griff-von-oben.md): Basisaufgabe für die Bewertung, Trainingsvarianten mit
# dem EXP-022-Rezept (Fortschritt, Aktionen auf ±1)
for _name, _cfg, _agent in (("Oben", "PibGraspEnvCfg_Oben", "PibGraspPPORunnerCfg_Clip"),
                            ("ObenMulti", "PibGraspEnvCfg_ObenMulti", "PibGraspPPORunnerCfg_Clip"),
                            ("ObenMultiXY", "PibGraspEnvCfg_ObenMultiXY", "PibGraspPPORunnerCfg_Clip")):
    gym.register(
        id=f"Pib-Grasp-Hand-Left-{_name}-v0",
        entry_point="isaaclab.envs:ManagerBasedRLEnv",
        disable_env_checker=True,
        kwargs={
            "env_cfg_entry_point": f"pib_grasp.env_cfg_oben:{_cfg}",
            "rsl_rl_cfg_entry_point": f"pib_grasp.agents.rsl_rl_ppo_cfg:{_agent}",
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
