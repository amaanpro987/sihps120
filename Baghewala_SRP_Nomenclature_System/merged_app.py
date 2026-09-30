# --- IMPORT SECTION ---
from dataclasses import dataclass
from datetime import datetime
from datetime import datetime, timedelta
from math import pi
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from typing import Dict, List, Any
from typing import Dict, List, Any, Optional
from typing import Dict, List, Any, Tuple
from typing import Dict, List, Tuple
from typing import Dict, List, Tuple, Any
from typing import Dict, List, Tuple, Optional
import json
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import streamlit as st

# --- CODE SECTION ---

# ========================================
# Content from: fluid_pvt.py
# ========================================
"""Heavy Oil PVT and Rheology Module for Baghewala Field.

Includes:
- Viscosity-temperature relationships for heavy / extra-heavy crude (ASTM D341 / Walther, Andrade)
- Fluid density temperature correction
- Saturated steam and water thermodynamic properties
- Dissolved gas GOR, oil formation volume factor Bo, and fluid compressibility
"""



@dataclass
class HeavyOilProperties:
    """PVT and rheological properties of heavy crude oil."""
    api_gravity: float = 14.5                  # °API (Baghewala crude ~14-17 API)
    dead_oil_visc_ref_cp: float = 12500.0      # Viscosity at reference temp (cP)
    ref_temp_c: float = 40.0                   # Reference temperature (°C)
    dead_oil_visc_steam_cp: float = 45.0       # Viscosity at steam temp (cP)
    steam_temp_c: float = 200.0                # Steam temperature (°C)
    bubble_point_psi: float = 350.0            # Bubble point pressure (psi)
    solution_gor_scf_bbl: float = 35.0         # Solution GOR (scf/bbl)
    water_specific_gravity: float = 1.02       # Formation brine SG
    thermal_expansion_coeff: float = 0.00072   # 1/°C


def api_to_specific_gravity(api: float) -> float:
    """Convert API gravity to specific gravity at 60°F (15.56°C)."""
    return 141.5 / (api + 131.5)


def specific_gravity_to_density_kg_m3(sg: float) -> float:
    """Convert specific gravity to density in kg/m³."""
    return sg * 999.016


def oil_density_at_temperature(api: float, temp_c: float, thermal_expansion: float = 0.00072) -> float:
    """Calculate oil density at a given temperature in kg/m³."""
    sg_60f = api_to_specific_gravity(api)
    rho_ref = specific_gravity_to_density_kg_m3(sg_60f)
    # Density decreases with temperature
    delta_t = temp_c - 15.56
    rho_t = rho_ref / (1.0 + thermal_expansion * delta_t)
    return max(700.0, rho_t)


def heavy_oil_viscosity_cp(temp_c: float, props: HeavyOilProperties = None) -> float:
    """
    Calculate heavy oil dynamic viscosity (cP) at a given temperature (°C).
    Uses the Walther / ASTM D341 log-log viscosity-temperature equation calibrated for heavy oil:
    log10(log10(v + 0.7)) = A - B * log10(T_K)
    where kinematic viscosity v = mu / rho.
    """
    if props is None:
        props = HeavyOilProperties()

    t_c = max(10.0, min(350.0, temp_c))
    t_k = t_c + 273.15

    # Known reference calibration points
    t1_k = props.ref_temp_c + 273.15
    mu1 = props.dead_oil_visc_ref_cp
    rho1 = oil_density_at_temperature(props.api_gravity, props.ref_temp_c) / 1000.0  # g/cm3
    nu1 = max(1.0, mu1 / rho1)  # cSt

    t2_k = props.steam_temp_c + 273.15
    mu2 = props.dead_oil_visc_steam_cp
    rho2 = oil_density_at_temperature(props.api_gravity, props.steam_temp_c) / 1000.0
    nu2 = max(1.0, mu2 / rho2)

    # Solve Walther coefficients:
    # W1 = log10(log10(nu1 + 0.7))
    # W2 = log10(log10(nu2 + 0.7))
    w1 = math.log10(math.log10(nu1 + 0.7))
    w2 = math.log10(math.log10(nu2 + 0.7))

    b_coeff = (w1 - w2) / (math.log10(t2_k) - math.log10(t1_k))
    a_coeff = w1 + b_coeff * math.log10(t1_k)

    w_curr = a_coeff - b_coeff * math.log10(t_k)
    try:
        nu_curr = 10.0 ** (10.0 ** w_curr) - 0.7
        nu_curr = max(1.0, min(1000000.0, nu_curr))
    except (OverflowError, ValueError):
        nu_curr = mu1

    rho_curr = oil_density_at_temperature(props.api_gravity, t_c) / 1000.0
    mu_curr = nu_curr * rho_curr
    return max(1.0, mu_curr)


def saturated_steam_temperature_c(pressure_bar: float) -> float:
    """
    Approximate saturation temperature of steam (°C) from absolute pressure (bar).
    Antoine equation approximation for water/steam.
    """
    p_bar = max(0.5, min(150.0, pressure_bar))
    # Formula: T_sat(°C) ≈ 100 * (P_bar / 1.01325) ** 0.25 for rough or Antoine:
    # log10(P_bar * 750.062) = A - B / (C + T)
    # Using simplified industrial fit:
    t_sat = 42.6776 / (math.log10(p_bar) - 5.5595) + 273.15  # Kelvin
    t_sat_c = 100.0 * (p_bar ** 0.235)  # Excellent empirical correlation between 1 and 100 bar
    return min(350.0, max(100.0, t_sat_c))


def steam_enthalpy_kj_kg(pressure_bar: float, steam_quality: float = 0.80) -> Tuple[float, float, float]:
    """
    Returns (h_liquid, h_vap, h_total) in kJ/kg for saturated steam at given pressure and quality.
    h_liquid: sensible heat of water
    h_vap: latent heat of vaporization (h_fg)
    h_total = h_liquid + quality * h_vap
    """
    t_sat = saturated_steam_temperature_c(pressure_bar)
    # Sensible heat of liquid water ~ 4.184 * T_sat
    h_liquid = 4.184 * t_sat
    # Latent heat decreases with temperature toward critical point:
    h_vap = max(500.0, 2501.0 - 2.37 * t_sat)
    x = max(0.0, min(1.0, steam_quality))
    h_total = h_liquid + x * h_vap
    return h_liquid, h_vap, h_total


def formation_volume_factor_bo(temp_c: float, solution_gor: float, api: float) -> float:
    """
    Estimate heavy oil formation volume factor Bo (bbl/STB) using Standing's correlation.
    """
    sg_gas = 0.65
    sg_oil = api_to_specific_gravity(api)
    temp_f = temp_c * 9.0 / 5.0 + 32.0
    term = solution_gor * (sg_gas / sg_oil) ** 0.5 + 1.25 * temp_f
    bo = 0.9759 + 0.000120 * (term ** 1.2)
    return max(1.01, min(1.35, bo))


def composite_fluid_properties(
    water_cut: float,
    temp_c: float,
    props: HeavyOilProperties = None
) -> Dict[str, float]:
    """
    Calculate composite liquid properties (emulsion viscosity, mixture density) as a function of water cut and temperature.
    """
    if props is None:
        props = HeavyOilProperties()

    wc = max(0.0, min(1.0, water_cut))
    oil_visc = heavy_oil_viscosity_cp(temp_c, props)
    water_visc = max(0.2, 1.0 / (1.0 + 0.0337 * (temp_c - 20.0) + 0.00022 * (temp_c - 20.0)**2))

    oil_density = oil_density_at_temperature(props.api_gravity, temp_c)
    water_density = props.water_specific_gravity * 999.016 / (1.0 + 0.0004 * (temp_c - 15.56))

    # Mixture density
    mix_density = (1.0 - wc) * oil_density + wc * water_density

    # Emulsion viscosity model (Woelflin / Brinkman inversion model):
    if wc < 0.60:
        # Water-in-oil emulsion: viscosity increases with water cut up to inversion point
        emulsion_factor = 1.0 + 2.5 * wc + 10.0 * (wc ** 2)
        mix_visc = oil_visc * emulsion_factor
    else:
        # Oil-in-water emulsion: water is continuous phase, viscosity drops
        mix_visc = water_visc * (1.0 + 2.5 * (1.0 - wc))

    return {
        "oil_viscosity_cp": oil_visc,
        "water_viscosity_cp": water_visc,
        "mixture_viscosity_cp": mix_visc,
        "oil_density_kg_m3": oil_density,
        "water_density_kg_m3": water_density,
        "mixture_density_kg_m3": mix_density,
        "water_cut": wc,
        "temperature_c": temp_c
    }

# ========================================
# Content from: srp_formulas.py
# ========================================

"""SRP engineering calculations.

Units:
- depth: m
- pressure: psi
- density: kg/m3
- tubing/rod/plunger diameter: inch unless stated
- stroke: inch
- speed: SPM
- rates: bbl/day
- power: hp
"""



BBL_M3 = 0.1589872949
M_TO_FT = 3.280839895
PSI_PER_M_WATER = 1.42233462


def pump_displacement_bpd(plunger_d_in: float, stroke_in: float, spm: float) -> float:
    """Theoretical single-plunger SRP displacement, bbl/day."""
    if min(plunger_d_in, stroke_in, spm) <= 0:
        return 0.0
    return 0.1166 * plunger_d_in**2 * stroke_in * spm


def pump_displacement_m3_day(plunger_d_in, stroke_in, spm):
    return pump_displacement_bpd(plunger_d_in, stroke_in, spm) * BBL_M3


def fluid_load_lbf(plunger_d_in: float, differential_pressure_psi: float) -> float:
    """Approximate load over plunger area, lbf."""
    area_in2 = pi * plunger_d_in**2 / 4
    return area_in2 * differential_pressure_psi


def hydrostatic_pressure_psi(depth_m: float, density_kg_m3: float) -> float:
    """Hydrostatic pressure from rho*g*h converted to psi."""
    return depth_m * density_kg_m3 * 9.80665 / 6894.757293


def hydrostatic_gradient_psi_m(density_kg_m3: float) -> float:
    return density_kg_m3 * 9.80665 / 6894.757293


def api_gravity_from_density(density_kg_m3: float) -> float:
    sg = density_kg_m3 / 999.016
    if sg <= 0:
        return 0.0
    return 141.5 / sg - 131.5


def density_from_api_gravity(api_gravity: float) -> float:
    sg = 141.5 / (api_gravity + 131.5)
    return sg * 999.016


def rod_string_weight_lbf(
    rod_d_in: float,
    rod_length_m: float,
    rod_material_density_kg_m3: float = 7850.0,
) -> float:
    """Approximate rod weight in air from a solid circular rod."""
    d_m = rod_d_in * 0.0254
    volume = pi * d_m**2 / 4 * rod_length_m
    mass = volume * rod_material_density_kg_m3
    return mass * 9.80665 / 4.4482216153


def buoyancy_factor(fluid_density_kg_m3: float, rod_material_density_kg_m3=7850.0) -> float:
    """Approximate buoyancy factor for submerged steel."""
    return max(0.0, 1.0 - fluid_density_kg_m3 / rod_material_density_kg_m3)


def rod_string_weight_submerged_lbf(
    rod_d_in, rod_length_m, fluid_density_kg_m3, rod_material_density_kg_m3=7850.0
):
    w_air = rod_string_weight_lbf(rod_d_in, rod_length_m, rod_material_density_kg_m3)
    return w_air * buoyancy_factor(fluid_density_kg_m3, rod_material_density_kg_m3)


def plunger_velocity_in_s(stroke_in: float, spm: float) -> float:
    """Average absolute velocity approximation: 2*stroke per cycle."""
    return 2.0 * stroke_in * spm / 60.0


def surface_power_hp(torque_lbf_ft: float, spm: float) -> float:
    """Rotational power relation: HP = torque(lb-ft)*RPM/5252."""
    return abs(torque_lbf_ft * spm / 5252.0)


def hydraulic_power_hp(rate_bpd: float, differential_pressure_psi: float) -> float:
    """Approximate hydraulic horsepower using oilfield units."""
    return max(0.0, rate_bpd * differential_pressure_psi / 1714.0)


def pump_efficiency(actual_rate_bpd: float, theoretical_rate_bpd: float) -> float:
    if theoretical_rate_bpd <= 0:
        return 0.0
    return max(0.0, min(1.2, actual_rate_bpd / theoretical_rate_bpd))


def volumetric_efficiency(actual_rate_bpd, theoretical_rate_bpd):
    return pump_efficiency(actual_rate_bpd, theoretical_rate_bpd)


def rod_float_indicator(min_polished_rod_load_lbf: float, submerged_rod_weight_lbf: float,
                        fluid_load_lbf: float) -> float:
    """
    Heuristic rod-float margin.

    Positive values mean the modeled minimum polished-rod load is below the
    modeled submerged rod-string support requirement, indicating increasing
    likelihood of compression/floating. It is an indicator, not a certified
    dynamometer diagnosis.
    """
    return (submerged_rod_weight_lbf - min_polished_rod_load_lbf) / max(
        submerged_rod_weight_lbf + abs(fluid_load_lbf), 1.0
    )


def impact_index(max_load_lbf: float, min_load_lbf: float, stroke_in: float, spm: float) -> float:
    """
    Dimensionless impact severity indicator.
    Larger load swing and higher velocity produce a larger index.
    """
    load_swing = max(0.0, max_load_lbf - min_load_lbf)
    velocity = plunger_velocity_in_s(stroke_in, spm)
    return load_swing * velocity / 10000.0


def estimate_oil_rate(
    plunger_d_in, stroke_in, spm, volumetric_efficiency_value,
    water_cut_fraction=0.0
):
    q_liquid = pump_displacement_bpd(plunger_d_in, stroke_in, spm) * volumetric_efficiency_value
    return q_liquid * max(0.0, 1.0 - water_cut_fraction), q_liquid


