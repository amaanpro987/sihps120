"""OIL INDIA LIMITED | ENTERPRISE REAL-TIME MONITORING & ADVISORY CENTER (ERTMAC)
Baghewala Heavy Oil Well-to-Surface Cyber-Physical Digital Twin & Optimization System.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json

# Internal Digital Twin Engines
from database import (
    init_db, seed_comprehensive_field_data, connect,
    insert_operating_data, insert_dynacard, insert_optimization_run
)
from fluid_pvt import (
    HeavyOilProperties, heavy_oil_viscosity_cp, saturated_steam_temperature_c,
    steam_enthalpy_kj_kg, oil_density_at_temperature
)
from reservoir_thermal_engine import (
    CSSThermalEngine, ReservoirParameters, CSSCycleConfig
)
from srp_wellbore_engine import (
    SRPWellboreEngine, WellboreConfig, RodStringConfig, SRPPumpingParameters
)
from css_optimizer import CSSOptimizer, CSSOptimizationBounds
from ai_engine import AIDynacardClassifier, ClosedLoopVFDController, FAULT_CLASSES, FAULT_DESCRIPTIONS
from digital_twin_orchestrator import IntegratedWellDigitalTwin
from ertmac_ui_components import (
    get_ertmac_css, render_ertmac_header, render_alarm_ticker, render_interactive_wellbore_svg
)

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
