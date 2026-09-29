"""AI Machine Learning Diagnostic and Autonomous Closed-Loop Controller Module.

Includes:
- Feature extraction from Surface and Downhole Dynamometer Cards
- Supervised Machine Learning Classifier for 6 Dynacard anomaly fault modes
- Dynamic Closed-Loop VFD/SRP Speed Optimizer tracking reservoir thermal state
- Real-time explainable diagnostic recommendations
"""

import math
from typing import Dict, List, Tuple, Any
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from srp_wellbore_engine import SRPWellboreEngine, SRPPumpingParameters


FAULT_CLASSES = [
    "NORMAL",
    "ROD_FLOAT",
    "FLUID_POUND",
    "GAS_INTERFERENCE",
    "PUMP_UNSETTING",
    "UNANCHORED_TUBING"
]

FAULT_DESCRIPTIONS = {
    "NORMAL": "Optimal pumping condition. Full barrel fillage, minimal dynamic slap, and excellent volumetric efficiency.",
    "ROD_FLOAT": "Heavy crude viscous friction opposes downstroke rod descent, causing rod slack, compression, and impact loading at bottom.",
    "FLUID_POUND": "Pump barrel is partially filled with liquid; plunger drops through void and violently strikes fluid level on downstroke.",
    "GAS_INTERFERENCE": "Free gas entering pump barrel creates elastic compression/expansion loops, delaying valve opening and reducing displacement.",
    "PUMP_UNSETTING": "Travelling/Standing valve leakage or upward mechanical unseating force causing pump slippage and lift degradation.",
    "UNANCHORED_TUBING": "Tubing string stretches during upstroke due to fluid load transfer, producing a tilted parallelogram dynacard."
}


def extract_dynacard_features(pos_list: List[float], load_list: List[float]) -> np.ndarray:
    """
    Extract geometric, dynamic, and statistical features from a dynamometer card (pos, load).
    """
    pos = np.array(pos_list)
    load = np.array(load_list)

    s_max = np.max(pos)
    s_min = np.min(pos)
    stroke = max(1.0, s_max - s_min)

    l_max = np.max(load)
    l_min = np.min(load)
    load_range = max(1.0, l_max - l_min)

    # Normalize coordinates to [0, 1]
    norm_pos = (pos - s_min) / stroke
    norm_load = (load - l_min) / load_range

    # 1. Area (Hydraulic work coefficient)
    if hasattr(np, "trapezoid"):
        norm_area = float(np.abs(np.trapezoid(norm_load, norm_pos)))
    else:
        norm_area = float(np.abs(np.trapz(norm_load, norm_pos)))

    # 2. Aspect and load ratios
    load_ratio = float(l_min / max(1.0, l_max))

    # 3. Quadrant distributions (Split into 4 quadrants in normalized space)
    q1 = float(np.sum((norm_pos >= 0.5) & (norm_load >= 0.5)) / len(pos))
    q2 = float(np.sum((norm_pos < 0.5) & (norm_load >= 0.5)) / len(pos))
    q3 = float(np.sum((norm_pos < 0.5) & (norm_load < 0.5)) / len(pos))
    q4 = float(np.sum((norm_pos >= 0.5) & (norm_load < 0.5)) / len(pos))

    # 4. Downstroke delayed rebound ratio (Indices where position is decreasing)
    d_pos = np.diff(pos)
    downstroke_indices = np.where(d_pos < 0)[0]
    if len(downstroke_indices) > 5:
        dn_loads = norm_load[downstroke_indices]
        dn_slope_mean = float(np.mean(np.diff(dn_loads)))
        dn_load_min = float(np.min(dn_loads))
    else:
        dn_slope_mean = 0.0
        dn_load_min = float(norm_load[0])

    # 5. Upstroke slope variance
    upstroke_indices = np.where(d_pos > 0)[0]
    if len(upstroke_indices) > 5:
        up_loads = norm_load[upstroke_indices]
        up_load_max = float(np.max(up_loads))
        up_variance = float(np.var(up_loads))
    else:
        up_load_max = 1.0
        up_variance = 0.0

    # 6. Kurtosis and skewness approximations of load
    load_mean = float(np.mean(norm_load))
    load_std = float(np.std(norm_load))
    load_skew = float(np.mean(((norm_load - load_mean) / max(0.001, load_std)) ** 3))

    features = np.array([
        norm_area,
        load_ratio,
        q1, q2, q3, q4,
        dn_slope_mean,
        dn_load_min,
        up_load_max,
        up_variance,
        load_skew,
        float(l_max / 10000.0),
        float(l_min / 5000.0)
    ])
    return features