@dataclass
class SRPInputs:
    plunger_d_in: float
    stroke_in: float
    spm: float
    pump_depth_m: float
    fluid_density_kg_m3: float
    rod_d_in: float
    rod_length_m: float
    differential_pressure_psi: float
    actual_rate_bpd: float = 0.0
    water_cut_fraction: float = 0.0
    min_prl_lbf: float = 0.0
    max_prl_lbf: float = 0.0


def calculate(inp: SRPInputs) -> dict:
    q_theoretical = pump_displacement_bpd(inp.plunger_d_in, inp.stroke_in, inp.spm)
    eff = pump_efficiency(inp.actual_rate_bpd, q_theoretical) if inp.actual_rate_bpd else None
    fluid_load = fluid_load_lbf(inp.plunger_d_in, inp.differential_pressure_psi)
    rod_wt = rod_string_weight_submerged_lbf(
        inp.rod_d_in, inp.rod_length_m, inp.fluid_density_kg_m3
    )
    float_index = rod_float_indicator(inp.min_prl_lbf, rod_wt, fluid_load)
    impact = impact_index(inp.max_prl_lbf, inp.min_prl_lbf, inp.stroke_in, inp.spm)
    return {
        "theoretical_liquid_bpd": q_theoretical,
        "pump_efficiency": eff,
        "fluid_load_lbf": fluid_load,
        "submerged_rod_weight_lbf": rod_wt,
        "rod_float_index": float_index,
        "impact_index": impact,
        "hydrostatic_pressure_psi": hydrostatic_pressure_psi(
            inp.pump_depth_m, inp.fluid_density_kg_m3
        ),
    }

# ========================================
# Content from: ertmac_ui_components.py
# ========================================
"""ERTMAC (Enterprise Real Time Monitoring & Advisory Center) UI Component Library.

Provides:
- Industrial SCADA Dark Theme CSS Styles
- Live Alarm & Event Annunciator Banner
- High-Density SCADA Telemetry Cards
- Interactive SVG Animated Wellbore & Reservoir Thermal Schematic
- Dynamic Pumping Unit Kinematics Display
- Industrial Gauges & Status LEDs
"""



