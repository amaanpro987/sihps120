# Baghewala AI Well-to-Surface Digital Twin: Physics-Informed Closed-Loop System

### Integrated CSS–SRP Optimization, Predictive Intelligence, and Edge Autonomy

## 1. Executive Summary

The proposed solution is a **Physics-Informed Closed-Loop Digital Twin for Baghewala Field**, designed to continuously connect reservoir behavior, thermal conditions, heavy-oil viscosity, Cyclic Steam Stimulation (CSS), artificial lift, production performance, and equipment health.

The core system addresses a major operational challenge in Baghewala: **CSS and artificial-lift operations are traditionally optimized separately**, even though they strongly influence each other.

The proposed Digital Twin creates a continuous feedback loop:

**Reservoir → Thermal State → Viscosity → Wellbore → SRP → Prediction → Optimization → Shadow Mode Audit → Action**

### Implementation Status: Prototype vs. Pilot

Rather than claiming this massive architecture is "fully implemented" in a hackathon, we present an honest implementation matrix mapping what runs in the React/FastAPI prototype today vs. what requires real Baghewala data during the pilot phase:

| Algorithm / Feature | Status in Current Prototype | Pilot / Real-Data Requirement |
| :--- | :--- | :--- |
| **Marx-Langenheim (Thermal)** | Implemented (Simulated Baseline) | Needs field CSS history to calibrate residual |
| **Walther ASTM D341 (Viscosity)** | Implemented | Needs lab crude samples for API constant tuning |
| **1D Wave Equation (Gibbs)** | Implemented (Synthetic Cards) | Needs surface load/position telemetry |
| **Goodman Fatigue Evaluator** | Implemented | Needs accurate rod string metallurgy tables |
| **Rod-Float Classifier / OOD** | Implemented (Trained on Synthetics) | Needs re-training on historical anomaly cards |
| **NSGA-II Optimizer** | Implemented | Needs management constraints on energy costs |
| **1D Wellbore Discretization** | Simulated | Needs exact tubing/casing geometry |
| **Steam Generator & CSOR Model** | Simulated | Needs real-time fuel and steam line loss data |
| **Integrated Cutoff Optimizer** | Implemented | Needs accurate economic thresholds |
| **Time-to-Failure Survival Model** | Planned | Needs historical failure timestamps |
| **Hierarchical Conformal Forecaster** | Implemented | Needs cold-start multi-well training dataset |
| **Shadow Mode Audit Ledger** | Implemented | Ready for deployment |
| **Edge Guardrail & Buffer** | Planned | Hardware dependent deployment |
| **Conversational AI Gateway** | Implemented | Ready for deployment |
| **Geospatial & Automated Reports** | Implemented (Extensions) | Needs accurate GIS well coordinates |

> **Validation Note:** The prototype currently demonstrates the *simulated benefit under model assumptions*. Actual performance (precision, recall, ROI) will be validated against real data during the Phase 1 pilot.

---

# 2. Problem Statement

Baghewala Field produces heavy crude oil with approximately **17–19° API gravity** from the Jodhpur Sandstone reservoir.

The field presents challenging production conditions including:

* High crude-oil viscosity
* High asphaltene content
* Low reservoir pressure
* Low reservoir temperature
* Poor oil mobility under primary recovery
* Dependence on artificial lift
* Dependence on thermal recovery techniques such as CSS

As steam is injected during CSS, the near-wellbore region heats up and oil viscosity decreases, improving mobility.

However, after the CSS cycle and during production, the reservoir gradually cools.

This can result in:

**Temperature ↓ → Viscosity ↑ → Oil Mobility ↓ → Pump Loading ↑ → Efficiency ↓ → Production ↓**

The changing thermal condition also affects artificial-lift behavior and may contribute to:

* Rod floating
* Rod failures
* Pump unsetting
* Increased energy consumption
* Reduced pump efficiency
* Production decline

The fundamental challenge is therefore not simply optimizing CSS or SRP individually.

### The real challenge is:

> **How can CSS, reservoir thermal behavior, fluid properties, artificial lift, production and equipment reliability be optimized together as one connected system?**

---

# 3. Proposed Solution

The proposed system is a **Well-to-Surface AI Digital Twin**.

It combines:

### Data Layer

* Production history
* CSS records
* Steam injection parameters
* SRP/VFD data
* Pressure and temperature data
* Reservoir data
* Well-completion information
* Fluid properties
* Rod failure history
* Pump-unsetting history
* Equipment events

### Intelligence Layer

* Data-quality engine
* Feature engineering
* Predictive ML models
* Anomaly detection
* Risk prediction
* Digital Twin
* Scenario simulator
* Optimization engine
* Explainable AI

### Decision Layer

* Well recommendations
* CSS recommendations
* SRP operating windows
* Equipment-risk alerts
* Production forecasts
* Automated engineering reports
* Multi-well spatial intelligence

---

# 4. Core Innovation

The primary innovation is the **integration of CSS and artificial lift into a single predictive optimization framework**.

Instead of asking:

> “What is the best steam cycle?”

or:

> “What should the SRP operating condition be?”

the system asks:

> **“Given the current and predicted thermal, reservoir, fluid, production and equipment state, what combination of CSS and artificial-lift conditions provides the best feasible operating window?”**

### The Core Physics Integration (Genuine Engineering Math)

To prove this isn't a black-box AI, the Digital Twin uses explicit mathematical coupling.

