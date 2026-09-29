"""Cyclic Steam Stimulation (CSS) Thermal Reservoir Engine for Baghewala Field.

Implements:
- Marx-Langenheim heat balance during steam injection
- Boberg-Lantz analytical thermal decline model during soaking & production
- Radial temperature distribution and heated zone radius growth
- Thermally-stimulated Inflow Performance Relationship (IPR)
- Multi-cycle CSS simulation (Steam Injection -> Soaking -> SRP Production Phase)
- Energy balance, Steam-Oil Ratio (SOR), and economic thermal efficiency
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
from fluid_pvt import (
    HeavyOilProperties, heavy_oil_viscosity_cp, saturated_steam_temperature_c,
    steam_enthalpy_kj_kg, oil_density_at_temperature
)


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
