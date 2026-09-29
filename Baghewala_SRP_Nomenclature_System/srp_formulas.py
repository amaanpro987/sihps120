
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

from dataclasses import dataclass
from math import pi


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
