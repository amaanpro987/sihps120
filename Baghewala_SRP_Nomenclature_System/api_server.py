"""FastAPI REST Server — Well-to-Surface Digital Twin API.

Exposes the full Python physics and AI engine stack as REST endpoints
so the React/Vite frontend can call real engineering models instead of
simplified JavaScript re-implementations.

Run:
    uvicorn api_server:app --reload --port 8000
"""

from __future__ import annotations

import math
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fluid_pvt import HeavyOilProperties, heavy_oil_viscosity_cp
from reservoir_thermal_engine import CSSThermalEngine, ReservoirParameters, CSSCycleConfig
from srp_wellbore_engine import (
    SRPWellboreEngine,
    WellboreConfig,
    RodStringConfig,
    SRPPumpingParameters,
)
from ai_engine import AIDynacardClassifier, ClosedLoopVFDController
from digital_twin_orchestrator import IntegratedWellDigitalTwin

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Baghewala Digital Twin API",
    description="AI-enabled Well-to-Surface Digital Twin for CSS–SRP optimisation",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Singleton heavy objects (trained once at startup)
# ---------------------------------------------------------------------------
_classifier: Optional[AIDynacardClassifier] = None
_twin_cache: dict = {}


def get_classifier() -> AIDynacardClassifier:
    global _classifier
    if _classifier is None:
        _classifier = AIDynacardClassifier()
    return _classifier


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CSSSimulationRequest(BaseModel):
    steam_volume_tonnes: float = Field(2800.0, ge=500, le=10000)
    injection_rate_tonnes_day: float = Field(140.0, ge=50, le=500)
    injection_pressure_bar: float = Field(65.0, ge=30, le=120)
    steam_quality: float = Field(0.80, ge=0.5, le=1.0)
    soak_days: float = Field(7.0, ge=1, le=30)
    max_production_days: float = Field(180.0, ge=30, le=365)
    economic_cut_off_oil_rate_bpd: float = Field(12.0, ge=1, le=50)
    cycle_number: int = Field(1, ge=1, le=20)


class SRPAnalysisRequest(BaseModel):
    stroke_length_in: float = Field(72.0, ge=36, le=144)
    spm: float = Field(2.2, ge=0.5, le=5.0)
    plunger_d_in: float = Field(1.75, ge=1.0, le=3.0)
    sandface_temp_c: float = Field(105.0, ge=40, le=300)
    well_depth_m: float = Field(1210.0, ge=500, le=3000)


class DynacardClassifyRequest(BaseModel):
    stroke_length_in: float = Field(72.0)
    spm: float = Field(2.2)
    plunger_d_in: float = Field(1.75)
    fault_mode: str = Field("NORMAL")


class VFDControlRequest(BaseModel):
    reservoir_temp_c: float = Field(105.0, ge=40, le=300)
    current_spm: float = Field(2.2, ge=0.5, le=5.0)
    stroke_length_in: float = Field(72.0)
    plunger_d_in: float = Field(1.75)


class StrategyComparisonRequest(BaseModel):
    well_name: str = Field("WX-11 / LOC-P9")
    steam_volume_tonnes: float = Field(2800.0)
    soak_days: float = Field(7.0)
    pay_thickness_m: float = Field(15.0)
    well_depth_m: float = Field(1210.0)
    api_gravity: float = Field(14.5)


class ViscosityCurveRequest(BaseModel):
    temp_min_c: float = Field(40.0)
    temp_max_c: float = Field(300.0)
    n_points: int = Field(50, ge=10, le=200)
    api_gravity: float = Field(14.5)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "Baghewala Digital Twin v0.1"}


# ---------- CSS Thermal Engine ----------

@app.post("/api/css/simulate")
def css_simulate(req: CSSSimulationRequest):
    """Run a full CSS cycle simulation (injection → soak → production)."""
    cfg = CSSCycleConfig(
        cycle_number=req.cycle_number,
        steam_volume_tonnes=req.steam_volume_tonnes,
        injection_rate_tonnes_day=req.injection_rate_tonnes_day,
        injection_pressure_bar=req.injection_pressure_bar,
        steam_quality=req.steam_quality,
        soak_days=req.soak_days,
        max_production_days=req.max_production_days,
        economic_cut_off_oil_rate_bpd=req.economic_cut_off_oil_rate_bpd,
    )
    engine = CSSThermalEngine()
    result = engine.simulate_cycle(cfg)
    return result


# ---------- SRP Rod Floating & Dynacard ----------

@app.post("/api/srp/analyze")
def srp_analyze(req: SRPAnalysisRequest):
    """Analyze rod floating risk, pump efficiency, and Goodman stress."""
    well_cfg = WellboreConfig(
        well_depth_m=req.well_depth_m,
        pump_depth_m=req.well_depth_m - 60.0,
        sandface_temp_c=req.sandface_temp_c,
    )
    engine = SRPWellboreEngine(well_cfg)
    srp = SRPPumpingParameters(
        stroke_length_in=req.stroke_length_in,
        spm=req.spm,
        plunger_d_in=req.plunger_d_in,
    )
    float_result = engine.analyze_rod_floating(srp)
    card = engine.generate_dynamometer_cards(srp, fault_mode="ROD_FLOAT" if float_result["is_floating"] else "NORMAL")
    stress = engine.evaluate_goodman_stress(card["pprl_lbf"], card["mprl_lbf"])
    unsetting = engine.evaluate_pump_unsetting_risk(srp, float_result["peak_downstroke_drag_lbf"])

    return {
        "floating": float_result,
        "dynacard": {
            "surface_position_in": card["surface_position_in"],
            "surface_load_lbf": card["surface_load_lbf"],
            "downhole_position_in": card["downhole_position_in"],
            "downhole_load_lbf": card["downhole_load_lbf"],
            "pprl_lbf": card["pprl_lbf"],
            "mprl_lbf": card["mprl_lbf"],
            "hydraulic_hp": card["hydraulic_hp"],
            "volumetric_efficiency": card["volumetric_efficiency"],
            "predicted_oil_rate_bpd": card["predicted_oil_rate_bpd"],
            "fault_mode": card["fault_mode"],
        },
        "goodman_stress": stress,
        "pump_unsetting": unsetting,
    }


