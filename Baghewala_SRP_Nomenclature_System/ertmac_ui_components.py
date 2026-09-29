"""ERTMAC (Enterprise Real Time Monitoring & Advisory Center) UI Component Library.

Provides:
- Industrial SCADA Dark Theme CSS Styles
- Live Alarm & Event Annunciator Banner
- High-Density SCADA Telemetry Cards
- Interactive SVG Animated Wellbore & Reservoir Thermal Schematic
- Dynamic Pumping Unit Kinematics Display
- Industrial Gauges & Status LEDs
"""

import math
from typing import Dict, List, Any


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