**1. Thermal-Viscosity Coupling (Walther ASTM D341):**
As the reservoir cools, viscosity skyrockets. We model this explicitly:
`log(log(ν + 0.7)) = A - B * log(T)`
*(where ν is kinematic viscosity, T is absolute temperature, and A/B are tuned via ML residuals to Baghewala lab data).*

**2. Mechanical-Viscous Coupling (Safe-SPM & Wave Equation):**
High viscosity fluid creates immense drag on the rod string during the downstroke. If the pump moves faster than the rod can fall through the thick crude, the rod floats, compressing the string and causing a violent impact. 
The system computes the maximum Safe-SPM ceiling by evaluating the screening velocity criterion:
`V_polished_rod_downstroke ≈ (π * S * N) / 60  ≤  V_rod_fall ∝ 1/μ`
*(where S is stroke length, N is SPM, and μ is dynamic viscosity). This is then refined using the 1D damped wave equation.*

**3. Fatigue Limit (API RP 11L Goodman):**
Using the simulated downhole loads, we compute the allowable stress range:
`S_A = ((T / 4) + (0.5625 * S_min)) / SF`
*(where SF is the Service Factor). The optimizer then ensures the simulated `S_max` never exceeds `S_A`.*

This creates a true, physics-grounded closed-loop intelligence system.

# 5. Overall System Architecture

```text
                    OIL COMPANY DATA
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Production          CSS Data          SRP/VFD Data
        │                  │                  │
        ├──────────── Reservoir Data ────────┤
        │                  │                  │
        ├──── Fluid / PVT / Pressure Data ───┤
        │                  │                  │
        └──────── Equipment Failure Data ────┘
                           │
                           ▼
                DATA INGESTION ENGINE
                           │
                           ▼
              DATA QUALITY & VALIDATION
                           │
                           ▼
                 UNIT NORMALIZATION
                           │
                           ▼
                TEMPORAL ALIGNMENT
                           │
                           ▼
                 FEATURE ENGINEERING
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
       PHYSICS CORE              ML MODEL LAYER
             │                           │
             └─────────────┬─────────────┘
                           ▼
                  PREDICTION ENGINE
                           │
                           ▼
                  SCENARIO ENGINE
                           │
                           ▼
                 OPTIMIZATION ENGINE
                           │
                           ▼
               RECOMMENDATION ENGINE
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       WELL DASHBOARD   REPORTING     GEO-SPATIAL
                           │             INTELLIGENCE
                           │              │
                           └──────┬───────┘
                                  ▼
                         ENGINEERING USER
```

---

# 5.1 The Algorithm Registry & Assistant Gateway

To realize this architecture in an industrial context and earn operator trust, the system exposes a **catalog of 23 distinct engineering algorithms, validated against reference cases and field history**. 

Rather than functioning as a black-box AI, the Digital Twin acts as an orchestrator. The Conversational AI Gateway routes natural-language queries to this registered tool catalog. The execution ledger logs every call, input, output, and latency, ensuring answers are physically grounded and auditable.

This suite integrates the deepest petroleum-engineering physics with rigorous ML hygiene:

### A. Core Petroleum Physics & Simulation
1. **Inquire Well Telemetry:** Queries real-time SCADA state (or historian/edge buffer) to establish the current operating point.
2. **Walther / ASTM D341 Viscosity Solver:** Calculates the heavy crude dual-log kinematic viscosity equation based on the current thermal state, calibrated to Baghewala data with an ML residual.
3. **Marx-Langenheim Heat Model (CSS Adapted):** Computes conductive heat loss and thermal radius calculation to generate a **"Thermal-Viscosity Cycle Forecast"** curve. It models the complete near-wellbore temperature decline through the entire production period, carrying residual heat from previous cycles.
4. **1D Wellbore Discretization:** Solves the 5-layer vertical hydrostatic and thermal gradient from the reservoir sandface to the wellhead.
5. **1D Damped Wave Dyno Solver (Gibbs Method):** Converts the measured surface card into a downhole pump card using the acoustic velocity of the steel rod string and viscous damping. *(Crucial Coupling: Viscosity from Algorithm #2 drives the damping coefficient in this equation, which is calibrated per-well using historical cards, directly bridging thermal physics to mechanical loads).*
6. **API RP 11L Goodman Evaluator:** Calculates allowable stress ratios and cumulative fatigue damage for the sucker rod string.
7. **Safe-SPM Ceiling Solver:** Ensures the polished rod's downstroke velocity must not exceed the velocity at which the rod string can fall through the fluid (roughly ∝ 1/viscosity), refined by the wave equation to prevent rod float.
8. **Steam Generator & Surface Model:** Calculates fuel consumption, generator efficiency, and surface steam line losses to the wellhead.

### B. Machine Learning, Optimization & Uncertainty
9. **NSGA-II Multi-Objective Optimizer:** Generates a Pareto frontier balancing conflicting goals: maximizing oil production, minimizing rod fatigue, minimizing CSOR, and minimizing energy per barrel.
10. **Integrated Cutoff & Next-Cycle Optimizer:** Evaluates marginal net value rate to calculate a recommended cutoff window with uncertainty for ending production and re-steaming.
11. **Hierarchical Conformal Forecaster:** Uses a hierarchical model (borrowing from neighbours with similar geology and completion) to produce the predictive distribution, then calibrates with group conformal prediction on pooled residuals to generate 30-day interval predictions.
12. **Thermal-State Decline Model:** Cycle-specific reservoir-response model for oil rate.
13. **Isolation Forest / OOD Detector:** Detects out-of-distribution mechanical anomalies by analyzing card-derived features (min load ratio, downstroke drop, spike size), not raw telemetry.
14. **Time-to-Failure Survival Model:** Uses Weibull or Cox survival analysis (handling censored data) to predict failure horizons based on accumulated fatigue and impact events.
15. **SHAP Attribution Waterfall:** Provides the "Why?" engine, explaining the exact factors (e.g., thermal cooling vs. pump loading) contributing to failure or production decline.

### C. Safety, Flow Assurance, Auditing & Control
16. **CSOR Energy Auditor:** Reconciles steam heat, fuel, and lift energy (kWh/bbl) on one basis.
17. **Flow-Assurance & Wear Diagnostics:** Flags asphaltene deposition risks, emulsion effects, and pump unsetting risks based on load signatures and thermal state.
18. **Pump Efficiency Engine:** Computes volumetric efficiency by combining wave-equation pump fillage and telemetry.
19. **Transmit RTU VFD Setpoint:** Validates the proposed operating window against safety envelopes before formatting it for RTU transmission.
20. **Scenario Lab & Constraint Checker:** Simulates parameter variations (e.g., steam volume, rod metallurgy upgrades) side-by-side with current operations, evaluating them against hard regulatory and equipment limits.
21. **Shadow Mode Audit Ledger:** Logs AI recommendations against actual operator actions to audit speed variance and build trust before supervised control is granted.
22. **Historical Backtester:** Replays past rod failures and floating events to report detection lead time, precision, and false-alert rates.
23. **Data-Quality Engine:** Tags incoming telemetry into Valid, Warning, Critical, Missing, or Suspected classes.

> **Implementation Note:** This exact tool paradigm is how our Conversational AI Assistant operates. When an engineer asks a question, the agent visibly executes these tools (e.g., *Running Marx-Langenheim Heat Model...*) before returning a physics-grounded response.

---

# 6. Data Management System

The platform should support the following structure:

```text
data/
│
├── raw/
│   ├── production/
│   ├── css/
│   ├── srp/
│   ├── reservoir/
│   ├── well_completion/
│   ├── fluid_properties/
│   ├── pressure_temperature/
│   └── failures/
│
├── incoming/
├── validated/
├── processed/
├── features/
├── training/
└── sample/
```

### Confidentiality principle

Actual oil-company data should remain separated from demonstration data.

Synthetic data should be provided so the complete system can be demonstrated before confidential field data becomes available.

Synthetic data must always be explicitly labelled **SYNTHETIC**.

---

# 7. Required Data & Sensor Fallbacks

To ensure honest deployment, the system expects specific telemetry. If primary sensors are missing, the Digital Twin uses fallback estimations while automatically lowering the data-confidence score.

| Required Signal | Purpose | If Missing (Fallback Action) |
| :--- | :--- | :--- |
| **Polished-rod load & position (Surface Card time series)** | 1D Wave Dyno solver (#5) | Estimate from motor current / VFD electrical data (Electrical card estimation) |
| **VFD frequency, motor kW / current** | Control and Energy auditor | **Required** (Cannot optimize without it) |
| **Wellhead P/T, Casing pressure** | Thermal state and wellbore model | Use historical estimates and flag lower confidence |
| **Fluid level / Fillage** | Pump efficiency computation | Infer computationally from downhole dynacard |
| **Steam rate, quality, enthalpy, pressure, temp** | CSS Thermal Model (#3) | **Required** for CSS physical modeling |
| **Fuel use (Steam Generator)** | CSOR Energy Auditor (#15) | Estimate from steam enthalpy tables |

## Static Well Information
* Rod string design (taper, grades, diameters)
* Pump size and depth
* Tubing and casing geometry
* Completion configuration

## Reservoir & Fluid Data
* Overburden thermal properties (Heat capacity, conductivity)
* Formation thickness & pressure history
* Lab viscosity-temperature curves (for D341 calibration)
* API gravity & Asphaltene content

## Failure Data

* Rod failure
* Pump failure
* Pump unsetting
* Rod floating
* Failure date
* Failure type
* Failure duration
* Repair information

---

# 8. Data Quality Engine

Before data reaches the ML models, the platform performs automated validation.

It checks:

* Missing values
* Duplicate records
* Invalid timestamps
* Unit inconsistencies
* Sensor gaps
* Impossible physical values
* Outliers
* CSS-cycle inconsistencies
* Production inconsistencies
* Equipment-data anomalies

The system must **never silently delete problematic data**.

Instead, every issue should be classified as:

* Valid
* Warning
* Critical
* Missing
* Suspected anomaly

This allows engineers to understand the quality of the information being used.

---

# 9. Feature Engineering

The system generates meaningful engineering features rather than relying only on raw measurements.

### Thermal Features

* Temperature decline rate
* Temperature recovery rate
* Time since steam injection
* Cumulative thermal exposure
* Temperature deviation from expected state

### Production Features

* Oil-rate decline
* Water-cut trend
* Production response after CSS
* Production acceleration/deceleration
* Cycle-normalized production

### CSS Features

* Steam volume
* Injection duration
* Soak duration
* Cycle number
* Steam-to-oil ratio
* Previous-cycle response

### SRP Features

* SPM
* Stroke length
* VFD frequency
* Load
* Torque
* Power
* Pump efficiency

### Interaction Features

Examples:

```text
Temperature × Viscosity
Temperature × SPM
Viscosity × Pump Load
CSS Cycle × Production Response
Temperature × Pump Efficiency
SPM × Rod-Floating Risk
```

These interactions are particularly important because the system is intended to model the **connected well system**, not isolated variables.

---

# 10. Machine Learning Layer

The platform uses different models for different engineering problems.

## 10.1 Temperature Forecasting

Predict:

* 6 hours to 7 days (for operational alerts and short-term trends)
* Multi-week and full cycle-length (for complete thermal/viscosity production periods, configuring the 180-day baseline to the actual well performance)

Potential models:

* Persistence baseline
* Linear models
* Random Forest
* XGBoost
* LightGBM
* HistGradientBoosting
* Suitable time-series models

---

# 11. Viscosity Prediction

Viscosity is a critical variable because heavy-oil mobility changes strongly with temperature.

The preferred architecture is:

**Physics/PVT relationship (Algorithm #2 with ML residual)**

rather than treating viscosity as a completely unconstrained black-box prediction. For cold-start wells with few cycles, the Hierarchical Forecaster (#11) borrows trends from nearby wells. Coverage is reported by group, and cold-start wells are explicitly flagged with lower confidence bounds.

Output:

```text
Estimated viscosity
+
Prediction interval
+
Confidence
+
Important influencing variables
```

> **Implementation Note:** The physics-informed viscosity model is implemented using the `heavy_oil_viscosity_cp` function in `fluid_pvt.py`. It anchors the model using the Walther (ASTM D341) equation, ensuring predictions remain thermodynamically sound outside normal training boundaries. This is demonstrated in the prototype at the `/pvt-model` route, showing the temperature-viscosity curve explicitly.

---

# 12. Oil Production Prediction (Algorithm #12)

The production model estimates future:

* Oil rate
* Production trend
* CSS response
* Production decline

The system should compare ML predictions against simple baselines to demonstrate whether the model provides genuine predictive value.

---

# 13. Rod-Floating Detection

Rather than relying purely on ML, the system employs a physics-first diagnostic stack:

1. **Dyno-Card Physics (#5, #7):** The Gibbs damped wave-equation converts surface telemetry to a downhole card.
2. **Anomaly Detection (#13):** An Isolation Forest runs specifically on card-derived features (min load ratio, downstroke drop, spike size), rather than raw telemetry, to flag OOD conditions.
3. **Supervised Classification:** If labels exist, a classifier predicts specific fault types.
4. **Explainability (#15):** SHAP factors explain the precise cause.

Output:

```text
Rod Floating Risk: Low / Medium / High
```

with confidence bounds and a SHAP attribution list. Label as model evidence.

> **Validation Note (Crucial):** Currently, the RandomForest classifier is trained on *synthetic* dynacards generated by the wave-equation synthesizer. Since the simulator and classifier use the same underlying math, high accuracy is expected by construction (circular validation). During the pilot, the classifier will be validated on *real* historical cards or published anomalous cards with independent noise to prove true field efficacy.

> **Implementation Note:** The Dynacard Fault Classification engine is implemented in the prototype at the `/ai-diagnostics` route. It uses a 6-class RandomForest classifier (`AIDynacardClassifier` in `ai_engine.py`) trained on synthetic dynamometer cards generated by the 1D damped wave-equation synthesizer. This allows real-time classification of Normal, Rod Float, Fluid Pound, Gas Interference, Pump Unsetting, and Unanchored Tubing conditions with confidence probabilities.

---

# 14. Equipment Failure Prediction (Algorithm #14)

Where sufficient historical failure data exists, the system uses a **Time-to-Failure Survival Model (Cox Proportional Hazards or Weibull)** to predict risks such as:

* Rod failure
* Pump failure
* Pump unsetting

**Survival Model Details:**
* **Covariates:** Accumulated fatigue damage (from Goodman), thermal cycles, OOD spike frequency, and historical run life.
* **Censoring:** Wells still running without failure are right-censored, ensuring all run-life data is utilized.
* **Low-Event Handling:** For wells with very few failures, the model pools baseline hazard rates across the field.

The model should output:

```text
Failure Risk
Prediction Horizon
Confidence
Important Factors
```

It should **not claim a failure will definitely occur**.

---

# 15. Pump Efficiency Model (Algorithm #18)

The system estimates pump performance using:

* Production
* Load
* SPM
* Stroke
* VFD
* Temperature
* Fluid properties
* Historical pump behavior

This helps identify operating conditions where increased artificial-lift effort does not produce proportional production benefit.

---

# 16. Digital Twin

The Digital Twin maintains a continuously updated representation of the well.

### WellState

```text
WellState
│
├── Reservoir
│   ├── Pressure
│   ├── Temperature
│   └── Reservoir condition
│
├── Fluid (← #2 Viscosity Solver)
│   ├── API gravity
│   ├── Viscosity
│   └── PVT properties
│
├── Thermal (← #3 Marx-Langenheim, #4 Wellbore)
│   ├── Current temperature
│   └── Cooling trend
│
├── CSS (← #8 Steam Model, #16 CSOR Auditor)
│   ├── Current cycle
│   ├── Steam parameters
│   └── Historical response
│
├── SRP / Equipment (← #5 Wave Dyno, #6 Goodman, #7 Safe-SPM)
│   ├── SPM / Stroke / VFD
│   ├── Rod-floating risk
│   ├── Failure risk
│   └── Pump efficiency (← #18)
│
└── Production
    ├── Oil rate
    ├── Water rate
    └── Production trend
```

> **Implementation Note:** The Digital Twin is implemented in `digital_twin_orchestrator.py` which runs a daily timestep simulation. The results are visualized in the prototype's `/strategy-compare` route, showing a comparison of AI Closed-Loop vs Reactive Operation. *Note: This comparison currently shows the simulated benefit under model assumptions, not empirical evidence. Empirical evidence will be gathered during the pilot.*

---

# 17. Scenario Simulator

Engineers can modify operating parameters and immediately see predicted consequences.

For example:

```text
Steam Volume
      ↓
Temperature
      ↓
Viscosity
      ↓
Oil Mobility
      ↓
Production
      ↓
Pump Loading
      ↓
Energy
      ↓
Equipment Risk
```

Possible scenario inputs:

* Steam volume
* Injection pressure
* Injection duration
* Soak time
* Production cutoff
* SPM
* Stroke
* VFD frequency

The simulator compares:

### Current Operation

versus

### Proposed Scenario

and displays predicted changes in:

* Temperature
* Viscosity
* Oil production
* SOR
* Energy
* Pump efficiency
* Rod-floating risk
* Failure risk

> **Implementation Note:** The CSS Scenario Simulator is implemented in the prototype at the `/css-simulator` route. It calls the FastAPI endpoint `/api/css/simulate` to run the Marx-Langenheim and Boberg-Lantz models, allowing evaluators to interactively adjust steam volume, soak days, and injection pressure and see the resulting oil production and SOR changes side-by-side.

---

# 18. Multi-Objective Optimization Engine

The optimizer should simultaneously consider multiple objectives.

The optimizer explicitly targets:

```text
Decision Variables:
    30-day SPM schedule
    30-day VFD frequency schedule
    Stroke length
    Steam volume & Soak time
    Cutoff day for production

Objectives (Minimize):
    -oil, fatigue damage, CSOR, energy per barrel
    Rod fatigue damage
    Cumulative Steam-Oil Ratio (CSOR)
    Energy per barrel

Constraints (Hard Guardrails):
    Stress ratio ≤ 1 (with safety margin)
    No rod float (Safe-SPM ceiling enforced)
    Pump fillage above minimum
    Motor and VFD physical limits
```

To ensure execution speed, the optimizer uses a fast surrogate (ML emulator) of the physics core during NSGA-II generation, verifying the final candidates with the full physics equations. Random seeds are fixed to ensure runs are reproducible. 

The optimizer picks the final recommendation from the Pareto front using a defined "knee point" or preference-weighted selection.

The system should produce **operating windows**, not unexplained magic numbers. Engineers approve the operating envelope and can override at any time; in supervised mode, the system acts only inside the approved window.

Example:

```text
Recommended SPM Range
Recommended VFD Range
Expected Production Range
Expected Energy Range
Equipment Risk
Confidence
```

Final operational decisions remain with authorized engineers.

---

# 19. Explainable AI

Every major prediction should answer:

### What is the prediction?

### Why is the model predicting it?

### How confident is it?

### Which factors contributed most?

Example:

```text
Oil production is predicted to decline.

Main contributing factors:
• Increasing thermal cooling
• Increasing estimated viscosity
• Reduced recent CSS response
• Increasing pump loading

Confidence: 82%
```

Feature importance should be presented as **model evidence**, not automatically interpreted as proof of physical causation.

---

# 20. Out-of-Distribution Detection

The system must identify when current conditions differ significantly from the training data.

For example:

> “Current well conditions are outside the model's historical operating range.”

This prevents the system from presenting uncertain predictions with false confidence.

---

# 21. Well Health Intelligence

Instead of relying on one unexplained overall score, the platform presents separate dimensions:

```text
Reservoir Condition
Thermal Condition
Production Condition
SRP Condition
Equipment Reliability
Data Confidence
```

Each dimension can have its own evidence and explanation.

---

# 22. ⭐ Additional Feature Layer: Automated Well Intelligence Report

This is an extension of the **main Digital Twin**, not a separate system.

For every selected well, the system automatically generates an engineering report.

### Report flow

```text
Select Well
     ↓
Retrieve Well Data
     ↓
Digital Twin
     ↓
Prediction Models
     ↓
Risk Detection
     ↓
CSS Analysis
     ↓
SRP Analysis
     ↓
Problem Detection
     ↓
Optimization
     ↓
Automated Report
```

---

# 23. Automated Problem Register

The report automatically identifies process-related problems.

Problems may belong to:

### Reservoir

* Pressure decline
* Thermal depletion
* Poor reservoir response

### Fluid

* Increasing viscosity
* Poor mobility

### CSS

* Weak cycle response
* Declining cycle performance
* High SOR

### Wellbore

* Abnormal operating behavior
* Production deterioration

### SRP

* Poor pump efficiency
* High loading
* Abnormal operating conditions

### Equipment

* Rod-floating risk
* Failure risk
* Pump-unsetting risk

### Production

* Production decline
* Unexpected production response

Each problem should contain:

```text
Problem
Severity
Evidence
Possible contributing factors
Operational impact
Future risk
Recommended action
```

The system should distinguish between:

**Observed problem**

**Model-detected condition**

**Engineering interpretation**

**Recommendation**

This is important for engineering credibility.

---

# 24. Root-Cause Relationship View

The report can visualize relationships such as:

```text
Reservoir Cooling
       ↓
Temperature Decrease
       ↓
Viscosity Increase
       ↓
Oil Mobility Decrease
       ↓
Pump Loading Increase
       ↓
Rod-Floating Risk Increase
       ↓
Production Efficiency Decrease
```

However, the system should label these as **relationships or contributing factors** unless causal evidence is available.

---

# 25. Well Timeline

Every well receives a chronological operational timeline.

Example:

```text
CSS Cycle 4
     ↓
Steam Injection
     ↓
Soak
     ↓
Production Increase
     ↓
Thermal Cooling
     ↓
Production Decline
     ↓
SRP Adjustment
     ↓
Equipment Event
```

This allows engineers to quickly understand **what happened and when**.

---

# 26. “What Changed?” Analysis

The platform should automatically compare the current state with a previous baseline.

For example:

```text
Temperature       ↓ 8%
Viscosity         ↑ 14%
Oil Rate          ↓ 11%
Pump Load         ↑ 7%
Energy            ↑ 10%
```

The exact values would come from the actual well data.

This makes the system useful even when an engineer does not want to manually inspect dozens of charts.

---

# 27. Geospatial Well Navigator — Major USP

The second major extension is a **geospatial multi-well intelligence system**.

Instead of analyzing only one well, engineers can navigate wells spatially.

The platform provides a full-screen field map showing wells geographically.

The engineer can select:

```text
Well A
+
Radius
+
Unit
```

For example:

```text
500 m
1 km
2 km
5 km
10 km
```

Internally, the platform normalizes distances to meters and uses proper geographic-distance calculations.

> **Implementation Note:** The Geospatial Map is implemented in the prototype at the `/well-map` route. It features a canvas-rendered interactive map of Baghewala field using Haversine distance formulas to filter nearby wells dynamically based on user-selected radius (e.g. 2km), directly addressing this major USP.

---

# 28. Radius-Based Nearby Well Intelligence

After selecting a radius, the platform displays nearby wells.

Example:

| Well  | Distance | Oil Rate | Temp | Viscosity | SOR | SPM | Failure Risk |
| ----- | -------: | -------: | ---: | --------: | --: | --: | ------------ |
| W-101 |   0.4 km |        — |    — |         — |   — |   — | —            |
| W-108 |   0.8 km |        — |    — |         — |   — |   — | —            |
| W-115 |   1.3 km |        — |    — |         — |   — |   — | —            |

The actual values come from the oil-company dataset.

---

# 29. Nearby Well Comparison

The system can compare the selected well with wells inside the chosen radius.

Parameters include:

* Production
* Temperature
* Pressure
* API gravity
* Viscosity
* CSS response
* SOR
* SPM
* VFD
* Failure frequency
* Rod-floating events
* Equipment condition

This allows engineers to identify how the selected well behaves relative to its spatial neighborhood.

---

# 30. Spatial Pattern Detection

The platform can detect patterns such as:

> Several nearby wells are experiencing similar production declines.

or:

> Multiple wells within the selected radius show similar thermal behavior.

or:

> Equipment-risk events appear clustered spatially.

The platform should describe these as **spatial patterns**, rather than automatically claiming a common physical cause.

Engineering interpretation can then investigate whether the pattern is related to:

* Reservoir characteristics
* Thermal behavior
* Operating practices
* Completion configuration
* CSS strategy
* Other field-level conditions

---

# 31. Radius-Based Area Intelligence Report

The selected well and surrounding radius can generate an **Area Intelligence Report**.

It contains:

### Selected Well

Current Digital Twin state.

### Nearby Wells

All wells inside the selected radius.

### Production Comparison

Selected well vs surrounding wells.

### Thermal Comparison

Temperature and cooling behavior.

### CSS Comparison

Cycle performance and response.

### SRP Comparison

Artificial-lift behavior.

### Equipment Comparison

Failure and rod-floating history.

### Spatial Patterns

Common trends identified within the radius.

### Well-Specific Recommendations

Recommendations remain specific to each well.

---

# 32. Report Types

The system can generate four report levels.

## 1. Quick Well Report

For daily operational review.

## 2. Engineering Well Report

Detailed technical analysis.

## 3. Management Report

High-level performance and risk summary.

## 4. Area Intelligence Report

Selected well + surrounding radius.

Reports can be exported as:

* PDF
* Excel appendix where useful

---

# 33. AI Engineering Assistant

A conversational interface can sit on top of the Digital Twin.

Engineers could ask:

> “Why did production decline?”

> “What changed after the last CSS cycle?”

> “Compare this well with wells within 2 km.”

> “What are the major current problems?”

> “Generate the engineering report.”

> “Which nearby wells have similar thermal behavior?”

> “Show the predicted equipment risks.”

The assistant must answer using:

* Actual well data
* Digital Twin state
* Model outputs
* Validated calculations

It should not invent engineering facts.

---

# 34. Premium Dashboard

The frontend should contain:

### Executive Dashboard

Field-level overview.

### Well Digital Twin

Detailed individual well state.

### Production Forecast

Current and predicted production.

### Reservoir/Thermal State

Temperature, pressure and viscosity behavior.

### CSS Optimization

Cycle analysis and scenarios.

### SRP Optimization

Pump and artificial-lift intelligence.

### Failure & Risk Monitoring

Equipment risks.

### Scenario Simulator

“What-if” analysis.

### Well Map

Geospatial field navigation.

### Area Intelligence

Radius-based analysis.

### Well Comparison

Multi-well comparison.

### Automated Reports

Generate engineering reports.

### Data Management

Upload and validate data.

### Model Performance

Monitor ML models.

### Model Registry

Track deployed models.

### System Health

Monitor the platform itself.

---

# 35. Backend Architecture

Suggested backend modules:

```text
src/
│
├── data/
├── features/
│
├── models/
│   ├── temperature/
│   ├── viscosity/
│   ├── production/
│   ├── rod_floating/
│   ├── failure/
│   └── pump_efficiency/
│
├── digital_twin/
│
├── optimization/
│
├── inference/
│
├── reporting/
│   ├── well_report.py
│   ├── area_report.py
│   ├── problem_detector.py
│   ├── report_templates.py
│   ├── report_charts.py
│   └── pdf_generator.py
│
├── geospatial/
│   ├── distance.py
│   ├── radius_search.py
│   ├── spatial_analysis.py
│   ├── well_locations.py
│   └── clustering.py
│
└── intelligence/
    ├── problem_engine.py
    ├── well_health.py
    ├── timeline.py
    └── change_detection.py
```

---

# 36. Frontend Architecture

```text
frontend/
│
├── pages/
│   ├── Dashboard.tsx
│   ├── WellTwin.tsx
│   ├── Production.tsx
│   ├── CSSOptimization.tsx
│   ├── SRPOptimization.tsx
│   ├── FailureRisk.tsx
│   ├── ScenarioSimulator.tsx
│   ├── WellMap.tsx
│   ├── WellReport.tsx
│   ├── AreaIntelligence.tsx
│   ├── WellComparison.tsx
│   └── ModelPerformance.tsx
│
└── components/
    ├── RadiusSelector
    ├── WellMap
    ├── NearbyWells
    ├── ProblemRegister
    ├── WellTimeline
    ├── WellHealth
    ├── EngineeringReport
    └── SpatialComparison
```

---

# 37. Database Extensions

The core database can be extended with:

```text
well_locations
well_events
problem_register
well_reports
area_reports
spatial_analysis
report_snapshots
```

This allows the platform to maintain historical versions of generated intelligence.

---

# 38. Model Training Strategy

The ML pipeline should follow:

```text
Raw Data
   ↓
Validation
   ↓
Cleaning
   ↓
Feature Engineering
   ↓
Chronological & Spatial Split
   ↓
Training
   ↓
Validation
   ↓
Testing
   ↓
Evaluation
   ↓
Model Registry
   ↓
Deployment
```

Time-aware and spatial splitting is essential.

Randomly mixing future and past observations can cause **data leakage**. To validate robustly, the strategy uses:
1. **Chronological Splitting:** Ensuring future data is never used to predict the past.
2. **Leave-One-Well-Out:** Ensuring models generalize to unseen wells.
3. **Cycle-Grouped Validation:** Ensuring performance holds across multi-cycle degradation.
4. **Baselines:** Comparing predictions against current manual practice, simple persistence, and generic decline curves.
5. **Coverage Checks:** Verifying the empirical coverage of conformal intervals per-well.

---

# 39. Model Evaluation

Depending on the task:

### Regression

* MAE
* RMSE
* R²
* SMAPE
* MAPE where appropriate

### Classification

* Precision
* Recall
* F1
* ROC-AUC where appropriate
* Confusion matrix
* Calibration

### Operational Evaluation

Also measure:

* Prediction stability
* False-alert frequency
* Lead time
* Recommendation feasibility
* Constraint violations

---

# 40. Model Registry

Every deployed model should record:

```text
Model Version
Dataset Version
Feature Version
Training Period
Validation Period
Test Period
Metrics
Hyperparameters
Model Artifact
Deployment Status
```

This makes the system auditable.

---

# 41. Security

The platform should implement:

* Environment-based secrets
* Authentication
* Role-based access
* Encrypted sensitive information
* Separation of confidential and demonstration data
* No confidential field data committed to Git
* Audit logging

---

# 41.5 The Edge Layer

To ensure safety and reliability even if cloud connectivity is lost, the system deploys a lightweight Edge node at the well site or field RTU.

**What runs locally:**
* **Local Safe-SPM Guardrail:** A hard-coded check comparing real-time downstroke velocity against the physics-derived limit to prevent immediate rod floating.
* **Store-and-Forward Buffer:** Caches up to 72 hours of high-frequency dynacard and SCADA telemetry if the connection drops *(assuming a 10Hz dynacard sampling rate × local flash storage capacity)*.
* **Re-sync Behavior:** Upon reconnection, the edge node flushes the buffer to the cloud, allowing the Digital Twin to backfill the missing history and update the thermal decline state.

---

# 42. Tiered Autonomy & Safety Philosophy

This system is an **engineering decision-support platform** that earns control step-by-step through a tiered autonomy framework.

It operates under the following hierarchy:

1. **Shadow Mode (Baseline):** The system recommends, logs the recommendation, and changes nothing. It compares "what we would have done" against operator action.
2. **Advisory Mode:** The engineer explicitly approves each recommendation via the gateway.
3. **Supervised Control:** Setpoints are written directly to the RTU/VFD within hard guardrails (safe envelope, rate-of-change limits, automatic revert on error) and allow immediate engineer override.

Promotion criteria to the next tier is strictly based on shadow-mode metrics (e.g., float events successfully predicted, low false-alert rate, recommendation feasibility).

---

# 43. Key Performance Indicators

The platform can monitor:

### Production

* Oil-rate improvement
* Production decline reduction
* CSS response

### Thermal

* Temperature prediction accuracy
* Cooling trend detection

### Artificial Lift

* Pump efficiency
* Energy per unit oil

### Value Case & Return on Investment (ROI)

The value of this Digital Twin is measured through a simple ROI model: **(Workover Cost Avoided + Steam Fuel Saved + Extra Oil Value) - System Cost**.

We will validate the following hypotheses during the pilot phase:

| Key Performance Indicator | Baseline (Illustrative placeholder) | Pilot Target (Hypothesis) |
| :--- | :--- | :--- |
| Rod failures / well-year | 1.5 failures/yr | Reduce by ≥ 30% |
| Pump unsetting events | 3 events/yr | Reduce by ≥ 40% |
| Float events detected before failure | 0 (run to failure) | ≥ 48 hours lead time |
| Cumulative SOR | 3.2 m³/m³ | Reduce by ≥ 10% |
| Energy per barrel (Fuel + Electricity) | 140 kWh/bbl | Reduce by ≥ 15% |
| Workover cost | ₹12 Lakh / event | Avoid ≥ 1 workover / well-year |
| Engineer time to diagnose a well | 2 hours | < 15 minutes |

*(Note: Baseline figures are illustrative placeholders. Exact ROI calculation requires Baghewala-specific input for oil price, steam generation cost per ton, and rig mobilization costs).*
---

# 44. Expected Benefits

The intended benefits, subject to validation using actual field data, include:

* Better integration of CSS and SRP decisions
* Earlier identification of declining well performance
* Improved understanding of thermal behavior
* More informed artificial-lift decisions
* Earlier identification of equipment risks
* Reduced dependence on manual data analysis
* Faster engineering reporting
* Easier comparison of nearby wells
* Better identification of spatial patterns
* More transparent AI-assisted recommendations

These should be validated through field trials rather than presented as guaranteed improvements.

---

# 45. Implementation Roadmap & Pilot Plan

## Pilot Plan
We will select 2-3 pilot wells for initial deployment:
1. One well with known historical rod floating or failure events (to prove backtesting lead time).
2. One mature well with extensive CSS data.
3. One "cold-start" well with few cycles (to demonstrate uncertainty bands tightening via neighbour-informed priors).

## Phase 1 — Data Foundation & Synthetic Generation
* Data schemas, ingestion, and validation
* Data-quality engine
* Synthetic dataset generation (for safe demoing before field data)

## Phase 2 — Physics Core (Highest Value)
* Walther / ASTM D341 Viscosity model
* Marx-Langenheim thermal model & Wellbore model
* 1D Wave equation dyno solver
* API 11L Goodman stress model
* Safe-SPM Ceiling solver

## Phase 3 — ML Data Layer & Digital Twin
* ML residuals for thermal/viscosity models
* Conformal forecasts and hierarchical priors
* Isolation Forest (OOD) & SHAP explainability
* Digital Twin State mapping

## Phase 4 — Decisions & Optimization
* NSGA-II Multi-objective optimization
* Cutoff and next-cycle logic
* Scenario lab and constraint checker

## Phase 5 — Well-to-Surface Energy Model
* Steam generator fuel consumption
* CSOR and VFD kW auditing
* Flow-assurance flags (Asphaltene)

## Phase 6 — Trust, Control & Edge Deployment
* Shadow mode audit ledger
* Conversational AI gateway and Algorithm registry
* **Edge Layer Deployment:** Local safe-SPM checks, store-and-forward data buffers for offline rod protection.

## Phase 7 — Tiered Control on Pilot Wells
* Shadow mode validation against baseline
* Promotion to Advisory mode
* Promotion to Supervised control with VFD guardrails

## Phase 8 — Extensions (Post-Pilot)
* Automated Engineering PDF Reports
* Geospatial Radius-Based Navigator (post-pilot extension)
---

# 46. Final End-to-End Workflow

```text
              OIL FIELD DATA
                    │
                    ▼
             DATA INGESTION
                    │
                    ▼
          DATA QUALITY ENGINE
                    │
                    ▼
           FEATURE ENGINEERING
                    │
                    ▼
              ML MODELS
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
   PREDICTIONS             DIGITAL TWIN
        │                       │
        └───────────┬───────────┘
                    ▼
             SCENARIO ENGINE
                    │
                    ▼
            OPTIMIZATION ENGINE
                    │
                    ▼
         RECOMMENDATION ENGINE
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
    WELL AI      WELL REPORT   WELL MAP
       │            │            │
       │            │            ▼
       │            │       RADIUS SEARCH
       │            │            │
       │            │            ▼
       │            │      NEARBY WELLS
       │            │            │
       │            │            ▼
       │            │   SPATIAL INTELLIGENCE
       │            │            │
       └────────────┴────────────┘
                    │
                    ▼
             ENGINEER REVIEW
                    │
                    ▼
              FIELD ACTION
                    │
                    ▼
              NEW DATA
                    │
                    └──────────────► DIGITAL TWIN
```

# 47. Overall Solution Vision

The final platform is not merely an ML prediction dashboard.

It is a **Well-to-Surface Engineering Intelligence Platform**.

Its core capability is the **AI Digital Twin for integrated CSS + artificial-lift optimization**.

The additional intelligence layer makes it substantially more useful at field scale:

> **One well → understand the well.**
> **One radius → understand the surrounding wells.**
> **One report → understand what is happening, why it may be happening, what could happen next, and what should be investigated.**

The complete concept can therefore be summarized as:

### **“An AI-driven Well-to-Surface Digital Twin that continuously connects reservoir thermal behavior, heavy-oil viscosity, CSS, SRP behavior, production, energy consumption and equipment health to predict future well behavior, simulate operating scenarios, recommend safer and more efficient operating windows, automatically generate engineering intelligence reports, and provide radius-based spatial intelligence across surrounding wells.”**

# sih_ps120
