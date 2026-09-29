"""Heavy Oil PVT and Rheology Module for Baghewala Field.

Includes:
- Viscosity-temperature relationships for heavy / extra-heavy crude (ASTM D341 / Walther, Andrade)
- Fluid density temperature correction
- Saturated steam and water thermodynamic properties
- Dissolved gas GOR, oil formation volume factor Bo, and fluid compressibility
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple


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
