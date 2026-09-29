from dataclasses import dataclass
@dataclass(frozen=True)
class SafetyLimits:
    max_spm: float=3.0; min_spm: float=.5; max_vfd_hz: float=50.; min_vfd_hz: float=10.; max_stroke_in: float=86.; min_stroke_in: float=48.; max_injection_pressure_psi: float=2400.; max_rod_load_lbf: float=24600.; max_torque_lbf_ft: float=320000/12
@dataclass(frozen=True)
class ModelConfig:
    random_state:int=42; min_training_rows:int=40; forecast_horizon_days:int=7
SAFETY=SafetyLimits(); MODEL=ModelConfig()
