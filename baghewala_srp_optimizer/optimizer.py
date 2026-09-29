
from dataclasses import dataclass
import numpy as np
from srp_formulas import (
    pump_displacement_bpd, pump_efficiency, rod_string_weight_submerged_lbf,
    fluid_load_lbf, rod_float_indicator, impact_index
)


@dataclass
class OptimizationInputs:
    plunger_d_in: float
    rod_d_in: float
    rod_length_m: float
    fluid_density_kg_m3: float
    differential_pressure_psi: float
    actual_efficiency_baseline: float
    current_oil_rate_bpd: float
    current_stroke_in: float
    current_spm: float
    min_prl_lbf: float
    max_prl_lbf: float
    max_spm: float = 4.0
    min_spm: float = 1.0
    stroke_min_in: float = 24.0
    stroke_max_in: float = 120.0
    float_limit: float = 0.10
    impact_limit: float = 100.0


def optimize(x: OptimizationInputs, steps=25):
    rod_wt = rod_string_weight_submerged_lbf(
        x.rod_d_in, x.rod_length_m, x.fluid_density_kg_m3
    )
    fl = fluid_load_lbf(x.plunger_d_in, x.differential_pressure_psi)

    best = None
    candidates = []

    for stroke in np.linspace(x.stroke_min_in, x.stroke_max_in, steps):
        for spm in np.linspace(x.min_spm, x.max_spm, steps):
            q_theory = pump_displacement_bpd(x.plunger_d_in, stroke, spm)

            # Baseline efficiency is deliberately used as a calibration prior.
            # A future ML/calibration layer should replace this assumption.
            eff = min(1.0, max(0.05, x.actual_efficiency_baseline))

            q_liquid = q_theory * eff
            oil_rate = q_liquid  # water-cut correction can be added when history exists

            # Conservative heuristic scaling of load swing with speed/stroke.
            speed_factor = spm / max(x.current_spm, 0.1)
            stroke_factor = stroke / max(x.current_stroke_in, 0.1)
            swing = max(0.0, x.max_prl_lbf - x.min_prl_lbf) * speed_factor * stroke_factor

            min_load_est = x.min_prl_lbf - 0.10 * swing
            max_load_est = x.max_prl_lbf + 0.10 * swing

            fidx = rod_float_indicator(min_load_est, rod_wt, fl)
            iidx = impact_index(max_load_est, min_load_est, stroke, spm)

            # Objective: production + moderate efficiency preference - risk penalties.
            risk_penalty = max(0, fidx - x.float_limit) * 500
            risk_penalty += max(0, iidx - x.impact_limit) * 2
            objective = oil_rate - risk_penalty

            feasible = (fidx <= x.float_limit and iidx <= x.impact_limit)
            candidates.append({
                "stroke_in": float(stroke),
                "spm": float(spm),
                "predicted_oil_bpd": float(oil_rate),
                "predicted_efficiency": float(eff),
                "float_index": float(fidx),
                "impact_index": float(iidx),
                "objective": float(objective),
                "feasible": feasible
            })

            if feasible and (best is None or objective > best["objective"]):
                best = candidates[-1]

    if best is None:
        best = min(candidates, key=lambda z: z["float_index"] + z["impact_index"] / 100)

    best["explanation"] = (
        "Recommendation maximizes modeled production while enforcing configured "
        "rod-float and impact-risk limits. It is a constrained engineering heuristic; "
        "calibrate it with actual Baghewala dynamometer, VFD, production and failure data "
        "before field use."
    )
    return best, candidates
