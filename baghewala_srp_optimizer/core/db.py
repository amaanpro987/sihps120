import sqlite3,json
from pathlib import Path
DB_PATH=Path(__file__).resolve().parents[1]/'digital_twin.db'
def con():
 c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c
def init():
 c=con(); c.executescript('''
CREATE TABLE IF NOT EXISTS wells(well_id TEXT PRIMARY KEY,well_name TEXT,formation TEXT,target_depth_m REAL,pay_thickness_m REAL,tubing_od_in REAL,casing_in REAL,pump_depth_m REAL,status TEXT);
CREATE TABLE IF NOT EXISTS css_cycles(cycle_id TEXT PRIMARY KEY,well_id TEXT,start_ts TEXT,end_ts TEXT,steam_volume_t REAL,injection_pressure_psi REAL,injection_temp_c REAL,soak_hours REAL,production_cutoff_days REAL,oil_recovery_bbl REAL,steam_oil_ratio REAL,energy_mwh REAL,status TEXT);
CREATE TABLE IF NOT EXISTS production(ts TEXT,well_id TEXT,oil_rate_bpd REAL,liquid_rate_bpd REAL,water_cut REAL,wellhead_pressure_psi REAL,pump_intake_pressure_psi REAL,fluid_level_m REAL,fluid_temp_c REAL);
CREATE TABLE IF NOT EXISTS srp_operations(ts TEXT,well_id TEXT,stroke_in REAL,spm REAL,vfd_hz REAL,motor_current_a REAL,torque_lbf_ft REAL,min_prl_lbf REAL,max_prl_lbf REAL,pump_fillage REAL,oil_rate_bpd REAL,liquid_rate_bpd REAL);
CREATE TABLE IF NOT EXISTS failures(event_id TEXT PRIMARY KEY,well_id TEXT,ts TEXT,failure_type TEXT,severity TEXT,downtime_hr REAL,root_cause TEXT,confirmed INTEGER);
CREATE TABLE IF NOT EXISTS unsetting(event_id TEXT PRIMARY KEY,well_id TEXT,ts TEXT,indicator TEXT,severity TEXT,downtime_hr REAL,confirmed INTEGER);
CREATE TABLE IF NOT EXISTS rod_cards(ts TEXT,well_id TEXT,position_deg REAL,load_lbf REAL,source TEXT);
CREATE TABLE IF NOT EXISTS fluid_properties(ts TEXT,well_id TEXT,temperature_c REAL,viscosity_cp REAL,density_kg_m3 REAL,api_gravity REAL,pressure_psi REAL);
CREATE TABLE IF NOT EXISTS model_runs(run_id TEXT PRIMARY KEY,ts TEXT,model_name TEXT,model_version TEXT,training_rows INTEGER,metrics_json TEXT,features_json TEXT);
CREATE TABLE IF NOT EXISTS recommendations(rec_id TEXT PRIMARY KEY,ts TEXT,well_id TEXT,css_action TEXT,stroke_in REAL,spm REAL,vfd_hz REAL,expected_oil_bpd REAL,expected_sor REAL,risk_score REAL,confidence REAL,status TEXT,reason TEXT);
CREATE TABLE IF NOT EXISTS audit_log(ts TEXT,actor TEXT,action TEXT,entity TEXT,details TEXT);
'''); c.commit(); c.close()
def seed():
 c=con(); c.execute('INSERT OR IGNORE INTO wells VALUES(?,?,?,?,?,?,?,?,?)',('BGW-04','Baghewala #4','Jodhpur Sandstone',1151.9,15,2.875,7,1017,'ACTIVE')); c.commit(); c.close()
def log(action,entity,details,actor='system'):
 c=con(); c.execute("INSERT INTO audit_log VALUES(datetime('now'),?,?,?,?)",(actor,action,entity,json.dumps(details))); c.commit(); c.close()
