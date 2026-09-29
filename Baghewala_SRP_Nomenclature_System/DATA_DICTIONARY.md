# Data Dictionary & Database Schema

## Table: `wells`
- `id` (INTEGER PRIMARY KEY): Unique well identifier.
- `well_name` (TEXT UNIQUE): Official well designation (e.g. `WX-11 / LOC-P9`, `WX-07 / LOC-P3`).
- `location` (TEXT): Surface drill site location.
- `target_depth_m` (REAL): Target total depth in meters MBDF (e.g. 1210.0 m).
- `formation` (TEXT): Target formation name (`Jodhpur Sandstone`).
- `pay_thickness_m` (REAL): Net oil pay column thickness (e.g. 15.0 m).
- `tubing_od_in` / `tubing_id_in` (REAL): Production tubing dimensions (2.875" / 2.441").
- `casing_od_in` (REAL): Production casing diameter (7.0").
- `api_gravity` (REAL): Crude oil API gravity (e.g. 14.5 °API).
- `initial_pressure_psi` / `reservoir_temp_c` (REAL): Virgin reservoir conditions.

## Table: `srp_config`
- `plunger_d_in` (REAL): Plunger bore diameter in inches (e.g. 1.75").
- `pump_depth_m` (REAL): Pump seating depth (e.g. 1150.0 m).
- `stroke_in` (REAL): Pumping unit stroke length in inches.
- `spm` (REAL): Pumping speed in strokes per minute.
- `vfd_hz` (REAL): Variable Frequency Drive output frequency (Hz).
- `top_rod_d_in` / `bottom_rod_d_in` (REAL): Tapered rod string diameters (7/8", 3/4").
- `sinker_bar_d_in` / `sinker_bar_length_m` (REAL): Heavy sinker bar specifications (1.5" x 100 m).
- `anchor_capacity_lbf` (REAL): Tubing anchor hold-down force rating.

## Table: `css_cycles`
- `cycle_number` (INTEGER): CSS cycle index (1, 2, 3...).
- `steam_volume_tonnes` (REAL): Injected cold water equivalent steam volume.
- `injection_pressure_bar` (REAL): Sandface steam injection pressure.
- `steam_quality` (REAL): Dryness fraction at sandface.
- `soak_days` (REAL): Shut-in soak duration.
- `cumulative_oil_bbl` (REAL): Total heavy oil recovered during cycle.
- `cumulative_sor` (REAL): Cumulative Steam-Oil Ratio (bbl steam / bbl oil).

## Table: `operating_data`
- `ts` (TEXT): ISO 8601 Timestamp.
- `stroke_in`, `spm`, `vfd_hz`, `vfd_current_a`, `motor_power_kw`: Surface drive telemetry.
- `pprl_lbf`, `mprl_lbf`: Peak and minimum polished rod loads.
- `sandface_temp_c`, `wellhead_temp_c`: Thermal monitoring.
- `oil_rate_bpd`, `water_cut`, `pump_efficiency`: Production metrics.
- `rod_float_index`, `impact_index`: Mechanical risk indices.
- `goodman_stress_percent`: Modified Goodman loading percentage.
- `specific_energy_kwh_bbl`: Power efficiency metric.
- `ai_fault_diagnosis`: Neural anomaly classification label.

## Table: `dynacards`
- `positions_json`, `loads_json`: High-resolution dynamometer curves.
- `ai_classified_mode`: Diagnosed regime (Normal, Rod Float, Fluid Pound, Gas Lock, Unsetting, Tubing Stretch).
- `ai_confidence_pct`: Probabilistic confidence score.
