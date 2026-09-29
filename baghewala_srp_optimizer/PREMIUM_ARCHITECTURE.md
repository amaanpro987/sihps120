# Premium Production Architecture

## Data-to-decision pipeline
SCADA/historian + CSS records + well/reservoir + fluid properties + failure history + dynamometer cards -> validation -> digital-twin state -> forecasts -> constrained optimization -> advisory -> operator approval -> controlled change -> response monitoring -> model update.

## Decision variables
CSS: steam volume, injection pressure, steam temperature, soak time, production cut-off.
SRP: stroke length, SPM, VFD frequency.

## Predicted states
Reservoir heating/cooling, viscosity response, production, SOR, energy/barrel, pump fillage/efficiency, rod floating risk, impact loading risk, rod-failure risk and pump-unsetting risk.

## Production ML
Use separate time-series models for oil rate, SOR, failure risk, unsetting risk, fillage and fluid-property response. Final validation should be chronological/time-based. Register model version, training period, features, metrics and approval state.

## Optimization
Use hard constraints for equipment/operating envelopes and a multi-objective function covering production/recovery, SOR, energy/barrel, reliability and risk. Move to constrained MPC only after sufficient field data and control-system approvals exist.

## Safety
No direct actuator write-back is implemented. Every recommendation is ADVISORY and audited. HAZOP, cybersecurity, alarm management, control-room approval and operating procedures must precede closed-loop control.

## Source hierarchy
FIELD_MEASURED > OIL_OFFICIAL > VENDOR > API > ENGINEERING_ASSUMPTION. API defines standards/methodologies; Baghewala actuals must come from OIL field documents/historian/measurements.