# ---------- AI Dynacard Classifier ----------

@app.post("/api/ai/classify-dynacard")
def classify_dynacard(req: DynacardClassifyRequest):
    """Generate a dynacard in the specified fault mode and classify it with the ML model."""
    engine = SRPWellboreEngine()
    srp = SRPPumpingParameters(
        stroke_length_in=req.stroke_length_in,
        spm=req.spm,
        plunger_d_in=req.plunger_d_in,
    )
    card = engine.generate_dynamometer_cards(srp, fault_mode=req.fault_mode, n_points=80)
    classifier = get_classifier()
    diagnosis = classifier.classify_dynacard(
        card["surface_position_in"], card["surface_load_lbf"]
    )
    return {
        "card": {
            "surface_position_in": card["surface_position_in"],
            "surface_load_lbf": card["surface_load_lbf"],
            "downhole_position_in": card["downhole_position_in"],
            "downhole_load_lbf": card["downhole_load_lbf"],
            "fault_mode_injected": req.fault_mode,
        },
        "classification": diagnosis,
    }


# ---------- All 6 fault mode cards ----------

@app.get("/api/ai/all-fault-cards")
def all_fault_cards(spm: float = 2.2, stroke: float = 72.0, plunger: float = 1.75):
    """Generate dynacards for all 6 fault modes and classify each."""
    engine = SRPWellboreEngine()
    classifier = get_classifier()
    srp = SRPPumpingParameters(stroke_length_in=stroke, spm=spm, plunger_d_in=plunger)
    results = []
    for mode in ["NORMAL", "ROD_FLOAT", "FLUID_POUND", "GAS_INTERFERENCE", "PUMP_UNSETTING", "UNANCHORED_TUBING"]:
        card = engine.generate_dynamometer_cards(srp, fault_mode=mode, n_points=80)
        diag = classifier.classify_dynacard(card["surface_position_in"], card["surface_load_lbf"])
        results.append({
            "injected_mode": mode,
            "surface_position_in": card["surface_position_in"],
            "surface_load_lbf": card["surface_load_lbf"],
            "classification": diag,
        })
    return results


# ---------- Closed-Loop VFD Controller ----------

@app.post("/api/vfd/optimize")
def vfd_optimize(req: VFDControlRequest):
    """Run the closed-loop VFD controller to find optimal SPM & Hz."""
    controller = ClosedLoopVFDController()
    result = controller.calculate_optimal_speed_setpoint(
        reservoir_temp_c=req.reservoir_temp_c,
        current_spm=req.current_spm,
        stroke_length_in=req.stroke_length_in,
        plunger_d_in=req.plunger_d_in,
    )
    return result


# ---------- Full Strategy Comparison (AI vs Legacy) ----------

@app.post("/api/twin/compare")
def twin_compare(req: StrategyComparisonRequest):
    """Run end-to-end digital twin: AI closed-loop vs reactive legacy."""
    twin = IntegratedWellDigitalTwin(
        well_name=req.well_name,
        pay_thickness_m=req.pay_thickness_m,
        well_depth_m=req.well_depth_m,
        api_gravity=req.api_gravity,
    )
    cfg = CSSCycleConfig(
        steam_volume_tonnes=req.steam_volume_tonnes,
        soak_days=req.soak_days,
    )
    result = twin.run_strategy_comparison(cfg)

    # Trim timeseries for reasonable JSON size (keep every 2nd day)
    for key in ("ai_twin", "reactive_legacy"):
        ts = result[key]["timeseries"]
        indices = list(range(0, len(ts["day"]), 2))
        for ts_key in ts:
            ts[ts_key] = [ts[ts_key][i] for i in indices if i < len(ts[ts_key])]

    return result


# ---------- Viscosity Curve ----------

@app.post("/api/pvt/viscosity-curve")
def viscosity_curve(req: ViscosityCurveRequest):
    """Return temperature vs viscosity curve for plotting."""
    props = HeavyOilProperties(api_gravity=req.api_gravity)
    temps = [req.temp_min_c + i * (req.temp_max_c - req.temp_min_c) / (req.n_points - 1) for i in range(req.n_points)]
    viscosities = [heavy_oil_viscosity_cp(t, props) for t in temps]
    return {"temperature_c": temps, "viscosity_cp": viscosities}


# ---------- Wellbore Temperature & Viscosity Profile ----------

@app.get("/api/wellbore/temp-profile")
def wellbore_temp_profile(sandface_temp_c: float = 105.0):
    """Return depth-dependent temperature and viscosity profile."""
    well = WellboreConfig(sandface_temp_c=sandface_temp_c)
    engine = SRPWellboreEngine(well)
    depths, temps, viscs = engine.wellbore_temperature_profile(n_points=25)
    return {
        "depth_m": depths.tolist(),
        "temperature_c": temps.tolist(),
        "viscosity_cp": viscs.tolist(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
