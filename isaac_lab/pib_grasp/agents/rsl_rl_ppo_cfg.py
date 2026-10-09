"""PPO-Konfiguration (rsl_rl) — Werte aus Dexsuite (DexsuiteKukaAllegroPPORunnerCfg),
Netze kleiner: die Policy soll int8-quantisiert auf der NPU des STM32N657 laufen."""
from isaaclab.utils import configclass

from isaaclab_rl.rsl_rl import RslRlOnPolicyRunnerCfg, RslRlPpoActorCriticCfg, RslRlPpoAlgorithmCfg


@configclass
class PibGraspPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    num_steps_per_env = 32
    # Asymmetric Actor-Critic: Actor nur reale Sensoren, Critic zusätzlich privilegiert
    obs_groups = {"policy": ["policy"], "critic": ["policy", "critic"]}
    max_iterations = 3000
    save_interval = 100
    experiment_name = "pib_grasp_hand_left"
    policy = RslRlPpoActorCriticCfg(
        init_noise_std=1.0,
        actor_obs_normalization=True,
        critic_obs_normalization=True,
        actor_hidden_dims=[256, 128, 64],
        critic_hidden_dims=[512, 256, 128],
        activation="elu",
    )
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.2,
        entropy_coef=0.005,
        num_learning_epochs=5,
        num_mini_batches=4,
        learning_rate=1.0e-3,
        schedule="adaptive",
        gamma=0.99,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=1.0,
    )


@configclass
class PibGraspPPORunnerCfg_Clip(PibGraspPPORunnerCfg):
    """EXP-020/022: Aktionen auf [−1, 1] begrenzt (rsl_rl-Wrapper, Isaac Lab clip_actions). NVIDIAs Dexsuite hält den
    Mittelwert der Policy im rl_games-Setup per bounds_loss (soft bound 1,1) — rsl_rl hat das nicht, ohne Begrenzung
    überzieht die Policy weit über die Servo-Sättigung (|a| 2–3, ADR-022). 1 · Skala 0,1 rad > 5° Sättigungsfehler:
    volle Kraft bleibt erreichbar. Firmware: Netzausgabe ebenso auf [−1, 1] begrenzen."""
    clip_actions = 1.0
