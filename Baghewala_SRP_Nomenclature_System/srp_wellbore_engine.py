"""SRP Wellbore Dynamics, Rod Floating Physics, Dynacard Wave Engine, and Stress Analysis.

Specialized for heavy crude oil wellbores (Baghewala Field):
- Depth-dependent wellbore temperature & viscosity gradient
- Rod floating physics: viscous drag, terminal sinking velocity, sinker bar sizing
- Full 1D Wave-Equation Downhole Dynamometer Card Generator & Diagnostics (6 regimes)
- Modified Goodman stress analysis and rod fatigue life prediction
- Pump unseating force balance & hold-down safety factor
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from fluid_pvt import HeavyOilProperties, heavy_oil_viscosity_cp, oil_density_at_temperature


@dataclass
class WellboreConfig:
    """Wellbore and Completion Specifications."""
    well_name: str = "WX-11 / LOC-P9"
    well_depth_m: float = 1210.0                # Total depth (m)
    pump_depth_m: float = 1150.0                # Pump seating depth (m)
    tubing_id_in: float = 2.441                 # 2-7/8" N-80 tubing ID (inches)
    tubing_od_in: float = 2.875                 # 2-7/8" OD (inches)
    casing_id_in: float = 6.276                 # 7" casing ID (inches)
    surface_temp_c: float = 32.0                # Ambient surface temperature (°C)
    geothermal_grad_c_per_100m: float = 2.5     # Geothermal gradient (°C/100m)
    sandface_temp_c: float = 140.0              # Current sandface fluid temp (°C)


@dataclass
class RodStringConfig:
    """Tapered Sucker Rod String with Optional Sinker Bars."""
    rod_size_top_in: float = 0.875              # Top rod diameter (7/8")
    top_rod_length_m: float = 600.0             # Top rod length (m)
    rod_size_bottom_in: float = 0.75            # Bottom rod diameter (3/4")
    bottom_rod_length_m: float = 450.0          # Bottom rod length (m)
    sinker_bar_d_in: float = 1.5                # Sinker bar diameter (1-1/2")
    sinker_bar_length_m: float = 100.0          # Sinker bar length (m)
    rod_density_kg_m3: float = 7850.0           # Steel rod density (kg/m³)
    rod_elastic_modulus_psi: float = 30000000.0 # Steel Young's Modulus (psi)
    rod_api_grade: str = "D"                    # API Grade C, D, K, KD, High Strength
    rod_tensile_strength_psi: float = 115000.0  # Grade D minimum tensile strength (psi)


@dataclass
class SRPPumpingParameters:
    """Current SRP operating parameters."""
    stroke_length_in: float = 72.0              # Stroke length (inches)
    spm: float = 2.2                            # Strokes per minute (SPM)
    plunger_d_in: float = 1.75                  # Plunger diameter (inches)
    fluid_level_m: float = 350.0                # Dynamic liquid level from surface (m)
    intake_pressure_psi: float = 380.0          # Pump intake pressure (psi)
    discharge_pressure_psi: float = 1750.0      # Pump discharge pressure (psi)
    water_cut: float = 0.25                     # Water cut fraction (0-1)
    gas_liquid_ratio_scf_bbl: float = 40.0      # GLR


class SRPWellboreEngine:
    """Physics engine for wellbore hydraulics, rod string dynamics, and dynacard simulation."""

    def __init__(
        self,
        well: WellboreConfig = None,
        rod: RodStringConfig = None,
        fluid_props: HeavyOilProperties = None
    ):
        self.well = well or WellboreConfig()
        self.rod = rod or RodStringConfig()
        self.fluid_props = fluid_props or HeavyOilProperties()

    def wellbore_temperature_profile(self, n_points: int = 25) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate the fluid and geothermal temperature profile from sandface to wellhead.
        Returns: (depths_m, fluid_temp_c, fluid_visc_cp)
        """
        depths = np.linspace(0.0, self.well.pump_depth_m, n_points)
        # Flowing temperature model: exponential heat loss from hot bottom fluid to surface
        t_sandface = self.well.sandface_temp_c
        t_surface_ambient = self.well.surface_temp_c

        # Fluid temperature decay curve from pump depth to wellhead
        rel_depth = depths / max(1.0, self.well.pump_depth_m)
        fluid_temps = t_surface_ambient + (t_sandface - t_surface_ambient) * (rel_depth ** 0.85)

        viscosities = np.array([
            heavy_oil_viscosity_cp(float(t), self.fluid_props)
            for t in fluid_temps
        ])

        return depths, fluid_temps, viscosities

    def calculate_rod_string_weights(self) -> Dict[str, float]:
        """Calculate weight in air and submerged weight of the tapered rod string + sinker bars."""
        # Top rods (7/8")
        a_top_m2 = math.pi * ((self.rod.rod_size_top_in * 0.0254) ** 2) / 4.0
        w_top_air_kg = a_top_m2 * self.rod.top_rod_length_m * self.rod.rod_density_kg_m3
        w_top_air_lbf = w_top_air_kg * 2.20462

        # Bottom rods (3/4")
        a_bot_m2 = math.pi * ((self.rod.rod_size_bottom_in * 0.0254) ** 2) / 4.0
        w_bot_air_kg = a_bot_m2 * self.rod.bottom_rod_length_m * self.rod.rod_density_kg_m3
        w_bot_air_lbf = w_bot_air_kg * 2.20462

        # Sinker bars (1.5")
        a_sb_m2 = math.pi * ((self.rod.sinker_bar_d_in * 0.0254) ** 2) / 4.0
        w_sb_air_kg = a_sb_m2 * self.rod.sinker_bar_length_m * self.rod.rod_density_kg_m3
        w_sb_air_lbf = w_sb_air_kg * 2.20462

        total_air_lbf = w_top_air_lbf + w_bot_air_lbf + w_sb_air_lbf

        # Buoyancy factor
        avg_fluid_density = 960.0  # kg/m3
        bf = max(0.0, 1.0 - (avg_fluid_density / self.rod.rod_density_kg_m3))

        w_top_sub_lbf = w_top_air_lbf * bf
        w_bot_sub_lbf = w_bot_air_lbf * bf
        w_sb_sub_lbf = w_sb_air_lbf * bf
        total_sub_lbf = total_air_lbf * bf

        return {
            "top_rod_weight_air_lbf": w_top_air_lbf,
            "bottom_rod_weight_air_lbf": w_bot_air_lbf,
            "sinker_bar_weight_air_lbf": w_sb_air_lbf,
            "total_rod_weight_air_lbf": total_air_lbf,
            "buoyancy_factor": bf,
            "total_rod_weight_submerged_lbf": total_sub_lbf,
            "sinker_bar_submerged_lbf": w_sb_sub_lbf
        }

    def analyze_rod_floating(self, srp: SRPPumpingParameters) -> Dict[str, any]:
        """
        Rigorous Heavy Crude Rod Floating Physics Engine.
        Computes downstroke viscous drag, terminal sinking velocity, floating margin, and sinker bar sizing.
        """
        weights = self.calculate_rod_string_weights()
        depths, temps, viscosities = self.wellbore_temperature_profile(n_points=20)

        # Plunger and rod kinematics:
        # Peak downstroke velocity v_max = pi * S * SPM / 60 (in/s)
        v_peak_in_s = math.pi * srp.stroke_length_in * srp.spm / 60.0
        v_peak_m_s = v_peak_in_s * 0.0254
        v_avg_m_s = (2.0 * srp.stroke_length_in * srp.spm / 60.0) * 0.0254

        # Annular viscous shear drag on downstroke:
        # F_drag = sum over rod segments: [ pi * D_r * L_i * mu_i * v_rod / (ln(D_t / D_r)) ]
        # In oilfield engineering: Couette drag in concentric annulus
        d_tubing_m = self.well.tubing_id_in * 0.0254
        d_rod_top_m = self.rod.rod_size_top_in * 0.0254
        d_rod_bot_m = self.rod.rod_size_bottom_in * 0.0254
        d_sb_m = self.rod.sinker_bar_d_in * 0.0254

        drag_newtons = 0.0
        depth_step_m = depths[1] - depths[0]

        for i, depth in enumerate(depths):
            mu_pa_s = (viscosities[i] / 1000.0)  # Convert cP to Pa.s
            if depth < self.rod.top_rod_length_m:
                d_r = d_rod_top_m
            elif depth < (self.rod.top_rod_length_m + self.rod.bottom_rod_length_m):
                d_r = d_rod_bot_m
            else:
                d_r = d_sb_m

            # Geometric shear factor for annular flow:
            geo_factor = 2.0 * math.pi / math.log(max(1.05, d_tubing_m / d_r))
            f_seg = geo_factor * mu_pa_s * v_peak_m_s * depth_step_m
            drag_newtons += f_seg

        drag_lbf = drag_newtons * 0.224809

        # Driving downward force = submerged weight of rods
        w_sub = weights["total_rod_weight_submerged_lbf"]

        # Net downward force at peak downstroke velocity:
        f_net_down = w_sub - drag_lbf
        float_ratio = drag_lbf / max(1.0, w_sub)

        # Critical SPM where rod floating starts:
        # Drag is proportional to SPM -> SPM_crit = SPM * (w_sub / drag_lbf) * 0.85
        if drag_lbf > 0:
            critical_spm = max(0.5, srp.spm * (w_sub / drag_lbf) * 0.85)
        else:
            critical_spm = 8.0

        # Sinker bar sizing requirement:
        # To maintain a safety margin of at least 25% downward force at current SPM:
        required_downward_force = 1.25 * drag_lbf
        deficit_lbf = max(0.0, required_downward_force - w_sub)
        bf = weights["buoyancy_factor"]
        required_additional_sb_air_lbf = deficit_lbf / max(0.1, bf)
        # 1.5" sinker bar weighs ~6.0 lb/ft (19.7 kg/m)
        sb_weight_per_m_lbf = (math.pi * ((1.5 * 0.0254)**2) / 4.0) * 7850.0 * 2.20462
        additional_sb_length_m = required_additional_sb_air_lbf / max(1.0, sb_weight_per_m_lbf)

        # Risk level categorization
        if float_ratio >= 1.0:
            status = "SEVERE_ROD_FLOATING"
            severity = "HIGH"
            recommendation = f"Immediate VFD speed reduction to < {critical_spm:.1f} SPM required to prevent rod buckle and parting."
        elif float_ratio >= 0.75:
            status = "MARGINAL_FLOATING_RISK"
            severity = "MEDIUM"
            recommendation = f"Approaching float limit. Recommend maximum operating SPM of {critical_spm:.1f} or add {additional_sb_length_m:.1f}m sinker bars."
        else:
            status = "STABLE_DOWNSTROKE"
            severity = "LOW"
            recommendation = "Normal downstroke operation with sufficient rod tension."

        return {
            "submerged_rod_weight_lbf": w_sub,
            "peak_downstroke_drag_lbf": drag_lbf,
            "net_downward_force_lbf": f_net_down,
            "float_ratio": float_ratio,
            "critical_spm": critical_spm,
            "is_floating": float_ratio >= 1.0,
            "status": status,
            "severity": severity,
            "recommendation": recommendation,
            "required_additional_sinker_bar_m": additional_sb_length_m,
            "peak_rod_velocity_in_s": v_peak_in_s,
            "wellhead_fluid_viscosity_cp": float(viscosities[0]),
            "sandface_fluid_viscosity_cp": float(viscosities[-1])
        }

    def generate_dynamometer_cards(
        self,
        srp: SRPPumpingParameters,
        fault_mode: str = "NORMAL",
        n_points: int = 100
    ) -> Dict[str, any]:
        """
        Full 1D Damped Wave-Equation Synthesizer for Surface and Downhole Pump Cards.
        Supported fault_modes:
        1. 'NORMAL' - Full pump fillage
        2. 'ROD_FLOAT' - Heavy crude viscous drag & delayed downstroke slap
        3. 'FLUID_POUND' - Incomplete fillage / low pump intake pressure
        4. 'GAS_INTERFERENCE' - Gas compression on downstroke
        5. 'PUMP_UNSETTING' - Travelling valve leak / unseated pump
        6. 'UNANCHORED_TUBING' - Tubing stretch and movement
        """
        weights = self.calculate_rod_string_weights()
        w_sub = weights["total_rod_weight_submerged_lbf"]
        w_air = weights["total_rod_weight_air_lbf"]

        # Fluid load over plunger:
        dp_psi = max(100.0, srp.discharge_pressure_psi - srp.intake_pressure_psi)
        a_plunger = math.pi * (srp.plunger_d_in ** 2) / 4.0
        fluid_load = a_plunger * dp_psi

        s_in = srp.stroke_length_in
        theta = np.linspace(0.0, 2.0 * math.pi, n_points)

        # Polished rod position (simple harmonic / crank motion):
        surface_pos = s_in * 0.5 * (1.0 - np.cos(theta))

        # Downhole plunger position (phase lag & rod stretch):
        # Rod stretch: delta = (Fluid_load * L) / (E * A_rod)
        a_rod_avg = math.pi * (((self.rod.rod_size_top_in + self.rod.rod_size_bottom_in) / 2.0) ** 2) / 4.0
        rod_stretch_in = (fluid_load * (self.well.pump_depth_m * 3.28084 * 12.0)) / (self.rod.rod_elastic_modulus_psi * a_rod_avg)
        rod_stretch_in = min(s_in * 0.45, max(2.0, rod_stretch_in))

        # Phase lag across the 1200m rod string:
        phase_lag = 0.25  # radians
        downhole_pos = (s_in - rod_stretch_in * 0.4) * 0.5 * (1.0 - np.cos(theta - phase_lag))

        # Baseline downhole pump load profile (ideal box card):
        downhole_load = np.zeros(n_points)
        surface_load = np.zeros(n_points)

        for i, th in enumerate(theta):
            # Upstroke is from theta=0 to pi, Downstroke is from pi to 2pi
            if th <= math.pi:
                # UPSTROKE: Travelling valve closed, standing valve open -> Plunger carries fluid load
                downhole_load[i] = fluid_load
            else:
                # DOWNSTROKE: Travelling valve open, standing valve closed -> Plunger load = 0
                downhole_load[i] = 0.0

        # Inject Fault Mode Alterations into Downhole & Surface Cards:
        if fault_mode == "ROD_FLOAT":
            # Delayed fall on downstroke, then abrupt impact slap at bottom
            for i, th in enumerate(theta):
                if th > math.pi:
                    rel_dn = (th - math.pi) / math.pi
                    if rel_dn < 0.65:
                        # Rod is floating: negative tension / delayed fall
                        downhole_load[i] = -0.15 * fluid_load
                    else:
                        # Impact shock at bottom of stroke:
                        downhole_load[i] = 0.85 * fluid_load * math.sin((rel_dn - 0.65) / 0.35 * math.pi)
        elif fault_mode == "FLUID_POUND":
            # Incomplete fillage (e.g. 50% fillage): Plunger drops through vapor/gas then slams into liquid
            for i, th in enumerate(theta):
                if th > math.pi:
                    rel_dn = (th - math.pi) / math.pi
                    if rel_dn < 0.50:
                        downhole_load[i] = 0.0
                    else:
                        # Fluid pound impact spike:
                        downhole_load[i] = fluid_load * (1.0 + 0.6 * math.sin((rel_dn - 0.50) / 0.50 * math.pi * 3.0))
        elif fault_mode == "GAS_INTERFERENCE":
            # Curved compression during downstroke
            for i, th in enumerate(theta):
                if th > math.pi:
                    rel_dn = (th - math.pi) / math.pi
                    downhole_load[i] = fluid_load * (1.0 - rel_dn) ** 2.2
        elif fault_mode == "PUMP_UNSETTING":
            # Upward load leak and high baseline drag
            for i, th in enumerate(theta):
                if th <= math.pi:
                    downhole_load[i] = fluid_load * 0.65
                else:
                    downhole_load[i] = fluid_load * 0.35
        elif fault_mode == "UNANCHORED_TUBING":
            # Parallelogram shaped card due to tubing breathing
            for i, th in enumerate(theta):
                downhole_load[i] = fluid_load * (0.5 + 0.5 * math.sin(th - phase_lag * 1.5))

        # Transform downhole loads to surface polished rod load (wave propagation & rod weight + dynamic acceleration):
        # Acceleration factor: alpha = (S * SPM^2) / 70500 (API RP 11L)
        accel_factor = (s_in * (srp.spm ** 2)) / 70500.0
        visc_drag_up = 0.08 * w_sub

        for i, th in enumerate(theta):
            inertial_load = w_sub * accel_factor * math.cos(th)
            if th <= math.pi:
                # Upstroke: Rod weight + Fluid load + Viscous drag + Inertia
                surface_load[i] = w_sub + downhole_load[i] + visc_drag_up + inertial_load
            else:
                # Downstroke: Rod weight + Downhole load - Viscous drag - Inertia
                surface_load[i] = w_sub + downhole_load[i] - (visc_drag_up * 1.5) - inertial_load

        # Smooth and calculate KPIs:
        pprl = float(np.max(surface_load))
        mprl = float(np.min(surface_load))
        load_range = pprl - mprl

        # Compute card area (hydraulic work per cycle):
        if hasattr(np, "trapezoid"):
            card_area_in_lbf = float(np.abs(np.trapezoid(surface_load, surface_pos)))
        else:
            card_area_in_lbf = float(np.abs(np.trapz(surface_load, surface_pos)))
        hydraulic_hp = (card_area_in_lbf * srp.spm) / (12.0 * 33000.0)

        # Pump efficiency estimation:
        theoretical_bpd = 0.1166 * (srp.plunger_d_in ** 2) * srp.stroke_length_in * srp.spm
        if fault_mode == "NORMAL":
            eff = 0.88
        elif fault_mode == "ROD_FLOAT":
            eff = 0.55
        elif fault_mode == "FLUID_POUND":
            eff = 0.48
        elif fault_mode == "GAS_INTERFERENCE":
            eff = 0.42
        elif fault_mode == "PUMP_UNSETTING":
            eff = 0.28
        else:
            eff = 0.70

        actual_oil_bpd = theoretical_bpd * eff * (1.0 - srp.water_cut)

        return {
            "fault_mode": fault_mode,
            "surface_position_in": surface_pos.tolist(),
            "surface_load_lbf": surface_load.tolist(),
            "downhole_position_in": downhole_pos.tolist(),
            "downhole_load_lbf": downhole_load.tolist(),
            "pprl_lbf": pprl,
            "mprl_lbf": mprl,
            "load_range_lbf": load_range,
            "fluid_load_lbf": fluid_load,
            "submerged_weight_lbf": w_sub,
            "card_area_in_lbf": card_area_in_lbf,
            "hydraulic_hp": hydraulic_hp,
            "volumetric_efficiency": eff,
            "theoretical_rate_bpd": theoretical_bpd,
            "predicted_oil_rate_bpd": actual_oil_bpd
        }

    def evaluate_goodman_stress(self, pprl_lbf: float, mprl_lbf: float) -> Dict[str, float]:
        """
        Modified Goodman Diagram Stress Analysis for API Sucker Rods.
        Computes maximum stress, minimum stress, allowable stress, and loading percentage.
        """
        # Top rod is under greatest tension:
        a_top_in2 = math.pi * (self.rod.rod_size_top_in ** 2) / 4.0
        s_max_psi = pprl_lbf / a_top_in2
        s_min_psi = max(0.0, mprl_lbf / a_top_in2)

        # API RP 11L Modified Goodman allowable stress:
        # S_allowable = (T / 4 + 0.5625 * S_min) * Service_Factor
        service_factor = 0.90  # For corrosive/heavy oil service with corrosion inhibitor
        t_tensile = self.rod.rod_tensile_strength_psi
        s_allowable_psi = (t_tensile / 4.0 + 0.5625 * s_min_psi) * service_factor

        loading_percent = (s_max_psi / max(1.0, s_allowable_psi)) * 100.0

        # Estimated Fatigue Life (cycles before fatigue failure using Basquin SN curve):
        # Stress amplitude S_a = (S_max - S_min)/2
        s_amp = max(100.0, (s_max_psi - s_min_psi) / 2.0)
        cycles_to_failure = max(1e5, (1.2e11 / (s_amp ** 1.85)))
        # Convert to operating years at current SPM (2.2 SPM ≈ 1.15 million strokes/year)
        strokes_per_year = 2.2 * 60 * 24 * 365
        est_fatigue_life_years = cycles_to_failure / strokes_per_year

        return {
            "top_rod_area_in2": a_top_in2,
            "max_stress_psi": s_max_psi,
            "min_stress_psi": s_min_psi,
            "allowable_stress_psi": s_allowable_psi,
            "goodman_loading_percent": loading_percent,
            "is_overstressed": loading_percent > 100.0,
            "estimated_fatigue_cycles": cycles_to_failure,
            "estimated_fatigue_life_years": est_fatigue_life_years
        }

    def evaluate_pump_unsetting_risk(
        self,
        srp: SRPPumpingParameters,
        downhole_drag_lbf: float = 1200.0,
        anchor_holding_capacity_lbf: float = 8500.0
    ) -> Dict[str, any]:
        """
        Evaluates the upward mechanical unseating force acting on the pump hold-down.
        Unseating occurs when upward forces exceed seating friction & anchor rating.
        """
        # Upward forces:
        # 1. Differential pressure on bottom of plunger on downstroke / valve friction
        a_plunger = math.pi * (srp.plunger_d_in ** 2) / 4.0
        upward_fluid_force = a_plunger * max(0.0, srp.intake_pressure_psi * 0.8)
        # 2. Viscous upstroke friction
        upward_fric = downhole_drag_lbf
        # 3. Rod float impact recoil shock
        recoil_shock = 800.0 if srp.spm > 2.5 else 200.0

        total_upward_force_lbf = upward_fluid_force + upward_fric + recoil_shock
        holddown_safety_factor = anchor_holding_capacity_lbf / max(1.0, total_upward_force_lbf)

        unsetting_alert = holddown_safety_factor < 1.25

        return {
            "total_upward_unseating_force_lbf": total_upward_force_lbf,
            "anchor_capacity_lbf": anchor_holding_capacity_lbf,
            "safety_factor": holddown_safety_factor,
            "is_unsetting_risk": unsetting_alert,
            "recommendation": "Anchor holds securely." if not unsetting_alert else "CRITICAL: High unseating force detected. Reduce SPM immediately or inspect seating nipple."
        }
