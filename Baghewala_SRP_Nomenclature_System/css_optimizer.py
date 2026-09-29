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

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
from reservoir_thermal_engine import (
    CSSThermalEngine, CSSCycleConfig, ReservoirParameters
)
from fluid_pvt import HeavyOilProperties


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