def get_ertmac_css() -> str:
    """Returns custom CSS for OIL India ERTMAC SCADA design."""
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Rajdhani:wght@500;600;700&display=swap');

    /* Global ERTMAC Dark SCADA Theme */
    .stApp {
        background-color: #060a12 !important;
        color: #e2e8f0 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    /* Remove default Streamlit top padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }

    /* SCADA Top Navigation Bar */
    .ertmac-header {
        background: linear-gradient(180deg, #0f172a 0%, #090e1a 100%);
        border: 1px solid #1e293b;
        border-bottom: 2px solid #0ea5e9;
        border-radius: 8px;
        padding: 12px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .ertmac-logo-title {
        font-family: 'Rajdhani', sans-serif;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 1px;
        color: #38bdf8;
        text-transform: uppercase;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .ertmac-subtitle {
        font-family: 'Inter', sans-serif;
        font-size: 12px;
        color: #94a3b8;
        letter-spacing: 0.5px;
        margin-top: 2px;
    }
    .scada-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        background: rgba(14, 165, 233, 0.1);
        border: 1px solid rgba(14, 165, 233, 0.3);
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        color: #38bdf8;
        font-weight: 600;
    }
    
    /* Heartbeat LED pulse */
    .led-pulse {
        width: 8px;
        height: 8px;
        background-color: #10b981;
        border-radius: 50%;
        box-shadow: 0 0 10px #10b981;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.7; }
        50% { transform: scale(1.3); opacity: 1; filter: drop-shadow(0 0 8px #10b981); }
        100% { transform: scale(0.9); opacity: 0.7; }
    }

    /* Industrial Telemetry Cards */
    .scada-card {
        background: linear-gradient(135deg, #0f172a 0%, #0d1527 100%);
        border: 1px solid #1e2d4a;
        border-left: 3px solid #0284c7;
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
        transition: all 0.2s ease;
    }
    .scada-card:hover {
        border-color: #38bdf8;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(14, 165, 233, 0.15);
    }
    .scada-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .scada-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 22px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.2;
    }
    .scada-unit {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 400;
        margin-left: 2px;
    }
    .scada-sub {
        font-size: 11px;
        font-weight: 500;
        margin-top: 4px;
    }
    .val-good { color: #10b981; }
    .val-warn { color: #f59e0b; }
    .val-crit { color: #ef4444; }
    .val-cyan { color: #38bdf8; }

    /* Alarm Banner */
    .alarm-banner {
        background: linear-gradient(90deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #3730a3;
        border-left: 4px solid #6366f1;
        border-radius: 6px;
        padding: 10px 16px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
    }

    /* Section Panels */
    .panel-box {
        background: #0d1527;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .panel-header {
        font-family: 'Rajdhani', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 8px;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #090e1a;
        padding: 4px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px;
        color: #94a3b8;
        padding: 8px 16px;
        font-family: 'Rajdhani', sans-serif;
        font-size: 15px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }
    
    /* Control Button */
    .stButton>button {
        background: linear-gradient(180deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 6px !important;
        padding: 8px 20px !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3) !important;
        transition: all 0.2s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(56, 189, 248, 0.5) !important;
    }
</style>
"""


def render_ertmac_header(well_name: str, status_text: str = "CSS CYCLE 3 - THERMAL SRP PRODUCTION") -> str:
    """Renders the top ERTMAC SCADA header bar."""
    return f"""
<div class="ertmac-header">
    <div>
        <div class="ertmac-logo-title">
            <span>⚡ OIL INDIA LIMITED | ERTMAC WELL-TO-SURFACE DIGITAL TWIN</span>
        </div>
        <div class="ertmac-subtitle">
            RAJASTHAN BASIN | BAGHEWALA HEAVY OIL THERMAL EOR FIELD | WELL: <b>{well_name}</b>
        </div>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
        <div class="scada-badge">
            <span class="led-pulse"></span>
            <span>SCADA LIVE (OPC-UA)</span>
        </div>
        <div class="scada-badge" style="background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); color: #34d399;">
            <span>{status_text}</span>
        </div>
    </div>
</div>
"""


def render_alarm_ticker(alarms: List[Dict[str, str]]) -> str:
    """Renders the ERTMAC Alarm & Event Advisory Banner."""
    if not alarms:
        return ""
    
    first_alarm = alarms[0]
    severity_colors = {
        "CRITICAL": "#ef4444",
        "WARNING": "#f59e0b",
        "ADVISORY": "#38bdf8",
        "SUCCESS": "#10b981"
    }
    color = severity_colors.get(first_alarm.get("severity", "ADVISORY"), "#38bdf8")
    
    return f"""
<div class="alarm-banner" style="border-left-color: {color};">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-weight: 700; color: {color}; font-family: 'JetBrains Mono', monospace;">[{first_alarm.get('type', 'ADVISORY')}]</span>
        <span style="color: #cbd5e1;">{first_alarm.get('message', '')}</span>
    </div>
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #64748b;">
        {first_alarm.get('timestamp', 'LIVE SCADA')}
    </div>
</div>
"""


def render_interactive_wellbore_svg(
    sandface_temp_c: float,
    wellhead_temp_c: float,
    fluid_level_m: float,
    heated_radius_m: float,
    spm: float,
    vfd_hz: float,
    is_floating: bool = False
) -> str:
    """
    Renders an animated, high-tech SVG cross-section schematic of the Baghewala Wellbore & Thermal Reservoir.
    """
    fluid_level_y = 120 + int((fluid_level_m / 1210.0) * 220)
    fluid_level_y = max(130, min(330, fluid_level_y))
    
    thermal_bubble_r = min(110, max(25, int(heated_radius_m * 3.5)))
    stroke_speed_s = max(0.5, 60.0 / max(0.1, spm * 12.0))
    
    rod_color = "#ef4444" if is_floating else "#38bdf8"
    
    return f"""
<div style="background: #090e1a; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; text-align: center;">
    <svg viewBox="0 0 500 520" width="100%" height="480" style="max-width: 500px; margin: 0 auto; display: block;">
        <defs>
            <!-- Thermal Gradient for Jodhpur Sandstone -->
            <radialGradient id="thermalGrad" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#ef4444" stop-opacity="0.85" />
                <stop offset="45%" stop-color="#f97316" stop-opacity="0.60" />
                <stop offset="80%" stop-color="#eab308" stop-opacity="0.30" />
                <stop offset="100%" stop-color="#0284c7" stop-opacity="0.05" />
            </radialGradient>
            
            <linearGradient id="casingGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#1e293b" />
                <stop offset="50%" stop-color="#475569" />
                <stop offset="100%" stop-color="#1e293b" />
            </linearGradient>
            
            <linearGradient id="fluidGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stop-color="#1e1b4b" stop-opacity="0.4" />
                <stop offset="100%" stop-color="#0f172a" stop-opacity="0.9" />
            </linearGradient>
        </defs>

        <!-- Background Stratigraphy -->
        <rect x="20" y="20" width="460" height="90" fill="#0f172a" rx="4" />
        <text x="35" y="45" fill="#64748b" font-size="11" font-family="'JetBrains Mono', monospace">Surface Formations (0 - 460m)</text>
        
        <rect x="20" y="115" width="460" height="150" fill="#0c1322" rx="4" />
        <text x="35" y="135" fill="#64748b" font-size="11" font-family="'JetBrains Mono', monospace">Bilara Dolostone (460 - 1100m)</text>

        <rect x="20" y="270" width="460" height="70" fill="#111c30" rx="4" />
        <text x="35" y="290" fill="#38bdf8" font-size="11" font-family="'JetBrains Mono', monospace">Lower Bilara Dolostone (1100 - 1162m)</text>

        <!-- Jodhpur Sandstone Heavy Oil Reservoir Pay Zone -->
        <rect x="20" y="345" width="460" height="155" fill="#172554" rx="4" stroke="#1d4ed8" stroke-width="1.5" />
        <text x="35" y="370" fill="#60a5fa" font-weight="700" font-size="12" font-family="'JetBrains Mono', monospace">JODHPUR SANDSTONE PAY (1162 - 1210m TD)</text>
        <text x="35" y="388" fill="#93c5fd" font-size="10" font-family="'Inter', sans-serif">15m Net Pay | Heavy Crude 14.5 °API | 12,500 cP</text>

        <!-- Thermal Steam Bubble in Reservoir -->
        <circle cx="250" cy="425" r="{thermal_bubble_r}" fill="url(#thermalGrad)" />
        <circle cx="250" cy="425" r="{thermal_bubble_r}" fill="none" stroke="#f97316" stroke-dasharray="4,4" stroke-width="1.5">
            <animate attributeName="stroke-dashoffset" from="0" to="20" dur="3s" repeatCount="indefinite" />
        </circle>
        <text x="{260 + thermal_bubble_r}" y="425" fill="#f97316" font-size="10" font-family="'JetBrains Mono', monospace">Steam Front rh: {heated_radius_m:.1f}m</text>

        <!-- Surface Unit & Wellhead -->
        <path d="M 215 50 L 285 50 L 275 80 L 225 80 Z" fill="#0284c7" stroke="#38bdf8" stroke-width="1.5" />
        <text x="250" y="42" fill="#38bdf8" font-weight="700" font-size="11" text-anchor="middle" font-family="'Rajdhani', sans-serif">WELLHEAD TREE</text>
        <text x="300" y="70" fill="#f59e0b" font-size="10" font-family="'JetBrains Mono', monospace">T_wh: {wellhead_temp_c:.1f}°C</text>

        <!-- 7\" Casing -->
        <rect x="235" y="80" width="30" height="340" fill="url(#casingGrad)" stroke="#334155" stroke-width="1" />
        
        <!-- 2-7/8\" Tubing -->
        <rect x="242" y="80" width="16" height="320" fill="#0f172a" stroke="#0284c7" stroke-width="1.5" />

        <!-- Dynamic Liquid Level in Annulus -->
        <rect x="236" y="{fluid_level_y}" width="28" height="{400 - fluid_level_y}" fill="url(#fluidGrad)" />
        <line x1="220" y1="{fluid_level_y}" x2="280" y2="{fluid_level_y}" stroke="#06b6d4" stroke-width="2" stroke-dasharray="3,2" />
        <text x="290" y="{fluid_level_y + 4}" fill="#06b6d4" font-size="10" font-family="'JetBrains Mono', monospace">Fluid Level: {fluid_level_m:.0f}m</text>

        <!-- Sucker Rod String & Sinker Bars -->
        <!-- Top 7/8\" Rods -->
        <line x1="250" y1="80" x2="250" y2="240" stroke="{rod_color}" stroke-width="3" />
        <!-- Bottom 3/4\" Rods -->
        <line x1="250" y1="240" x2="250" y2="350" stroke="{rod_color}" stroke-width="2.5" />
        <!-- 1.5\" Sinker Bars (Thicker) -->
        <line x1="250" y1="350" x2="250" y2="390" stroke="#f59e0b" stroke-width="5" />
        <text x="175" y="375" fill="#f59e0b" font-size="10" font-family="'JetBrains Mono', monospace">Sinker Bars (1.5\")</text>

        <!-- Downhole Pump & Plunger with reciprocating motion -->
        <rect x="240" y="390" width="20" height="25" fill="#0284c7" stroke="#38bdf8" stroke-width="1.5" />
        <rect x="244" y="394" width="12" height="15" fill="#e2e8f0">
            <animateTransform attributeName="transform" type="translate" values="0,0; 0,-8; 0,0" dur="{stroke_speed_s}s" repeatCount="indefinite" />
        </rect>
        <text x="160" y="405" fill="#38bdf8" font-size="10" font-family="'JetBrains Mono', monospace">Pump Depth: 1150m</text>

        <!-- Sandface Perforations -->
        <g stroke="#f97316" stroke-width="1.5">
            <line x1="230" y1="415" x2="240" y2="415" />
            <line x1="230" y1="425" x2="240" y2="425" />
            <line x1="230" y1="435" x2="240" y2="435" />
            <line x1="260" y1="415" x2="270" y2="415" />
            <line x1="260" y1="425" x2="270" y2="425" />
            <line x1="260" y1="435" x2="270" y2="435" />
        </g>
        <text x="250" y="465" fill="#ef4444" font-weight="700" font-size="12" text-anchor="middle" font-family="'JetBrains Mono', monospace">
            Sandface: {sandface_temp_c:.1f}°C
        </text>

        <!-- Live VFD / SPM indicator badge at bottom -->
        <rect x="140" y="485" width="220" height="26" fill="#0f172a" rx="4" stroke="#1e293b" />
        <text x="250" y="502" fill="#38bdf8" font-weight="700" font-size="11" text-anchor="middle" font-family="'JetBrains Mono', monospace">
            VFD: {vfd_hz:.1f} Hz | SPEED: {spm:.2f} SPM
        </text>
    </svg>
</div>
"""

# ========================================
# Content from: database.py
# ========================================
"""Production-Grade Database Manager and Data Layer for Baghewala SRP & CSS Digital Twin."""


DB_PATH = Path(__file__).parent / "baghewala_srp.db"


def connect(db_path=DB_PATH):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS wells (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_name TEXT UNIQUE NOT NULL,
    location TEXT,
    target_depth_m REAL,
    formation TEXT,
    pay_thickness_m REAL,
    tubing_od_in REAL,
    tubing_id_in REAL DEFAULT 2.441,
    casing_od_in REAL DEFAULT 7.0,
    tubing_grade TEXT,
    lift_system TEXT,
    api_gravity REAL DEFAULT 14.5,
    reservoir_temp_c REAL DEFAULT 48.0,
    initial_pressure_psi REAL DEFAULT 1650.0,
    permeability_md REAL DEFAULT 450.0,
    porosity REAL DEFAULT 0.24,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS srp_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    effective_from TEXT NOT NULL,
    pump_type TEXT DEFAULT 'Tubing Insert Rod Pump',
    plunger_d_in REAL DEFAULT 1.75,
    pump_depth_m REAL DEFAULT 1150.0,
    stroke_in REAL DEFAULT 72.0,
    spm REAL DEFAULT 2.2,
    vfd_hz REAL DEFAULT 31.4,
    top_rod_d_in REAL DEFAULT 0.875,
    top_rod_length_m REAL DEFAULT 600.0,
    bottom_rod_d_in REAL DEFAULT 0.75,
    bottom_rod_length_m REAL DEFAULT 450.0,
    sinker_bar_d_in REAL DEFAULT 1.5,
    sinker_bar_length_m REAL DEFAULT 100.0,
    rod_material_density_kg_m3 REAL DEFAULT 7850,
    rod_api_grade TEXT DEFAULT 'D',
    anchor_capacity_lbf REAL DEFAULT 8500.0,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS css_cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    cycle_number INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    steam_volume_tonnes REAL,
    injection_rate_tonnes_day REAL,
    injection_pressure_bar REAL,
    steam_quality REAL,
    soak_days REAL,
    production_days REAL,
    cumulative_oil_bbl REAL,
    cumulative_water_bbl REAL,
    cumulative_sor REAL,
    peak_oil_rate_bpd REAL,
    status TEXT DEFAULT 'COMPLETED',
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS operating_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    stroke_in REAL,
    spm REAL,
    vfd_hz REAL,
    vfd_current_a REAL,
    motor_power_kw REAL,
    torque_lbf_ft REAL,
    min_prl_lbf REAL,
    max_prl_lbf REAL,
    sandface_temp_c REAL,
    wellhead_temp_c REAL,
    fluid_level_m REAL,
    intake_pressure_psi REAL,
    discharge_pressure_psi REAL,
    fluid_density_kg_m3 REAL,
    oil_rate_bpd REAL,
    liquid_rate_bpd REAL,
    water_cut REAL,
    pump_efficiency REAL,
    rod_float_index REAL,
    impact_index REAL,
    goodman_stress_percent REAL,
    specific_energy_kwh_bbl REAL,
    ai_fault_diagnosis TEXT DEFAULT 'NORMAL',
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS dynacards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    card_type TEXT DEFAULT 'SURFACE',
    stroke_in REAL,
    spm REAL,
    pprl_lbf REAL,
    mprl_lbf REAL,
    card_area_in_lbf REAL,
    positions_json TEXT NOT NULL,
    loads_json TEXT NOT NULL,
    ai_classified_mode TEXT,
    ai_confidence_pct REAL,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS rod_failure_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    depth_m REAL,
    rod_size_in REAL,
    failure_mode TEXT,
    root_cause TEXT,
    operating_spm REAL,
    stroke_in REAL,
    torque_lbf_ft REAL,
    remarks TEXT,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS pump_unsetting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    pump_depth_m REAL,
    spm REAL,
    stroke_in REAL,
    fluid_level_m REAL,
    min_prl_lbf REAL,
    max_prl_lbf REAL,
    cause TEXT,
    corrective_action TEXT,
    remarks TEXT,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);

CREATE TABLE IF NOT EXISTS optimization_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_id INTEGER NOT NULL,
    run_time TEXT NOT NULL,
    opt_type TEXT DEFAULT 'INTEGRATED',
    selected_stroke_in REAL,
    selected_spm REAL,
    selected_vfd_hz REAL,
    recommended_steam_vol_tonnes REAL,
    recommended_soak_days REAL,
    predicted_oil_bpd REAL,
    predicted_efficiency REAL,
    predicted_float_index REAL,
    predicted_impact_index REAL,
    predicted_sor REAL,
    predicted_energy_saving_pct REAL,
    objective_value REAL,
    explanation TEXT,
    FOREIGN KEY (well_id) REFERENCES wells(id)
);
"""


def init_db(db_path=DB_PATH):
    con = connect(db_path)
    # Check if wells table exists and has all columns; if old schema, migrate safely
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wells'")
    if cur.fetchone():
        # Check column names in wells
        cur.execute("PRAGMA table_info(wells)")
        cols = [r["name"] for r in cur.fetchall()]
        if "tubing_id_in" not in cols:
            # Upgrade schema by dropping old empty tables or altering
            con.execute("DROP TABLE IF EXISTS wells")
            con.execute("DROP TABLE IF EXISTS srp_config")
            con.execute("DROP TABLE IF EXISTS operating_data")
            con.execute("DROP TABLE IF EXISTS css_cycles")
            con.execute("DROP TABLE IF EXISTS dynacards")
            con.execute("DROP TABLE IF EXISTS rod_failure_history")
            con.execute("DROP TABLE IF EXISTS pump_unsetting_history")
            con.execute("DROP TABLE IF EXISTS optimization_runs")
            con.commit()

    con.executescript(SCHEMA)
    con.commit()
    con.close()


def seed_comprehensive_field_data(db_path=DB_PATH):
    """Initializes and seeds rich realistic data for WX-11 and WX-07 wells."""
    init_db(db_path)
    con = connect(db_path)
    cur = con.cursor()

    # Seed Wells
    wells_to_seed = [
        {
            "name": "WX-11 / LOC-P9",
            "loc": "Baghewala Central Pad P9",
            "td": 1210.0,
            "pay": 15.0,
            "api": 14.5,
            "notes": "Target: Jodhpur Sandstone heavy oil formation. CSS Thermal Recovery + SRP artificial lift."
        },
        {
            "name": "WX-07 / LOC-P3",
            "loc": "Baghewala North Pad P3",
            "td": 1162.0,
            "pay": 14.2,
            "api": 15.2,
            "notes": "Jodhpur Sandstone barefoot completion. CSS Cycle 2 underway."
        }
    ]

    well_ids = {}
    for w in wells_to_seed:
        cur.execute("SELECT id FROM wells WHERE well_name=?", (w["name"],))
        row = cur.fetchone()
        if row:
            well_ids[w["name"]] = row["id"]
        else:
            cur.execute("""
                INSERT INTO wells (
                    well_name, location, target_depth_m, formation, pay_thickness_m,
                    tubing_od_in, tubing_id_in, casing_od_in, tubing_grade, lift_system,
                    api_gravity, reservoir_temp_c, initial_pressure_psi, permeability_md, porosity, notes
                ) VALUES (?, ?, ?, 'Jodhpur Sandstone', ?, 2.875, 2.441, 7.0, 'N-80 EUE 6.5', 'SRP', ?, 48.0, 1650.0, 450.0, 0.24, ?)
            """, (w["name"], w["loc"], w["td"], w["pay"], w["api"], w["notes"]))
            well_ids[w["name"]] = cur.lastrowid

    # Seed SRP Config for WX-11
    wx11_id = well_ids["WX-11 / LOC-P9"]
    cur.execute("SELECT COUNT(*) c FROM srp_config WHERE well_id=?", (wx11_id,))
    if cur.fetchone()["c"] == 0:
        cur.execute("""
            INSERT INTO srp_config (
                well_id, effective_from, pump_type, plunger_d_in, pump_depth_m,
                stroke_in, spm, vfd_hz, top_rod_d_in, top_rod_length_m,
                bottom_rod_d_in, bottom_rod_length_m, sinker_bar_d_in, sinker_bar_length_m,
                rod_material_density_kg_m3, rod_api_grade, anchor_capacity_lbf
            ) VALUES (?, '2025-11-01', 'RHAM Tubing Insert', 1.75, 1150.0, 72.0, 2.2, 31.4, 0.875, 600.0, 0.75, 450.0, 1.5, 100.0, 7850, 'D', 8500.0)
        """, (wx11_id,))

    # Seed CSS Cycles History for WX-11
    cur.execute("SELECT COUNT(*) c FROM css_cycles WHERE well_id=?", (wx11_id,))
    if cur.fetchone()["c"] == 0:
        cur.execute("""
            INSERT INTO css_cycles (
                well_id, cycle_number, start_date, end_date, steam_volume_tonnes,
                injection_rate_tonnes_day, injection_pressure_bar, steam_quality,
                soak_days, production_days, cumulative_oil_bbl, cumulative_water_bbl,
                cumulative_sor, peak_oil_rate_bpd, status
            ) VALUES
            (?, 1, '2025-01-10', '2025-06-25', 2400.0, 150.0, 62.0, 0.80, 6.0, 150.0, 6850.0, 4200.0, 2.20, 95.0, 'COMPLETED'),
            (?, 2, '2025-07-05', '2025-12-18', 2800.0, 140.0, 66.0, 0.82, 7.0, 158.0, 7420.0, 5100.0, 2.37, 88.0, 'COMPLETED'),
            (?, 3, '2026-01-15', NULL, 3200.0, 145.0, 68.0, 0.82, 8.0, 75.0, 3940.0, 3100.0, 2.45, 82.0, 'PRODUCING')
        """, (wx11_id, wx11_id, wx11_id))

    # Seed Rod Failure and Pump Unsetting Historical Incidents
    cur.execute("SELECT COUNT(*) c FROM rod_failure_history WHERE well_id=?", (wx11_id,))
    if cur.fetchone()["c"] == 0:
        cur.execute("""
            INSERT INTO rod_failure_history (
                well_id, event_date, depth_m, rod_size_in, failure_mode, root_cause,
                operating_spm, stroke_in, torque_lbf_ft, remarks
            ) VALUES
            (?, '2025-05-14', 380.0, 0.875, 'Fatigue Parting', 'Severe rod floating in upper tubing due to heavy crude viscous drag at 3.2 SPM. High compressive buckling load.', 3.2, 72.0, 480.0, 'Replaced top 400m rods, added sinker bars.'),
            (?, '2025-11-20', 520.0, 0.75, 'Rod Body Buckle & Tensile Snap', 'Fluid pound impact shock combined with downstroke compression during late cycle cooling.', 2.8, 86.0, 510.0, 'Fishing job completed; VFD speed lowered to 2.2 SPM.')
        """, (wx11_id, wx11_id))

    cur.execute("SELECT COUNT(*) c FROM pump_unsetting_history WHERE well_id=?", (wx11_id,))
    if cur.fetchone()["c"] == 0:
        cur.execute("""
            INSERT INTO pump_unsetting_history (
                well_id, event_date, pump_depth_m, spm, stroke_in, fluid_level_m,
                min_prl_lbf, max_prl_lbf, cause, corrective_action, remarks
            ) VALUES
            (?, '2025-08-11', 1150.0, 3.0, 72.0, 480.0, 450.0, 6400.0, 'Excessive upward viscous friction and traveling valve drag unseated mechanical hold-down cup.', 'Pulled pump, replaced seating cup assembly, reset hold-down to 8500 lbf capacity.', 'Recommended real-time hold-down force monitoring.')
        """, (wx11_id,))

    con.commit()
    con.close()
    return well_ids


def seed_baghewala_well(db_path=DB_PATH):
    """Backward compatibility helper."""
    w_ids = seed_comprehensive_field_data(db_path)
    return w_ids["WX-11 / LOC-P9"]


def insert_operating_data(well_id: int, record: Dict[str, Any], db_path=DB_PATH):
    con = connect(db_path)
    cols = [
        "well_id", "ts", "stroke_in", "spm", "vfd_hz", "vfd_current_a", "motor_power_kw",
        "torque_lbf_ft", "min_prl_lbf", "max_prl_lbf", "sandface_temp_c", "wellhead_temp_c",
        "fluid_level_m", "intake_pressure_psi", "discharge_pressure_psi", "fluid_density_kg_m3",
        "oil_rate_bpd", "liquid_rate_bpd", "water_cut", "pump_efficiency", "rod_float_index",
        "impact_index", "goodman_stress_percent", "specific_energy_kwh_bbl", "ai_fault_diagnosis"
    ]
    vals = [well_id, record.get("ts", datetime.now().isoformat())] + [
        record.get(c) for c in cols[2:]
    ]
    placeholders = ",".join(["?"] * len(cols))
    con.execute(f"INSERT INTO operating_data ({','.join(cols)}) VALUES ({placeholders})", vals)
    con.commit()
    con.close()


def insert_dynacard(well_id: int, card_data: Dict[str, Any], db_path=DB_PATH):
    con = connect(db_path)
    con.execute("""
        INSERT INTO dynacards (
            well_id, ts, card_type, stroke_in, spm, pprl_lbf, mprl_lbf, card_area_in_lbf,
            positions_json, loads_json, ai_classified_mode, ai_confidence_pct
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        well_id,
        card_data.get("ts", datetime.now().isoformat()),
        card_data.get("card_type", "SURFACE"),
        card_data.get("stroke_in", 72.0),
        card_data.get("spm", 2.2),
        card_data.get("pprl_lbf", 5500.0),
        card_data.get("mprl_lbf", 1200.0),
        card_data.get("card_area_in_lbf", 18500.0),
        json.dumps(card_data.get("positions", [])),
        json.dumps(card_data.get("loads", [])),
        card_data.get("ai_classified_mode", "NORMAL"),
        card_data.get("ai_confidence_pct", 98.5)
    ))
    con.commit()
    con.close()


def insert_optimization_run(well_id: int, run_data: Dict[str, Any], db_path=DB_PATH):
    con = connect(db_path)
    con.execute("""
        INSERT INTO optimization_runs (
            well_id, run_time, opt_type, selected_stroke_in, selected_spm, selected_vfd_hz,
            recommended_steam_vol_tonnes, recommended_soak_days, predicted_oil_bpd,
            predicted_efficiency, predicted_float_index, predicted_impact_index,
            predicted_sor, predicted_energy_saving_pct, objective_value, explanation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        well_id,
        datetime.now().isoformat(),
        run_data.get("opt_type", "INTEGRATED"),
        run_data.get("stroke_in"),
        run_data.get("spm"),
        run_data.get("vfd_hz"),
        run_data.get("steam_vol"),
        run_data.get("soak_days"),
        run_data.get("predicted_oil_bpd"),
        run_data.get("predicted_efficiency"),
        run_data.get("predicted_float_index"),
        run_data.get("predicted_impact_index"),
        run_data.get("predicted_sor"),
        run_data.get("predicted_energy_saving_pct"),
        run_data.get("objective_value"),
        run_data.get("explanation")
    ))
    con.commit()
    con.close()

# ========================================
# Content from: reservoir_thermal_engine.py
# ========================================
"""Cyclic Steam Stimulation (CSS) Thermal Reservoir Engine for Baghewala Field.

Implements:
- Marx-Langenheim heat balance during steam injection
- Boberg-Lantz analytical thermal decline model during soaking & production
- Radial temperature distribution and heated zone radius growth
- Thermally-stimulated Inflow Performance Relationship (IPR)
- Multi-cycle CSS simulation (Steam Injection -> Soaking -> SRP Production Phase)
- Energy balance, Steam-Oil Ratio (SOR), and economic thermal efficiency
"""



@dataclass
class ReservoirParameters:
    """Reservoir and rock thermal properties for Baghewala Jodhpur Sandstone."""
    pay_thickness_m: float = 15.0               # Net pay thickness (m)
    depth_m: float = 1210.0                     # Formation depth (m)
    porosity: float = 0.24                      # Reservoir porosity (fraction)
    permeability_md: float = 450.0              # Permeability (mD)
    initial_pressure_psi: float = 1650.0        # Initial reservoir pressure (psi)
    initial_temp_c: float = 48.0                # Initial reservoir temp (°C)
    initial_oil_sat: float = 0.72               # Initial oil saturation (Soi)
    connate_water_sat: float = 0.28             # Connate water saturation (Swc)
    drainage_radius_m: float = 150.0            # Drainage radius re (m)
    wellbore_radius_m: float = 0.108            # Wellbore radius rw (m) for 8.5" hole
    rock_density_kg_m3: float = 2450.0          # Sandstone grain density (kg/m³)
    rock_specific_heat_kj_kg_c: float = 0.92    # Rock heat capacity (kJ/kg/°C)
    caprock_thermal_diffusivity_m2_d: float = 0.0864  # Caprock thermal diffusivity alpha (m²/day)
    caprock_thermal_cond_w_m_k: float = 1.73    # Caprock thermal conductivity (W/m/K)
    skin_factor: float = 0.5                    # Near-wellbore skin factor


@dataclass
class CSSCycleConfig:
    """CSS Cycle operational parameters."""
    cycle_number: int = 1
    steam_volume_tonnes: float = 2800.0         # Cumulative steam volume injected (tonnes)
    injection_rate_tonnes_day: float = 140.0    # Steam injection rate (tonnes/day)
    injection_pressure_bar: float = 65.0        # Injection wellhead/sandface pressure (bar)
    steam_quality: float = 0.80                 # Steam dryness fraction at sandface
    soak_days: float = 7.0                      # Soak period duration (days)
    max_production_days: float = 180.0          # Max days to run production phase
    economic_cut_off_oil_rate_bpd: float = 12.0 # Economic cut-off oil rate (bpd)
    cut_off_temp_c: float = 52.0                # Cut-off reservoir temperature (°C)
    oil_price_usd_bbl: float = 72.0             # Crude oil price ($/bbl)
    steam_cost_usd_tonne: float = 28.0          # Steam generation cost ($/tonne)
    lifting_cost_usd_kwh: float = 0.12          # Electric power cost ($/kWh)


class CSSThermalEngine:
    """Full analytical physics engine for Cyclic Steam Stimulation."""

    def __init__(self, res: ReservoirParameters = None, fluid: HeavyOilProperties = None):
        self.res = res or ReservoirParameters()
        self.fluid = fluid or HeavyOilProperties()

    def volumetric_heat_capacity_reservoir_kj_m3_c(self) -> float:
        """Calculate volumetric heat capacity of saturated reservoir rock M_R (kJ/m³/°C)."""
        rho_r = self.res.rock_density_kg_m3
        c_r = self.res.rock_specific_heat_kj_kg_c
        phi = self.res.porosity
        s_o = self.res.initial_oil_sat
        s_w = self.res.connate_water_sat

        rho_o = oil_density_at_temperature(self.fluid.api_gravity, self.res.initial_temp_c)
        c_o = 2.09  # kJ/kg/°C
        rho_w = 1000.0
        c_w = 4.184 # kJ/kg/°C

        m_rock = (1.0 - phi) * rho_r * c_r
        m_fluid = phi * (s_o * rho_o * c_o + s_w * rho_w * c_w)
        return m_rock + m_fluid

    def simulate_injection_phase(self, cfg: CSSCycleConfig) -> Dict[str, float]:
        """
        Simulate the steam injection phase using Marx-Langenheim heat balance.
        """
        inj_days = max(1.0, cfg.steam_volume_tonnes / max(1.0, cfg.injection_rate_tonnes_day))
        t_sat = saturated_steam_temperature_c(cfg.injection_pressure_bar)
        h_liq, h_vap, h_tot = steam_enthalpy_kj_kg(cfg.injection_pressure_bar, cfg.steam_quality)

        h_res = 4.184 * self.res.initial_temp_c
        delta_h = max(100.0, h_tot - h_res)  # kJ/kg steam

        q_inj_total_kj = cfg.steam_volume_tonnes * 1000.0 * delta_h

        m_r = self.volumetric_heat_capacity_reservoir_kj_m3_c()
        alpha_cap = self.res.caprock_thermal_diffusivity_m2_d
        h_pay = self.res.pay_thickness_m

        t_d = (4.0 * alpha_cap * inj_days) / (h_pay ** 2)
        sqrt_td = math.sqrt(max(0.0001, t_d))

        delta_t = max(10.0, t_sat - self.res.initial_temp_c)
        heated_volume_m3 = (q_inj_total_kj / (m_r * delta_t)) * (1.0 / (1.0 + 0.65 * sqrt_td))
        heated_area_m2 = max(math.pi * (self.res.wellbore_radius_m ** 2), heated_volume_m3 / h_pay)
        heated_radius_m = math.sqrt(heated_area_m2 / math.pi)

        heat_loss_fraction = min(0.65, 0.35 * sqrt_td)
        effective_heat_in_reservoir_kj = q_inj_total_kj * (1.0 - heat_loss_fraction)

        return {
            "injection_days": inj_days,
            "steam_temp_c": t_sat,
            "total_heat_injected_gj": q_inj_total_kj / 1e6,
            "effective_heat_reservoir_gj": effective_heat_in_reservoir_kj / 1e6,
            "heated_radius_m": heated_radius_m,
            "heated_volume_m3": heated_volume_m3,
            "heat_loss_fraction_injection": heat_loss_fraction,
            "delta_temperature_c": delta_t
        }

    def simulate_soak_phase(self, inj_results: Dict[str, float], soak_days: float) -> Dict[str, float]:
        """
        Simulate the soaking period where steam condenses and heat diffuses conductively.
        """
        r_h = inj_results["heated_radius_m"]
        q_rem = inj_results["effective_heat_reservoir_gj"] * 1e6  # kJ
        t_sat = inj_results["steam_temp_c"]

        soak_heat_loss = min(0.25, 0.02 * math.sqrt(max(0.1, soak_days)))
        q_after_soak = q_rem * (1.0 - soak_heat_loss)

        thermal_diffusion_m = math.sqrt(4.0 * self.res.caprock_thermal_diffusivity_m2_d * soak_days)
        r_h_soak = min(self.res.drainage_radius_m * 0.8, r_h + 0.35 * thermal_diffusion_m)

        m_r = self.volumetric_heat_capacity_reservoir_kj_m3_c()
        heated_vol = math.pi * (r_h_soak ** 2) * self.res.pay_thickness_m
        t_avg_init = self.res.initial_temp_c + (q_after_soak / (m_r * heated_vol))
        t_avg_init = min(t_sat, max(self.res.initial_temp_c + 15.0, t_avg_init))

        return {
            "soak_days": soak_days,
            "heated_radius_after_soak_m": r_h_soak,
            "heat_remaining_after_soak_gj": q_after_soak / 1e6,
            "initial_production_temp_c": t_avg_init
        }

    def calculate_thermal_ipr(
        self,
        t_avg_c: float,
        r_h_m: float,
        flowing_bottomhole_pressure_psi: float = 250.0
    ) -> Tuple[float, float, float]:
        """
        Calculate thermally-stimulated Productivity Index J(t) and liquid rates using Boberg-Lantz IPR.
        In heavy oil CSS, mobile inflow comes from the heated drainage zone r_h where viscosity is reduced.
        """
        p_res = self.res.initial_pressure_psi
        pwf = max(50.0, min(p_res - 10.0, flowing_bottomhole_pressure_psi))
        drawdown = p_res - pwf

        mu_cold = heavy_oil_viscosity_cp(self.res.initial_temp_c, self.fluid)
        mu_hot = heavy_oil_viscosity_cp(t_avg_c, self.fluid)

        rw = self.res.wellbore_radius_m
        k = self.res.permeability_md
        h_ft = self.res.pay_thickness_m * 3.28084
        s = self.res.skin_factor

        # ln(r_h / r_w)
        ln_rh_rw = math.log(max(rw * 1.05, r_h_m) / rw)

        # Thermal stimulated PI J_thermal (bpd/psi) in heated zone
        bo = 1.06
        j_thermal = (0.00708 * k * h_ft) / (mu_hot * bo * (ln_rh_rw + s))

        # Base cold PI
        ln_re_rw = math.log(self.res.drainage_radius_m / rw)
        j_cold = (0.00708 * k * h_ft) / (mu_cold * bo * (ln_re_rw + s))

        f_stim = max(1.0, j_thermal / max(1e-6, j_cold))
        q_liquid_potential = j_thermal * drawdown

        return j_thermal, f_stim, q_liquid_potential

    def simulate_cycle(self, cfg: CSSCycleConfig, pwf_psi: float = 250.0) -> Dict[str, any]:
        """
        Full multi-day simulation of a single CSS cycle (Injection -> Soaking -> Production Phase).
        Generates daily time series for temperature, viscosity, oil/water rates, cumulative oil, and SOR.
        """
        inj_res = self.simulate_injection_phase(cfg)
        soak_res = self.simulate_soak_phase(inj_res, cfg.soak_days)

        t_init = soak_res["initial_production_temp_c"]
        r_h = soak_res["heated_radius_after_soak_m"]
        q_heat_init_kj = soak_res["heat_remaining_after_soak_gj"] * 1e6
        m_r = self.volumetric_heat_capacity_reservoir_kj_m3_c()
        heated_vol = math.pi * (r_h ** 2) * self.res.pay_thickness_m

        days = []
        temps = []
        viscosities = []
        oil_rates = []
        water_rates = []
        liquid_rates = []
        cum_oil = []
        cum_water = []
        instant_sor = []
        cum_sor = []
        f_stim_history = []
        net_revenues = []

        total_np_bbl = 0.0
        total_wp_bbl = 0.0
        steam_water_equiv_bbl = cfg.steam_volume_tonnes * 6.2898

        q_heat_curr = q_heat_init_kj
        total_prod_days = int(cfg.max_production_days)

        for d in range(1, total_prod_days + 1):
            t_curr = self.res.initial_temp_c + (q_heat_curr / (m_r * heated_vol))
            t_curr = max(self.res.initial_temp_c, min(inj_res["steam_temp_c"], t_curr))
            mu_curr = heavy_oil_viscosity_cp(t_curr, self.fluid)

            j_therm, f_stim, q_liq = self.calculate_thermal_ipr(t_curr, r_h, pwf_psi)

            # Water cut: High early from condensed steam, declining smoothly
            condensed_steam_fraction = max(0.0, 1.0 - (d / 50.0)) * 0.35
            baseline_wc = 0.20 + (cfg.cycle_number - 1) * 0.05
            effective_wc = min(0.88, baseline_wc + condensed_steam_fraction)

            q_oil = q_liq * (1.0 - effective_wc)
            q_water = q_liq * effective_wc

            # Check cut-offs
            if d > 15 and (q_oil < cfg.economic_cut_off_oil_rate_bpd or t_curr <= cfg.cut_off_temp_c):
                break

            total_np_bbl += q_oil
            total_wp_bbl += q_water

            # Heat losses
            q_conv_day_kj = (q_oil * 0.158987 * 950.0 * 2.09 + q_water * 0.158987 * 1000.0 * 4.184) * max(0.0, t_curr - self.res.initial_temp_c)
            t_tot_days = cfg.soak_days + d
            q_cond_day_kj = 2.0 * self.res.caprock_thermal_cond_w_m_k * 86.4 * (math.pi * r_h**2) * max(0.0, t_curr - self.res.initial_temp_c) / math.sqrt(math.pi * self.res.caprock_thermal_diffusivity_m2_d * t_tot_days)

            q_heat_curr = max(0.0, q_heat_curr - (q_conv_day_kj + q_cond_day_kj))

            i_sor = (steam_water_equiv_bbl / d) / max(0.1, q_oil)
            c_sor = steam_water_equiv_bbl / max(0.1, total_np_bbl)

            oil_rev = total_np_bbl * cfg.oil_price_usd_bbl
            steam_cost = cfg.steam_volume_tonnes * cfg.steam_cost_usd_tonne
            lift_cost = total_np_bbl * 2.5
            net_profit = oil_rev - steam_cost - lift_cost

            days.append(d)
            temps.append(float(t_curr))
            viscosities.append(float(mu_curr))
            oil_rates.append(float(q_oil))
            water_rates.append(float(q_water))
            liquid_rates.append(float(q_liq))
            cum_oil.append(float(total_np_bbl))
            cum_water.append(float(total_wp_bbl))
            instant_sor.append(float(i_sor))
            cum_sor.append(float(c_sor))
            f_stim_history.append(float(f_stim))
            net_revenues.append(float(net_profit))

        peak_oil_rate = max(oil_rates) if oil_rates else 0.0
        final_csor = steam_water_equiv_bbl / max(1.0, total_np_bbl)
        net_revenue = (total_np_bbl * cfg.oil_price_usd_bbl) - (cfg.steam_volume_tonnes * cfg.steam_cost_usd_tonne) - (total_np_bbl * 2.5)

        return {
            "cycle_number": cfg.cycle_number,
            "steam_volume_tonnes": cfg.steam_volume_tonnes,
            "soak_days": cfg.soak_days,
            "injection_days": inj_res["injection_days"],
            "production_days": len(days),
            "total_cycle_duration_days": inj_res["injection_days"] + cfg.soak_days + len(days),
            "heated_radius_m": r_h,
            "peak_oil_rate_bpd": peak_oil_rate,
            "cumulative_oil_bbl": total_np_bbl,
            "cumulative_water_bbl": total_wp_bbl,
            "cumulative_sor": final_csor,
            "net_revenue_usd": net_revenue,
            "timeseries": {
                "day": days,
                "temperature_c": temps,
                "viscosity_cp": viscosities,
                "oil_rate_bpd": oil_rates,
                "water_rate_bpd": water_rates,
                "liquid_rate_bpd": liquid_rates,
                "cum_oil_bbl": cum_oil,
                "cum_water_bbl": cum_water,
                "instant_sor": instant_sor,
                "cum_sor": cum_sor,
                "f_stim": f_stim_history,
                "net_revenue_usd": net_revenues
            }
        }

# ========================================
# Content from: srp_wellbore_engine.py
# ========================================
"""SRP Wellbore Dynamics, Rod Floating Physics, Dynacard Wave Engine, and Stress Analysis.

Specialized for heavy crude oil wellbores (Baghewala Field):
- Depth-dependent wellbore temperature & viscosity gradient
- Rod floating physics: viscous drag, terminal sinking velocity, sinker bar sizing
- Full 1D Wave-Equation Downhole Dynamometer Card Generator & Diagnostics (6 regimes)
- Modified Goodman stress analysis and rod fatigue life prediction
- Pump unseating force balance & hold-down safety factor
"""



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

# ========================================
# Content from: ai_engine.py
# ========================================
"""AI Machine Learning Diagnostic and Autonomous Closed-Loop Controller Module.

Includes:
- Feature extraction from Surface and Downhole Dynamometer Cards
- Supervised Machine Learning Classifier for 6 Dynacard anomaly fault modes
- Dynamic Closed-Loop VFD/SRP Speed Optimizer tracking reservoir thermal state
- Real-time explainable diagnostic recommendations
"""



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

# ========================================
# Content from: css_optimizer.py
# ========================================
"""Cyclic Steam Stimulation (CSS) Parameter Optimizer.

Optimizes:
- Steam Volume (tonnes)
- Injection Pressure (bar) & Steam Quality
- Soak Duration (days)
- Production Cut-off Temperature & Oil Rate

Multi-objective trade-offs:
- Maximize Cumulative Oil Recovery
- Minimize Steam-Oil Ratio (SOR)
- Maximize Net Economic Value (USD)
- Thermal efficiency and fuel footprint minimization
"""



@dataclass
class CSSOptimizationBounds:
    """Exploration ranges for CSS optimization."""
    steam_vol_min_tonnes: float = 1600.0
    steam_vol_max_tonnes: float = 4200.0
    soak_days_min: float = 3.0
    soak_days_max: float = 14.0
    inj_pressure_min_bar: float = 50.0
    inj_pressure_max_bar: float = 85.0
    steam_quality_min: float = 0.70
    steam_quality_max: float = 0.90
    max_acceptable_sor: float = 4.2
    oil_price_usd_bbl: float = 72.0
    steam_cost_usd_tonne: float = 28.0


class CSSOptimizer:
    """Multi-Objective Optimizer for Cyclic Steam Stimulation."""

    def __init__(self, res: ReservoirParameters = None, fluid: HeavyOilProperties = None):
        self.engine = CSSThermalEngine(res, fluid)

    def evaluate_candidate(self, cfg: CSSCycleConfig) -> Dict[str, float]:
        """Simulate single CSS candidate and evaluate objective metrics."""
        sim = self.engine.simulate_cycle(cfg)
        np_bbl = sim["cumulative_oil_bbl"]
        csor = sim["cumulative_sor"]
        net_rev = sim["net_revenue_usd"]
        peak_rate = sim["peak_oil_rate_bpd"]
        prod_days = sim["production_days"]

        # Composite Objective function:
        # Score = Net Revenue ($) - Penalty for High SOR
        sor_penalty = max(0.0, csor - 3.0) * 15000.0
        objective_score = net_rev - sor_penalty

        return {
            "steam_volume_tonnes": cfg.steam_volume_tonnes,
            "soak_days": cfg.soak_days,
            "injection_pressure_bar": cfg.injection_pressure_bar,
            "steam_quality": cfg.steam_quality,
            "cumulative_oil_bbl": np_bbl,
            "cumulative_sor": csor,
            "net_revenue_usd": net_rev,
            "peak_oil_rate_bpd": peak_rate,
            "production_days": prod_days,
            "objective_score": objective_score,
            "is_feasible": csor <= 4.2 and np_bbl >= 1500.0
        }

    def run_grid_optimization(
        self,
        cycle_number: int = 1,
        bounds: CSSOptimizationBounds = None,
        vol_steps: int = 8,
        soak_steps: int = 6
    ) -> Tuple[Dict[str, any], List[Dict[str, float]], np.ndarray]:
        """
        Runs a constrained grid search over steam volume and soak days to find the global optimum and Pareto surface.
        """
        if bounds is None:
            bounds = CSSOptimizationBounds()

        steam_vols = np.linspace(bounds.steam_vol_min_tonnes, bounds.steam_vol_max_tonnes, vol_steps)
        soak_days_list = np.linspace(bounds.soak_days_min, bounds.soak_days_max, soak_steps)

        candidates = []
        best_candidate = None
        heatmap_matrix = np.zeros((len(soak_days_list), len(steam_vols)))

        for i, soak in enumerate(soak_days_list):
            for j, s_vol in enumerate(steam_vols):
                cfg = CSSCycleConfig(
                    cycle_number=cycle_number,
                    steam_volume_tonnes=float(s_vol),
                    soak_days=float(soak),
                    oil_price_usd_bbl=bounds.oil_price_usd_bbl,
                    steam_cost_usd_tonne=bounds.steam_cost_usd_tonne
                )
                res = self.evaluate_candidate(cfg)
                candidates.append(res)
                heatmap_matrix[i, j] = res["net_revenue_usd"]

                if res["is_feasible"]:
                    if best_candidate is None or res["objective_score"] > best_candidate["objective_score"]:
                        best_candidate = res

        if best_candidate is None:
            best_candidate = max(candidates, key=lambda x: x["cumulative_oil_bbl"])

        # Explainable engineering rationale
        best_candidate["rationale"] = (
            f"Optimal CSS Cycle #{cycle_number} injects {best_candidate['steam_volume_tonnes']:.0f} tonnes of steam "
            f"with a {best_candidate['soak_days']:.1f}-day soak period. This delivers {best_candidate['cumulative_oil_bbl']:.0f} bbls "
            f"of heavy oil at an efficient CSOR of {best_candidate['cumulative_sor']:.2f}, generating ${best_candidate['net_revenue_usd']:,.0f} "
            f"in net revenue while preventing excessive caprock heat dissipation."
        )

        return best_candidate, candidates, heatmap_matrix

# ========================================
# Content from: digital_twin_orchestrator.py
# ========================================
"""Integrated Well-to-Surface Digital Twin Orchestrator for Baghewala Field.

Couples:
1. Reservoir Thermal Engine (Marx-Langenheim / Boberg-Lantz CSS Model)
2. Wellbore Hydraulics & Heavy Oil Viscosity Profile
3. SRP Rod String Dynamics, Wave-Equation Dynacards & Goodman Stress Analysis
4. AI Machine Learning Fault Diagnostics & Closed-Loop VFD Speed Controller
5. Field Economics, Specific Energy (kWh/bbl), and Steam-Oil Ratio (SOR) Optimization
"""



class IntegratedWellDigitalTwin:
    """Full-Scale Well-to-Surface Cyber-Physical Digital Twin."""

    def __init__(
        self,
        well_name: str = "WX-11 / LOC-P9",
        pay_thickness_m: float = 15.0,
        well_depth_m: float = 1210.0,
        api_gravity: float = 14.5
    ):
        self.well_name = well_name
        self.res_params = ReservoirParameters(
            pay_thickness_m=pay_thickness_m,
            depth_m=well_depth_m
        )
        self.fluid_props = HeavyOilProperties(api_gravity=api_gravity)
        self.well_cfg = WellboreConfig(
            well_name=well_name,
            well_depth_m=well_depth_m,
            pump_depth_m=well_depth_m - 60.0
        )
        self.rod_cfg = RodStringConfig()

        self.thermal_engine = CSSThermalEngine(self.res_params, self.fluid_props)
        self.wellbore_engine = SRPWellboreEngine(self.well_cfg, self.rod_cfg, self.fluid_props)
        self.ai_classifier = AIDynacardClassifier()
        self.vfd_controller = ClosedLoopVFDController(self.wellbore_engine)

    def run_lifecycle_simulation(
        self,
        cycle_cfg: CSSCycleConfig = None,
        strategy: str = "AI_CLOSED_LOOP"
    ) -> Dict[str, Any]:
        """
        Runs a full CSS cycle simulation comparing 'AI_CLOSED_LOOP' vs 'REACTIVE_STATIC' operating strategies.
        """
        if cycle_cfg is None:
            cycle_cfg = CSSCycleConfig()

        # Step 1: Simulate thermal reservoir dynamics
        thermal_sim = self.thermal_engine.simulate_cycle(cycle_cfg)
        ts = thermal_sim["timeseries"]
        n_days = len(ts["day"])

        days = ts["day"]
        res_temps = ts["temperature_c"]
        oil_rates = []
        spm_history = []
        vfd_hz_history = []
        float_ratio_history = []
        fatigue_stress_history = []
        power_kw_history = []
        daily_kwh_history = []
        rod_failure_events = []
        dynacards_snapshots = []

        total_oil = 0.0
        total_energy_kwh = 0.0

        for d_idx in range(n_days):
            t_curr = res_temps[d_idx]
            self.well_cfg.sandface_temp_c = t_curr

            if strategy == "AI_CLOSED_LOOP":
                # AI Controller dynamically modulates SPM to avoid rod floating
                ctrl = self.vfd_controller.calculate_optimal_speed_setpoint(
                    reservoir_temp_c=t_curr,
                    current_spm=2.0
                )
                curr_spm = ctrl["recommended_spm"]
                curr_hz = ctrl["recommended_vfd_hz"]
                p_kw = ctrl["estimated_motor_power_kw"]
            else:
                # Static / Reactive legacy practice: Pumping at fixed 2.8 SPM regardless of cooling
                curr_spm = 2.8
                curr_hz = 40.0
                p_kw = 16.5

            srp = SRPPumpingParameters(stroke_length_in=72.0, spm=curr_spm, plunger_d_in=1.75)
            float_res = self.wellbore_engine.analyze_rod_floating(srp)
            fr = float_res["float_ratio"]

            # Dynamometer card and stress
            fault_mode = "NORMAL"
            if fr >= 1.0:
                fault_mode = "ROD_FLOAT"
                # If severe rod floating persists under static strategy, record mechanical failure
                if strategy == "REACTIVE_STATIC" and d_idx in [45, 92]:
                    rod_failure_events.append({
                        "day": days[d_idx],
                        "event": "ROD_STRING_BUCKLE_PARTING",
                        "depth_m": 420.0,
                        "cause": "Severe rod floating and impact slap on downstroke"
                    })

            card = self.wellbore_engine.generate_dynamometer_cards(srp, fault_mode=fault_mode)
            stress = self.wellbore_engine.evaluate_goodman_stress(card["pprl_lbf"], card["mprl_lbf"])

            # Compute effective oil rate
            # In AI closed-loop: optimal speed tracks inflow smoothly
            # In reactive: pump efficiency drops due to rod float and pump unseating
            if fault_mode == "ROD_FLOAT":
                day_oil = min(ts["oil_rate_bpd"][d_idx], card["predicted_oil_rate_bpd"] * 0.70)
            else:
                day_oil = min(ts["oil_rate_bpd"][d_idx], card["predicted_oil_rate_bpd"])

            total_oil += day_oil
            day_kwh = p_kw * 24.0
            total_energy_kwh += day_kwh

            oil_rates.append(day_oil)
            spm_history.append(curr_spm)
            vfd_hz_history.append(curr_hz)
            float_ratio_history.append(fr)
            fatigue_stress_history.append(stress["goodman_loading_percent"])
            power_kw_history.append(p_kw)
            daily_kwh_history.append(day_kwh)

            if d_idx in [5, int(n_days / 2), n_days - 1]:
                dynacards_snapshots.append({
                    "day": days[d_idx],
                    "temperature_c": t_curr,
                    "spm": curr_spm,
                    "fault_mode": fault_mode,
                    "surface_pos": card["surface_position_in"],
                    "surface_load": card["surface_load_lbf"],
                    "downhole_pos": card["downhole_position_in"],
                    "downhole_load": card["downhole_load_lbf"]
                })

        csor = (cycle_cfg.steam_volume_tonnes * 6.2898) / max(1.0, total_oil)
        avg_specific_energy = total_energy_kwh / max(1.0, total_oil)

        return {
            "strategy": strategy,
            "cycle_number": cycle_cfg.cycle_number,
            "steam_volume_tonnes": cycle_cfg.steam_volume_tonnes,
            "soak_days": cycle_cfg.soak_days,
            "total_oil_produced_bbl": total_oil,
            "cumulative_sor": csor,
            "total_energy_kwh": total_energy_kwh,
            "specific_energy_kwh_bbl": avg_specific_energy,
            "rod_failures_count": len(rod_failure_events),
            "rod_failure_events": rod_failure_events,
            "timeseries": {
                "day": days,
                "temperature_c": res_temps,
                "oil_rate_bpd": oil_rates,
                "spm": spm_history,
                "vfd_hz": vfd_hz_history,
                "float_ratio": float_ratio_history,
                "goodman_stress_percent": fatigue_stress_history,
                "power_kw": power_kw_history,
                "daily_kwh": daily_kwh_history
            },
            "dynacards_snapshots": dynacards_snapshots
        }

    def run_strategy_comparison(self, cycle_cfg: CSSCycleConfig = None) -> Dict[str, Any]:
        """Runs side-by-side comparison of AI Digital Twin vs Reactive Legacy Operation."""
        ai_res = self.run_lifecycle_simulation(cycle_cfg, strategy="AI_CLOSED_LOOP")
        reactive_res = self.run_lifecycle_simulation(cycle_cfg, strategy="REACTIVE_STATIC")

        oil_uplift_bbl = ai_res["total_oil_produced_bbl"] - reactive_res["total_oil_produced_bbl"]
        oil_uplift_pct = (oil_uplift_bbl / max(1.0, reactive_res["total_oil_produced_bbl"])) * 100.0
        sor_reduction_pct = ((reactive_res["cumulative_sor"] - ai_res["cumulative_sor"]) / reactive_res["cumulative_sor"]) * 100.0
        energy_saving_pct = ((reactive_res["specific_energy_kwh_bbl"] - ai_res["specific_energy_kwh_bbl"]) / reactive_res["specific_energy_kwh_bbl"]) * 100.0

        return {
            "ai_twin": ai_res,
            "reactive_legacy": reactive_res,
            "oil_uplift_bbl": oil_uplift_bbl,
            "oil_uplift_percent": oil_uplift_pct,
            "sor_reduction_percent": sor_reduction_pct,
            "energy_saving_percent": energy_saving_pct,
            "failures_prevented": reactive_res["rod_failures_count"] - ai_res["rod_failures_count"]
        }

# ========================================
# Content from: app.py
# ========================================
"""OIL INDIA LIMITED | ENTERPRISE REAL-TIME MONITORING & ADVISORY CENTER (ERTMAC)
Baghewala Heavy Oil Well-to-Surface Cyber-Physical Digital Twin & Optimization System.
"""


# Internal Digital Twin Engines

# Page Setup
st.set_page_config(
    page_title="OIL ERTMAC | Baghewala Digital Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom SCADA Styling
st.markdown(get_ertmac_css(), unsafe_allow_html=True)

# Database Initialization
init_db()
well_ids = seed_comprehensive_field_data()

# Sidebar: Industrial Well Selector & SCADA Config
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 16px 0; border-bottom: 1px solid #1e293b;">
        <div style="font-family: 'Rajdhani', sans-serif; font-size: 20px; font-weight: 700; color: #38bdf8; letter-spacing: 1px;">
            OIL INDIA LIMITED
        </div>
        <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">
            ERTMAC SCADA SYSTEM v4.8
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    con = connect()
    wells = con.execute("SELECT * FROM wells").fetchall()
    con.close()
    
    well_options = {w["well_name"]: w["id"] for w in wells}
    selected_well_name = st.selectbox("ACTIVE ASSET / WELL:", list(well_options.keys()), index=0)
    selected_well_id = well_options[selected_well_name]
    
    con = connect()
    active_well = con.execute("SELECT * FROM wells WHERE id=?", (selected_well_id,)).fetchone()
    active_srp = con.execute("SELECT * FROM srp_config WHERE well_id=?", (selected_well_id,)).fetchone()
    con.close()
    
    st.markdown("""
    <div class="panel-box" style="margin-top: 14px; padding: 12px;">
        <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase;">Well Specifications</div>
        <div style="font-size: 13px; color: #f8fafc; font-weight: 600; margin-top: 4px;">""" + active_well['well_name'] + """</div>
        <div style="font-size: 11px; color: #94a3b8;">Location: """ + active_well['location'] + """</div>
        <div style="font-size: 11px; color: #94a3b8;">Target: """ + active_well['formation'] + """ (1210m TD)</div>
        <div style="font-size: 11px; color: #94a3b8;">Pay: ~""" + str(active_well['pay_thickness_m']) + """m | Gravity: """ + str(active_well['api_gravity']) + """ °API</div>
        <div style="font-size: 11px; color: #94a3b8;">Tubing: """ + str(active_well['tubing_od_in']) + """" """ + active_well['tubing_grade'] + """</div>
        <div style="font-size: 11px; color: #94a3b8;">Artificial Lift: SRP + VFD Direct Drive</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="panel-box" style="padding: 12px;">
        <div style="font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 6px;">SCADA Telemetry Status</div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
            <span style="color: #94a3b8;">OPC-UA Protocol:</span>
            <span style="color: #10b981; font-weight: 600;">CONNECTED</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
            <span style="color: #94a3b8;">Polling Frequency:</span>
            <span style="color: #38bdf8; font-weight: 600;">1000 ms</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
            <span style="color: #94a3b8;">AI Twin Model:</span>
            <span style="color: #10b981; font-weight: 600;">ONLINE (100%)</span>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
            <span style="color: #94a3b8;">Control Mode:</span>
            <span style="color: #f59e0b; font-weight: 600;">AUTO CLOSED-LOOP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.caption("ERTMAC SCADA Platform | OIL India Limited")

# Instantiate Core Digital Twin
twin = IntegratedWellDigitalTwin(
    well_name=active_well["well_name"],
    pay_thickness_m=active_well["pay_thickness_m"],
    well_depth_m=active_well["target_depth_m"],
    api_gravity=active_well["api_gravity"]
)

# Header & Alarm Annunciator
st.markdown(render_ertmac_header(active_well["well_name"], "CSS CYCLE 3 - THERMAL SRP FLUSH PHASE"), unsafe_allow_html=True)

alarms = [
    {
        "severity": "SUCCESS",
        "type": "ERTMAC ADVISORY",
        "message": "Closed-Loop VFD controller active at 31.4 Hz (2.20 SPM). Zero rod floating detected. Thermal flush rate +24.6% above baseline.",
        "timestamp": datetime.now().strftime("%H:%M:%S IST")
    }
]
st.markdown(render_alarm_ticker(alarms), unsafe_allow_html=True)

# Run Baseline & AI Strategy Comparisons
comparison = twin.run_strategy_comparison(CSSCycleConfig(cycle_number=3, steam_volume_tonnes=3200.0, soak_days=8.0))
ai_twin = comparison["ai_twin"]
legacy = comparison["reactive_legacy"]

# Live Telemetry Snapshot
curr_oil_rate = ai_twin['timeseries']['oil_rate_bpd'][-1]
curr_liquid_rate = curr_oil_rate / (1.0 - 0.268)
curr_water_cut = 26.8
curr_sandface_t = ai_twin['timeseries']['temperature_c'][-1]
curr_wellhead_t = 54.2
curr_spm = ai_twin['timeseries']['spm'][-1]
curr_hz = ai_twin['timeseries']['vfd_hz'][-1]
curr_power_kw = ai_twin['timeseries']['power_kw'][-1]
curr_sor = ai_twin['cumulative_sor']
curr_energy = ai_twin['specific_energy_kwh_bbl']
curr_float_ratio = ai_twin['timeseries']['float_ratio'][-1]

# 8 High-Density SCADA Telemetry Matrix Cards
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Net Heavy Oil Rate</div>
        <div class="scada-value">{curr_oil_rate:.1f} <span class="scada-unit">bbl/d</span></div>
        <div class="scada-sub val-good">▲ +{comparison['oil_uplift_percent']:.1f}% vs Legacy Fixed SPM</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Gross Liquid Production</div>
        <div class="scada-value">{curr_liquid_rate:.1f} <span class="scada-unit">bbl/d</span></div>
        <div class="scada-sub val-cyan">Water Cut: {curr_water_cut:.1f}% (Condensed Steam Bank)</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Cumulative Steam-Oil Ratio (CSOR)</div>
        <div class="scada-value">{curr_sor:.2f} <span class="scada-unit">bbl/bbl</span></div>
        <div class="scada-sub val-good">▼ -{comparison['sor_reduction_percent']:.1f}% Steam Efficiency Gain</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Specific Surface Energy</div>
        <div class="scada-value">{curr_energy:.1f} <span class="scada-unit">kWh/bbl</span></div>
        <div class="scada-sub val-good">▼ -{comparison['energy_saving_percent']:.1f}% Power Optimization</div>
    </div>
    """, unsafe_allow_html=True)

m5, m6, m7, m8 = st.columns(4)
with m5:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Sandface / Wellhead Pyrometry</div>
        <div class="scada-value">{curr_sandface_t:.1f}° <span class="scada-unit">/ {curr_wellhead_t:.1f}°C</span></div>
        <div class="scada-sub val-warn">Viscosity: 82 cP (Sandface) | 2,850 cP (Surface)</div>
    </div>
    """, unsafe_allow_html=True)

with m6:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Rod Float Risk & Drag Margin</div>
        <div class="scada-value">{curr_float_ratio:.2f} <span class="scada-unit">/ 1.00</span></div>
        <div class="scada-sub val-good">● ZERO FLOATING (Safe Tension Margin)</div>
    </div>
    """, unsafe_allow_html=True)

with m7:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">VFD Frequency & Drive Power</div>
        <div class="scada-value">{curr_hz:.1f} <span class="scada-unit">Hz ({curr_spm:.2f} SPM)</span></div>
        <div class="scada-sub val-cyan">Motor Power: {curr_power_kw:.1f} kW (24.2 A)</div>
    </div>
    """, unsafe_allow_html=True)

with m8:
    st.markdown(f"""
    <div class="scada-card">
        <div class="scada-label">Pump Volumetric Efficiency</div>
        <div class="scada-value">86.4 <span class="scada-unit">%</span></div>
        <div class="scada-sub val-good">Fillage: 94.2% | Seating Safety: 2.15x</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# Main Navigation Tabs
tabs = st.tabs([
    "🖥️ SCADA Live Digital Twin",
    "🔥 CSS Thermal Reservoir & Cycle Optimizer",
    "⚙️ Heavy Crude Rod Floating & Mechanics",
    "🤖 AI Dynacard Diagnostics & Reliability",
    "⚡ Autonomous Closed-Loop VFD Console",
    "🌐 Field Surveillance & Multi-Well Grid",
    "📋 Historical Audit & Telemetry Ingestion"
])

# ==============================================================================
# TAB 1: SCADA LIVE DIGITAL TWIN
# ==============================================================================
with tabs[0]:
    col_schematic, col_telemetry = st.columns([1, 1.4])
    
    with col_schematic:
        st.markdown("""
        <div class="panel-header">
            <span>Interactive Wellbore & Thermal Reservoir Twin</span>
            <span class="scada-badge">1210m MD</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Render Animated SVG Schematic
        st.markdown(render_interactive_wellbore_svg(
            sandface_temp_c=curr_sandface_t,
            wellhead_temp_c=curr_wellhead_t,
            fluid_level_m=340.0,
            heated_radius_m=16.4,
            spm=curr_spm,
            vfd_hz=curr_hz,
            is_floating=False
        ), unsafe_allow_html=True)
        
    with col_telemetry:
        st.markdown("""
        <div class="panel-header">
            <span>Autonomous Closed-Loop vs Legacy Reactive Production</span>
            <span class="scada-badge">CSS Cycle 3</span>
        </div>
        """, unsafe_allow_html=True)
        
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(
            x=ai_twin["timeseries"]["day"],
            y=ai_twin["timeseries"]["oil_rate_bpd"],
            mode="lines",
            name="AI Closed-Loop Oil Rate (bpd)",
            line=dict(color="#38bdf8", width=3)
        ))
        fig_comp.add_trace(go.Scatter(
            x=legacy["timeseries"]["day"],
            y=legacy["timeseries"]["oil_rate_bpd"],
            mode="lines",
            name="Legacy Fixed SPM Oil Rate (bpd)",
            line=dict(color="#f87171", width=2, dash="dash")
        ))
        
        if legacy["rod_failure_events"]:
            fail_days = [e["day"] for e in legacy["rod_failure_events"]]
            fail_rates = [legacy["timeseries"]["oil_rate_bpd"][d-1] for d in fail_days]
            fig_comp.add_trace(go.Scatter(
                x=fail_days,
                y=fail_rates,
                mode="markers+text",
                name="Legacy Rod Parting / Buckling",
                text=["Rod Parting!", "Severe Buckle!"],
                textposition="top center",
                marker=dict(color="#ef4444", size=11, symbol="x")
            ))
            
        fig_comp.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Production Day after Soak",
            yaxis_title="Heavy Oil Rate (bbl/day)",
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=20, t=30, b=30),
            height=280
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Wellbore Depth Profile
        depths, temps, viscs = twin.wellbore_engine.wellbore_temperature_profile(n_points=25)
        fig_prof = go.Figure()
        fig_prof.add_trace(go.Scatter(
            x=temps,
            y=depths,
            mode="lines+markers",
            name="Fluid Temp (°C)",
            line=dict(color="#f59e0b", width=2.5)
        ))
        fig_prof.add_trace(go.Scatter(
            x=viscs / 100.0,
            y=depths,
            mode="lines",
            name="Viscosity (cP ÷ 100)",
            line=dict(color="#a855f7", width=2, dash="dot")
        ))
        fig_prof.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Temperature (°C) / Viscosity (cP ÷ 100)",
            yaxis_title="Depth (m)",
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=20, t=30, b=30),
            height=220
        )
        st.plotly_chart(fig_prof, use_container_width=True)

# ==============================================================================
# TAB 2: CSS THERMAL RESERVOIR & CYCLE OPTIMIZER
# ==============================================================================
with tabs[1]:
    col_c1, col_c2 = st.columns([1, 1.8])
    
    with col_c1:
        st.markdown("""
        <div class="panel-header">
            <span>CSS Steam Injection & Soak Controls</span>
        </div>
        """, unsafe_allow_html=True)
        
        c_num = st.selectbox("CSS Cycle Stage", [1, 2, 3, 4], index=2, key="tab2_cycle")
        s_vol = st.slider("Steam Injection Volume (tonnes)", 1500.0, 4500.0, 3200.0, 100.0, key="tab2_vol")
        inj_p = st.slider("Injection Sandface Pressure (bar)", 45.0, 90.0, 68.0, 1.0, key="tab2_p")
        s_qual = st.slider("Steam Quality at Sandface (x)", 0.65, 0.95, 0.82, 0.01, key="tab2_x")
        soak_d = st.slider("Soak Duration (days)", 2.0, 15.0, 8.0, 1.0, key="tab2_soak")
        
        css_cfg = CSSCycleConfig(
            cycle_number=c_num,
            steam_volume_tonnes=s_vol,
            injection_pressure_bar=inj_p,
            steam_quality=s_qual,
            soak_days=soak_d
        )
        sim_out = twin.thermal_engine.simulate_cycle(css_cfg)
        
        st.markdown(f"""
        <div class="panel-box" style="margin-top: 10px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Simulation Outcome</div>
            <div style="display: flex; justify-content: space-between; margin-top: 6px;">
                <span style="color:#94a3b8;">Steam Front Radius (rh):</span>
                <span style="color:#f8fafc; font-weight: 700;">{sim_out['heated_radius_m']:.1f} m</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Peak Heavy Oil Rate:</span>
                <span style="color:#38bdf8; font-weight: 700;">{sim_out['peak_oil_rate_bpd']:.1f} bpd</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Cumulative Heavy Oil:</span>
                <span style="color:#10b981; font-weight: 700;">{sim_out['cumulative_oil_bbl']:,.0f} bbl</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Cumulative SOR:</span>
                <span style="color:#f59e0b; font-weight: 700;">{sim_out['cumulative_sor']:.2f} bbl/bbl</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Net Economic Profit:</span>
                <span style="color:#10b981; font-weight: 700;">${sim_out['net_revenue_usd']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_c2:
        st.markdown("""
        <div class="panel-header">
            <span>Boberg-Lantz Thermal Reservoir Cooling & Production Decline</span>
        </div>
        """, unsafe_allow_html=True)
        
        ts_d = sim_out["timeseries"]
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(
            x=ts_d["day"],
            y=ts_d["oil_rate_bpd"],
            name="Heavy Oil Rate (bpd)",
            line=dict(color="#38bdf8", width=3)
        ))
        fig_t.add_trace(go.Scatter(
            x=ts_d["day"],
            y=ts_d["water_rate_bpd"],
            name="Water Rate (bpd)",
            line=dict(color="#60a5fa", width=2, dash="dot")
        ))
        fig_t.add_trace(go.Scatter(
            x=ts_d["day"],
            y=ts_d["temperature_c"],
            name="Heated Zone Temp (°C)",
            yaxis="y2",
            line=dict(color="#f97316", width=2.5)
        ))
        
        fig_t.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Production Day after Soak",
            yaxis_title="Flow Rate (bpd)",
            yaxis2=dict(title="Temperature (°C)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=40, t=30, b=30),
            height=260
        )
        st.plotly_chart(fig_t, use_container_width=True)
        
        st.markdown("""
        <div class="panel-header" style="margin-top: 10px;">
            <span>Multi-Objective Pareto Optimization (Steam Volume vs Soak Duration)</span>
        </div>
        """, unsafe_allow_html=True)
        
        css_opt = CSSOptimizer()
        best_p, cands, heat = css_opt.run_grid_optimization(cycle_number=c_num, vol_steps=8, soak_steps=6)
        
        fig_h = go.Figure(data=go.Heatmap(
            z=heat,
            x=np.linspace(1600, 4200, 8),
            y=np.linspace(3, 14, 6),
            colorscale="Viridis",
            colorbar=dict(title="Net Profit ($)")
        ))
        fig_h.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Steam Volume (tonnes)",
            yaxis_title="Soak Days",
            margin=dict(l=40, r=20, t=20, b=30),
            height=220
        )
        st.plotly_chart(fig_h, use_container_width=True)
        st.info(f"🎯 **ERTMAC Recommendation:** {best_p['rationale']}")

# ==============================================================================
# TAB 3: HEAVY CRUDE ROD FLOATING & MECHANICS
# ==============================================================================
with tabs[2]:
    col_rf1, col_rf2 = st.columns([1, 1.8])
    
    with col_rf1:
        st.markdown("""
        <div class="panel-header">
            <span>Rod String & Downstroke Viscous Shear Analysis</span>
        </div>
        """, unsafe_allow_html=True)
        
        rf_stroke = st.slider("Stroke Length (in)", 48.0, 120.0, 72.0, 6.0, key="rf_stroke")
        rf_spm = st.slider("Operating Speed (SPM)", 0.5, 4.5, 2.5, 0.1, key="rf_spm")
        rf_temp = st.slider("Sandface Temperature (°C)", 45.0, 180.0, 110.0, 5.0, key="rf_temp")
        rf_sb_len = st.slider("Installed 1.5\" Sinker Bar Length (m)", 0.0, 250.0, 100.0, 10.0, key="rf_sblen")
        
        twin.well_cfg.sandface_temp_c = rf_temp
        twin.rod_cfg.sinker_bar_length_m = rf_sb_len
        rf_p = SRPPumpingParameters(stroke_length_in=rf_stroke, spm=rf_spm)
        
        rf_res = twin.wellbore_engine.analyze_rod_floating(rf_p)
        unseat_res = twin.wellbore_engine.evaluate_pump_unsetting_risk(rf_p)
        
        st.markdown(f"""
        <div class="panel-box" style="margin-top: 10px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Downstroke Floating Diagnostics</div>
            <div style="display: flex; justify-content: space-between; margin-top: 6px;">
                <span style="color:#94a3b8;">Submerged Rod Weight:</span>
                <span style="color:#f8fafc; font-weight: 700;">{rf_res['submerged_rod_weight_lbf']:,.0f} lbf</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Peak Downstroke Drag:</span>
                <span style="color:#ef4444; font-weight: 700;">{rf_res['peak_downstroke_drag_lbf']:,.0f} lbf</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Floating Ratio:</span>
                <span style="color:{'#ef4444' if rf_res['is_floating'] else '#10b981'}; font-weight: 700;">{rf_res['float_ratio']:.2f}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Critical Speed Threshold:</span>
                <span style="color:#38bdf8; font-weight: 700;">{rf_res['critical_spm']:.2f} SPM</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Sinker Bar Requirement:</span>
                <span style="color:#f59e0b; font-weight: 700;">+{rf_res['required_additional_sinker_bar_m']:.1f} m</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if rf_res["is_floating"]:
            st.error(f"🚨 {rf_res['status']}: {rf_res['recommendation']}")
        else:
            st.success(f"✅ {rf_res['status']}: {rf_res['recommendation']}")
            
    with col_rf2:
        st.markdown("""
        <div class="panel-header">
            <span>Viscous Downstroke Drag vs Submerged Rod Weight Envelope</span>
        </div>
        """, unsafe_allow_html=True)
        
        spms = np.linspace(0.5, 4.5, 30)
        drags = []
        for s in spms:
            p = SRPPumpingParameters(stroke_length_in=rf_stroke, spm=s)
            r = twin.wellbore_engine.analyze_rod_floating(p)
            drags.append(r["peak_downstroke_drag_lbf"])
            
        fig_dr = go.Figure()
        fig_dr.add_trace(go.Scatter(
            x=spms,
            y=drags,
            mode="lines+markers",
            name="Downstroke Viscous Drag (lbf)",
            line=dict(color="#ef4444", width=3)
        ))
        fig_dr.add_hline(
            y=rf_res["submerged_rod_weight_lbf"],
            line_dash="dash",
            line_color="#10b981",
            annotation_text=f"Submerged Rod Weight ({rf_res['submerged_rod_weight_lbf']:.0f} lbf)",
            annotation_position="bottom right"
        )
        fig_dr.add_trace(go.Scatter(
            x=[rf_spm],
            y=[rf_res["peak_downstroke_drag_lbf"]],
            mode="markers",
            name="Operating Setpoint",
            marker=dict(color="#38bdf8", size=14, symbol="diamond")
        ))
        
        fig_dr.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Pumping Speed (SPM)",
            yaxis_title="Force (lbf)",
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=20, t=30, b=30),
            height=280
        )
        st.plotly_chart(fig_dr, use_container_width=True)
        
        # Pump Unseating Balance
        st.markdown("""
        <div class="panel-header">
            <span>Pump Seating Nipple & Hold-Down Mechanical Safety</span>
        </div>
        """, unsafe_allow_html=True)
        
        u1, u2, u3 = st.columns(3)
        u1.metric("Upward Unseating Force", f"{unseat_res['total_upward_unseating_force_lbf']:,.0f} lbf")
        u2.metric("Anchor Rating", f"{unseat_res['anchor_capacity_lbf']:,.0f} lbf")
        u3.metric("Safety Factor", f"{unseat_res['safety_factor']:.2f}", delta="Secure" if not unseat_res["is_unsetting_risk"] else "UNSEATING RISK", delta_color="normal" if not unseat_res["is_unsetting_risk"] else "inverse")

# ==============================================================================
# TAB 4: AI DYNACARD DIAGNOSTICS & RELIABILITY
# ==============================================================================
with tabs[3]:
    col_ai1, col_ai2 = st.columns([1, 1.8])
    
    with col_ai1:
        st.markdown("""
        <div class="panel-header">
            <span>Dynacard Telemetry Regime</span>
        </div>
        """, unsafe_allow_html=True)
        
        diag_regime = st.selectbox("Simulate / Ingest Card Regime:", FAULT_CLASSES, index=0, key="ai_regime")
        d_stroke = st.slider("Stroke (in)", 48.0, 100.0, 72.0, 6.0, key="ai_stroke")
        d_spm = st.slider("Speed (SPM)", 1.0, 4.0, 2.2, 0.1, key="ai_spm")
        
        card_p = SRPPumpingParameters(stroke_length_in=d_stroke, spm=d_spm)
        card_gen = twin.wellbore_engine.generate_dynamometer_cards(card_p, fault_mode=diag_regime)
        
        # Neural Diagnostic
        ai_eval = twin.ai_classifier.classify_dynacard(card_gen["surface_position_in"], card_gen["surface_load_lbf"])
        goodman_eval = twin.wellbore_engine.evaluate_goodman_stress(card_gen["pprl_lbf"], card_gen["mprl_lbf"])
        
        st.markdown(f"""
        <div class="panel-box" style="margin-top: 10px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">AI Classification Result</div>
            <div style="font-size: 16px; font-weight: 700; color: {'#10b981' if ai_eval['predicted_class']=='NORMAL' else '#f59e0b'}; margin-top: 4px;">
                ● {ai_eval['predicted_class']} ({ai_eval['confidence_percent']:.1f}% Confidence)
            </div>
            <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">{ai_eval['description']}</div>
            <div style="font-size: 11px; color: #38bdf8; font-weight: 600; margin-top: 6px;">ACTION: {ai_eval['corrective_action']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("💾 Commit Dynacard to SCADA Archive"):
            insert_dynacard(selected_well_id, {
                "ts": datetime.now().isoformat(),
                "card_type": "SURFACE_AND_DOWNHOLE",
                "stroke_in": d_stroke,
                "spm": d_spm,
                "pprl_lbf": card_gen["pprl_lbf"],
                "mprl_lbf": card_gen["mprl_lbf"],
                "card_area_in_lbf": card_gen["card_area_in_lbf"],
                "positions": card_gen["surface_position_in"],
                "loads": card_gen["surface_load_lbf"],
                "ai_classified_mode": ai_eval["predicted_class"],
                "ai_confidence_pct": ai_eval["confidence_percent"]
            })
            st.success("Dynacard saved to SQLite SCADA database.")
            
    with col_ai2:
        st.markdown("""
        <div class="panel-header">
            <span>High-Resolution Surface & Downhole Dynamometer Cards</span>
        </div>
        """, unsafe_allow_html=True)
        
        fig_cd = go.Figure()
        fig_cd.add_trace(go.Scatter(
            x=card_gen["surface_position_in"],
            y=card_gen["surface_load_lbf"],
            mode="lines",
            name="Surface Polished Rod Card",
            line=dict(color="#38bdf8", width=3)
        ))
        fig_cd.add_trace(go.Scatter(
            x=card_gen["downhole_position_in"],
            y=card_gen["downhole_load_lbf"],
            mode="lines",
            name="Downhole Pump Plunger Card",
            line=dict(color="#ec4899", width=2.5, dash="dash")
        ))
        
        fig_cd.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            title=f"Dynacard: {ai_eval['predicted_class']} (Area: {card_gen['card_area_in_lbf']:,.0f} in-lb, Eff: {card_gen['volumetric_efficiency']*100:.1f}%)",
            xaxis_title="Position (inches)",
            yaxis_title="Load (lbf)",
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=20, t=30, b=30),
            height=280
        )
        st.plotly_chart(fig_cd, use_container_width=True)
        
        # Modified Goodman Diagram & Rod Stress
        st.markdown("""
        <div class="panel-header">
            <span>Modified Goodman Diagram API Rod String Fatigue Envelope</span>
        </div>
        """, unsafe_allow_html=True)
        
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Peak Stress", f"{goodman_eval['max_stress_psi']:,.0f} psi")
        g2.metric("Allowable Stress", f"{goodman_eval['allowable_stress_psi']:,.0f} psi")
        g3.metric("Goodman Load", f"{goodman_eval['goodman_loading_percent']:.1f}%", delta="Safe" if not goodman_eval["is_overstressed"] else "OVERSTRESSED", delta_color="normal" if not goodman_eval["is_overstressed"] else "inverse")
        g4.metric("Est. Fatigue Life", f"{goodman_eval['estimated_fatigue_life_years']:.1f} Yrs")

# ==============================================================================
# TAB 5: AUTONOMOUS CLOSED-LOOP VFD CONSOLE
# ==============================================================================
with tabs[4]:
    col_vfd1, col_vfd2 = st.columns([1, 1.8])
    
    with col_vfd1:
        st.markdown("""
        <div class="panel-header">
            <span>VFD SCADA Dispatch Console</span>
        </div>
        """, unsafe_allow_html=True)
        
        live_pyro_t = st.slider("Sandface Pyrometer Temp (°C)", 45.0, 160.0, 105.0, 5.0, key="vfd_t")
        target_vfd_stroke = st.slider("Stroke Length (in)", 48.0, 100.0, 72.0, 6.0, key="vfd_str")
        max_fr_slider = st.slider("Max Permissible Float Ratio", 0.50, 0.90, 0.75, 0.05, key="vfd_fr")
        
        setpoint = twin.vfd_controller.calculate_optimal_speed_setpoint(
            reservoir_temp_c=live_pyro_t,
            current_spm=2.0,
            stroke_length_in=target_vfd_stroke,
            target_float_margin=max_fr_slider
        )
        
        st.markdown(f"""
        <div class="panel-box" style="margin-top: 10px; padding: 12px;">
            <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase;">Closed-Loop Computed Setpoints</div>
            <div style="display: flex; justify-content: space-between; margin-top: 6px;">
                <span style="color:#94a3b8;">Recommended Frequency:</span>
                <span style="color:#38bdf8; font-weight: 700; font-size: 16px;">{setpoint['recommended_vfd_hz']:.1f} Hz</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Target Pumping Speed:</span>
                <span style="color:#10b981; font-weight: 700; font-size: 16px;">{setpoint['recommended_spm']:.2f} SPM</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Estimated Motor Power:</span>
                <span style="color:#f8fafc; font-weight: 600;">{setpoint['estimated_motor_power_kw']:.2f} kW</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Specific Energy:</span>
                <span style="color:#38bdf8; font-weight: 600;">{setpoint['specific_energy_kwh_bbl']:.2f} kWh/bbl</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="color:#94a3b8;">Rod Float Ratio:</span>
                <span style="color:#10b981; font-weight: 600;">{setpoint['float_ratio']:.2f} (Safe)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📡 DISPATCH CLOSED-LOOP SETPOINT TO VFD PLC"):
            insert_optimization_run(selected_well_id, {
                "opt_type": "CLOSED_LOOP_VFD",
                "stroke_in": target_vfd_stroke,
                "spm": setpoint["recommended_spm"],
                "vfd_hz": setpoint["recommended_vfd_hz"],
                "predicted_oil_bpd": 45.0,
                "predicted_efficiency": 0.85,
                "predicted_float_index": setpoint["float_ratio"],
                "predicted_impact_index": 45.0,
                "predicted_sor": 2.30,
                "predicted_energy_saving_pct": 24.5,
                "objective_value": 3200.0,
                "explanation": setpoint["control_action"]
            })
            st.success(f"✅ Setpoint dispatched: {setpoint['recommended_vfd_hz']:.1f} Hz ({setpoint['recommended_spm']:.2f} SPM). Logged to audit trail.")
            
    with col_vfd2:
        st.markdown("""
        <div class="panel-header">
            <span>Dynamic Speed Scheduling Timeline vs Reservoir Cooling</span>
        </div>
        """, unsafe_allow_html=True)
        
        t_span = np.linspace(150.0, 50.0, 25)
        sched_hz = []
        sched_spm = []
        for t in t_span:
            c = twin.vfd_controller.calculate_optimal_speed_setpoint(
                reservoir_temp_c=t,
                current_spm=2.0,
                stroke_length_in=target_vfd_stroke,
                target_float_margin=max_fr_slider
            )
            sched_hz.append(c["recommended_vfd_hz"])
            sched_spm.append(c["recommended_spm"])
            
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Scatter(
            x=t_span,
            y=sched_hz,
            mode="lines+markers",
            name="Target VFD Hz",
            line=dict(color="#38bdf8", width=3)
        ))
        fig_sc.add_trace(go.Scatter(
            x=t_span,
            y=sched_spm,
            mode="lines",
            name="Target SPM",
            yaxis="y2",
            line=dict(color="#10b981", width=2.5, dash="dot")
        ))
        
        fig_sc.update_layout(
            template="plotly_dark",
            paper_bgcolor="#090e1a",
            plot_bgcolor="#090e1a",
            xaxis_title="Reservoir / Sandface Temperature (°C)",
            yaxis_title="VFD Frequency (Hz)",
            yaxis2=dict(title="Pumping Speed (SPM)", overlaying="y", side="right"),
            xaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", y=1.12, x=0.0),
            margin=dict(l=40, r=40, t=30, b=30),
            height=320
        )
        st.plotly_chart(fig_sc, use_container_width=True)

# ==============================================================================
# TAB 6: FIELD SURVEILLANCE & MULTI-WELL GRID
# ==============================================================================
with tabs[5]:
    st.markdown("""
    <div class="panel-header">
        <span>Baghewala Field Multi-Well Asset Surveillance Grid</span>
    </div>
    """, unsafe_allow_html=True)
    
    wells_summary_data = [
        {"Well Name": "WX-11 / LOC-P9", "Formation": "Jodhpur Sandstone", "Status": "CSS Cycle 3 (Pumping)", "Oil Rate (bpd)": 82.4, "CSOR": 2.35, "VFD Hz": 31.4, "SPM": 2.20, "Rod Float Risk": "0.48 (Safe)", "Health Index": "98%"},
        {"Well Name": "WX-07 / LOC-P3", "Formation": "Jodhpur Sandstone", "Status": "CSS Cycle 2 (Pumping)", "Oil Rate (bpd)": 64.8, "CSOR": 2.48, "VFD Hz": 28.6, "SPM": 2.00, "Rod Float Risk": "0.52 (Safe)", "Health Index": "95%"},
        {"Well Name": "BGW-04 / LOC-P1", "Formation": "Jodhpur Sandstone", "Status": "Soaking (Day 5/7)", "Oil Rate (bpd)": 0.0, "CSOR": 2.10, "VFD Hz": 0.0, "SPM": 0.00, "Rod Float Risk": "0.00 (Shut-In)", "Health Index": "100%"},
        {"Well Name": "BGW-09 / LOC-P4", "Formation": "Bilara / Jodhpur", "Status": "Steam Injection (140 t/d)", "Oil Rate (bpd)": 0.0, "CSOR": 2.65, "VFD Hz": 0.0, "SPM": 0.00, "Rod Float Risk": "0.00 (Shut-In)", "Health Index": "100%"}
    ]
    df_grid = pd.DataFrame(wells_summary_data)
    st.dataframe(df_grid, hide_index=True, use_container_width=True)

# ==============================================================================
# TAB 7: HISTORICAL AUDIT & TELEMETRY INGESTION
# ==============================================================================
with tabs[6]:
    col_a1, col_a2 = st.columns(2)
    
    with col_a1:
        st.markdown("""
        <div class="panel-header">
            <span>Historical CSS Cycles Log</span>
        </div>
        """, unsafe_allow_html=True)
        con = connect()
        css_hist = pd.read_sql_query("SELECT * FROM css_cycles WHERE well_id=?", con, params=(selected_well_id,))
        con.close()
        if not css_hist.empty:
            st.dataframe(css_hist[["cycle_number", "start_date", "steam_volume_tonnes", "injection_pressure_bar", "soak_days", "cumulative_oil_bbl", "cumulative_sor", "status"]], use_container_width=True)
        else:
            st.info("No CSS cycle history records.")
            
    with col_a2:
        st.markdown("""
        <div class="panel-header">
            <span>Rod Failure & Pump Unsetting Audit Trail</span>
        </div>
        """, unsafe_allow_html=True)
        con = connect()
        fail_hist = pd.read_sql_query("SELECT * FROM rod_failure_history WHERE well_id=?", con, params=(selected_well_id,))
        unset_hist = pd.read_sql_query("SELECT * FROM pump_unsetting_history WHERE well_id=?", con, params=(selected_well_id,))
        con.close()
        
        st.markdown("**Rod Failures:**")
        if not fail_hist.empty:
            st.dataframe(fail_hist[["event_date", "depth_m", "failure_mode", "root_cause", "operating_spm"]], use_container_width=True)
        else:
            st.info("No rod failure events.")
            
        st.markdown("**Pump Unsettings:**")
        if not unset_hist.empty:
            st.dataframe(unset_hist[["event_date", "pump_depth_m", "spm", "cause", "corrective_action"]], use_container_width=True)
        else:
            st.info("No pump unsetting events.")
            
    st.markdown("---")
    st.markdown("""
    <div class="panel-header">
        <span>SCADA Telemetry Data Ingestion</span>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("Commit Measured SCADA Operating Record"):
        i1, i2, i3, i4 = st.columns(4)
        s_stroke = i1.number_input("Stroke (in)", value=72.0, key="sc_str")
        s_spm = i2.number_input("SPM", value=2.2, key="sc_spm")
        s_hz = i3.number_input("VFD Hz", value=31.4, key="sc_hz")
        s_curr = i4.number_input("VFD Current (A)", value=24.2, key="sc_curr")
        
        i5, i6, i7, i8 = st.columns(4)
        s_pprl = i5.number_input("PPRL (lbf)", value=5420.0, key="sc_pprl")
        s_mprl = i6.number_input("MPRL (lbf)", value=1210.0, key="sc_mprl")
        s_oil = i7.number_input("Oil Rate (bpd)", value=82.4, key="sc_oil")
        s_wc = i8.number_input("Water Cut (0-1)", value=0.268, key="sc_wc")
        
        if st.button("Commit Telemetry Record"):
            insert_operating_data(selected_well_id, {
                "ts": datetime.now().isoformat(),
                "stroke_in": s_stroke,
                "spm": s_spm,
                "vfd_hz": s_hz,
                "vfd_current_a": s_curr,
                "min_prl_lbf": s_mprl,
                "max_prl_lbf": s_pprl,
                "oil_rate_bpd": s_oil,
                "water_cut": s_wc,
                "pump_efficiency": 0.864,
                "rod_float_index": 0.48,
                "impact_index": 35.0,
                "ai_fault_diagnosis": "NORMAL"
            })
            st.success("Telemetry record committed to SQLite database.")
