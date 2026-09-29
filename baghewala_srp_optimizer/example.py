
from srp_formulas import SRPInputs, calculate

x = SRPInputs(
    plunger_d_in=1.75,
    stroke_in=72,
    spm=2.0,
    pump_depth_m=1150,
    fluid_density_kg_m3=950,
    rod_d_in=0.875,
    rod_length_m=1100,
    differential_pressure_psi=500,
    actual_rate_bpd=50,
    min_prl_lbf=1000,
    max_prl_lbf=5000,
)

print(calculate(x))
