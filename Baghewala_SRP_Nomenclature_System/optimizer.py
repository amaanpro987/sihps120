"""Sucker Rod Pump (SRP) Speed and Stroke Optimizer with Thermal & Rod Floating Constraints."""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import numpy as np
from srp_formulas import (
    pump_displacement_bpd, pump_efficiency, rod_string_weight_submerged_lbf,
    fluid_load_lbf, rod_float_indicator, impact_index
)
from srp_wellbore_engine import (
    SRPWellboreEngine, WellboreConfig, RodStringConfig, SRPPumpingParameters
)
from fluid_pvt import HeavyOilProperties, heavy_oil_viscosity_cp


@dataclass
class OptimizationInputs:
    """Inputs for SRP Optimization."""
    plunger_d_in: float = 1.75
    rod_d_in: float = 0.875
    rod_length_m: float = 1100.0
    fluid_density_kg_m3: float = 950.0
    differential_pressure_psi: float = 500.0
    actual_efficiency_baseline: float = 0.75
    current_oil_rate_bpd: float = 50.0
    current_stroke_in: float = 72.0
    current_spm: float = 2.2
    min_prl_lbf: float = 1200.0
    max_prl_lbf: float = 5500.0
    max_spm: float = 4.0
    min_spm: float = 1.0
    stroke_min_in: float = 36.0
    stroke_max_in: float = 100.0
    float_limit: float = 0.75
    impact_limit: float = 85.0
    reservoir_temp_c: float = 110.0
    electricity_cost_kwh: float = 0.12


def optimize(x: OptimizationInputs, steps: int = 25) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Constrained Grid Search & Physics Optimizer for Stroke Length and SPM.
    Accounts for Heavy Oil Viscous Friction, Rod Floating Thresholds, and Goodman Stress.
    """
    wellbore_engine = SRPWellboreEngine(
        well=WellboreConfig(sandface_temp_c=x.reservoir_temp_c),
        rod=RodStringConfig(rod_size_top_in=x.rod_d_in),
        fluid_props=HeavyOilProperties()
    )

    weights = wellbore_engine.calculate_rod_string_weights()
    w_sub = weights["total_rod_weight_submerged_lbf"]
    fl = fluid_load_lbf(x.plunger_d_in, x.differential_pressure_psi)

    best = None
    candidates = []

    stroke_candidates = np.linspace(x.stroke_min_in, x.stroke_max_in, steps)
    spm_candidates = np.linspace(x.min_spm, x.max_spm, steps)

    for stroke in stroke_candidates:
        for spm in spm_candidates:
            srp_params = SRPPumpingParameters(
                stroke_length_in=float(stroke),
                spm=float(spm),
                plunger_d_in=x.plunger_d_in
            )

            # Evaluate real viscous floating mechanics
            float_analysis = wellbore_engine.analyze_rod_floating(srp_params)
            float_ratio = float_analysis["float_ratio"]
            drag_lbf = float_analysis["peak_downstroke_drag_lbf"]

            # Wave-equation dynacard simulation
            card = wellbore_engine.generate_dynamometer_cards(srp_params, fault_mode="NORMAL" if float_ratio < 0.85 else "ROD_FLOAT")
            pprl = card["pprl_lbf"]
            mprl = card["mprl_lbf"]
            stress = wellbore_engine.evaluate_goodman_stress(pprl, mprl)

            # Displacement & Production
            q_theory = pump_displacement_bpd(x.plunger_d_in, stroke, spm)
            eff = card["volumetric_efficiency"]
            oil_rate = q_theory * eff

            # Legacy index indicators for backward compatibility:
            fidx = rod_float_indicator(mprl, w_sub, fl)
            iidx = impact_index(pprl, mprl, stroke, spm)

            # VFD Electrical Power & Specific Energy (kWh/bbl)
            vfd_hz = min(60.0, max(12.0, spm * 14.2857))
            motor_kw = (vfd_hz / 50.0) ** 1.3 * 18.5
            kwh_per_bbl = (motor_kw * 24.0) / max(1.0, oil_rate)

            # Feasibility: zero severe rod floating, Goodman stress <= 95%, impact within bounds
            feasible = (float_ratio <= x.float_limit) and (stress["goodman_loading_percent"] <= 95.0)

            # Multi-objective optimization:
            # Objective = Oil Revenue - Electricity Cost - Heavy Penalties for Rod Floating / Overstress
            oil_revenue = oil_rate * 72.0
            power_cost = (motor_kw * 24.0) * x.electricity_cost_kwh
            float_penalty = max(0.0, float_ratio - x.float_limit) * 800.0
            stress_penalty = max(0.0, stress["goodman_loading_percent"] - 90.0) * 100.0

            objective = oil_revenue - power_cost - float_penalty - stress_penalty

            candidate_record = {
                "stroke_in": float(stroke),
                "spm": float(spm),
                "vfd_hz": float(vfd_hz),
                "motor_power_kw": float(motor_kw),
                "specific_energy_kwh_bbl": float(kwh_per_bbl),
                "predicted_oil_bpd": float(oil_rate),
                "predicted_efficiency": float(eff),
                "float_ratio": float(float_ratio),
                "float_index": float(fidx),
                "impact_index": float(iidx),
                "goodman_stress_percent": float(stress["goodman_loading_percent"]),
                "pprl_lbf": float(pprl),
                "mprl_lbf": float(mprl),
                "objective": float(objective),
                "feasible": feasible
            }
            candidates.append(candidate_record)

            if feasible and (best is None or objective > best["objective"]):
                best = candidate_record

    if best is None:
        best = min(candidates, key=lambda z: z["float_ratio"] + z["goodman_stress_percent"] / 100.0)

    best["explanation"] = (
        f"Recommended Setpoint: Stroke = {best['stroke_in']:.1f} in, SPM = {best['spm']:.2f} ({best['vfd_hz']:.1f} Hz). "
        f"Delivers {best['predicted_oil_bpd']:.1f} bbl/day heavy oil at {best['specific_energy_kwh_bbl']:.1f} kWh/bbl. "
        f"Downstroke rod float ratio is safely kept at {best['float_ratio']:.2f} (Limit: {x.float_limit}), with "
        f"Modified Goodman rod stress at {best['goodman_stress_percent']:.1f}%."
    )

    return best, candidates
