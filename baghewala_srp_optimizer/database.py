"""Production-Grade Database Manager and Data Layer for Baghewala SRP & CSS Digital Twin."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

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