class AIDynacardClassifier:
    """Trained machine learning classifier for automatic Dynacard pattern recognition."""

    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=12)
        self.is_trained = False
        self._train_baseline_model()

    def _train_baseline_model(self):
        """Generate synthetic training dataset across operational regimes and fit model."""
        engine = SRPWellboreEngine()
        x_train = []
        y_train = []

        # Generate cards across various strokes (36-120 in), SPM (1.0-4.5), and all 6 fault modes
        for fault_idx, mode in enumerate(FAULT_CLASSES):
            for stroke in [48.0, 64.0, 72.0, 86.0, 100.0]:
                for spm in [1.2, 1.8, 2.2, 2.8, 3.5]:
                    for plunger_d in [1.5, 1.75, 2.0, 2.25]:
                        srp = SRPPumpingParameters(stroke_length_in=stroke, spm=spm, plunger_d_in=plunger_d)
                        card = engine.generate_dynamometer_cards(srp, fault_mode=mode, n_points=80)
                        feat = extract_dynacard_features(card["surface_position_in"], card["surface_load_lbf"])
                        x_train.append(feat)
                        y_train.append(fault_idx)

        x_arr = np.array(x_train)
        y_arr = np.array(y_train)
        self.model.fit(x_arr, y_arr)
        self.is_trained = True

    def classify_dynacard(self, pos_list: List[float], load_list: List[float]) -> Dict[str, Any]:
        """Classifies a given dynacard, returning class, confidence probabilities, and explanation."""
        feat = extract_dynacard_features(pos_list, load_list).reshape(1, -1)
        pred_idx = int(self.model.predict(feat)[0])
        probs = self.model.predict_proba(feat)[0]

        pred_class = FAULT_CLASSES[pred_idx]
        confidence = float(probs[pred_idx] * 100.0)

        prob_dict = {FAULT_CLASSES[i]: float(probs[i] * 100.0) for i in range(len(FAULT_CLASSES))}

        # Determine urgency and action
        if pred_class == "NORMAL":
            action = "Maintain current operating parameters. System is operating at peak volumetric efficiency."
            status_level = "SUCCESS"
        elif pred_class == "ROD_FLOAT":
            action = "Reduce VFD speed (SPM) or add sinker bars to upper string to eliminate downstroke floating and prevent rod buckling."
            status_level = "CRITICAL"
        elif pred_class == "FLUID_POUND":
            action = "Slow pump SPM by 20-30% to match dynamic reservoir inflow and eliminate fluid pound impact stresses."
            status_level = "WARNING"
        elif pred_class == "GAS_INTERFERENCE":
            action = "Increase pump submergence or install downhole gas separator to prevent gas locking."
            status_level = "WARNING"
        elif pred_class == "PUMP_UNSETTING":
            action = "Inspect pump seating nipple / anchor. Check travelling valve seal and hold-down force balance."
            status_level = "CRITICAL"
        else:
            action = "Anchor tubing string at bottom to eliminate tubing breathing and recover lost stroke displacement."
            status_level = "WARNING"

        return {
            "predicted_class": pred_class,
            "confidence_percent": confidence,
            "probabilities": prob_dict,
            "description": FAULT_DESCRIPTIONS[pred_class],
            "corrective_action": action,
            "status_level": status_level
        }


class ClosedLoopVFDController:
    """
    Autonomous Closed-Loop Controller for Sucker Rod Pumping VFDs.
    Continuously optimizes VFD Hz and SPM based on reservoir thermal decline and dynacard feedback.
    """

    def __init__(self, wellbore_engine: SRPWellboreEngine = None):
        self.wellbore_engine = wellbore_engine or SRPWellboreEngine()

    def calculate_optimal_speed_setpoint(
        self,
        reservoir_temp_c: float,
        current_spm: float,
        stroke_length_in: float = 72.0,
        plunger_d_in: float = 1.75,
        target_float_margin: float = 0.75
    ) -> Dict[str, Any]:
        """
        Computes the target VFD frequency (Hz) and SPM that maximizes production without triggering rod floating.
        """
        # Viscosity as a function of current reservoir / wellhead temp
        self.wellbore_engine.well.sandface_temp_c = reservoir_temp_c
        weights = self.wellbore_engine.calculate_rod_string_weights()
        w_sub = weights["total_rod_weight_submerged_lbf"]

        # Search optimal SPM in range [0.8, 4.5]
        spm_range = np.linspace(0.8, 4.5, 38)
        best_spm = 1.0
        best_rate = 0.0
        selected_drag = 0.0
        selected_float_ratio = 0.0

        for test_spm in spm_range:
            srp = SRPPumpingParameters(
                stroke_length_in=stroke_length_in,
                spm=test_spm,
                plunger_d_in=plunger_d_in
            )
            float_res = self.wellbore_engine.analyze_rod_floating(srp)
            fr = float_res["float_ratio"]

            if fr <= target_float_margin:
                theo_bpd = 0.1166 * (plunger_d_in ** 2) * stroke_length_in * test_spm
                if theo_bpd > best_rate:
                    best_rate = theo_bpd
                    best_spm = test_spm
                    selected_drag = float_res["peak_downstroke_drag_lbf"]
                    selected_float_ratio = fr

        # Convert SPM to VFD Hz (Standard gearbox ratio e.g. 50 Hz = 3.5 SPM)
        # Ratio: Hz = SPM * (50.0 / 3.5) = SPM * 14.285
        target_vfd_hz = min(60.0, max(12.0, best_spm * 14.2857))
        target_vfd_current_a = 15.0 + (target_vfd_hz / 50.0) * 22.0
        target_vfd_power_kw = (target_vfd_hz / 50.0) ** 1.3 * 18.5

        # Energy per barrel (kWh / bbl):
        daily_kwh = target_vfd_power_kw * 24.0
        daily_bbl = max(1.0, best_rate * 0.75)  # Assuming 75% eff
        kwh_per_bbl = daily_kwh / daily_bbl

        return {
            "recommended_spm": round(best_spm, 2),
            "recommended_vfd_hz": round(target_vfd_hz, 1),
            "estimated_motor_current_a": round(target_vfd_current_a, 1),
            "estimated_motor_power_kw": round(target_vfd_power_kw, 2),
            "specific_energy_kwh_bbl": round(kwh_per_bbl, 2),
            "downstroke_drag_lbf": round(selected_drag, 1),
            "float_ratio": round(selected_float_ratio, 3),
            "is_floating_safe": selected_float_ratio <= target_float_margin,
            "reservoir_temperature_c": reservoir_temp_c,
            "control_action": f"Set VFD to {target_vfd_hz:.1f} Hz ({best_spm:.2f} SPM) to maximize lift without rod floating."
        }
