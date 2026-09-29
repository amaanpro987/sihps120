import math
def pump_displacement_bpd(plunger_in,stroke_in,spm): return .1166*plunger_in**2*stroke_in*spm
def hydrostatic_psi(depth_m,density): return depth_m*density*9.80665/1000/6894.757
def rod_weight_lbf(length_m,diameter_in,density_kg_m3=7850):
 d=diameter_in*.0254; return length_m*math.pi*d*d/4*density_kg_m3*9.80665/4.44822
def rod_float_index(min_prl,max_prl,rod_weight,fluid_load):
 return max(0,min(1,(fluid_load-(max_prl-rod_weight))/max(max_prl-min_prl,1)))
def impact_index(min_prl,max_prl,stroke,spm): return min(1,max(max_prl-min_prl,0)/max(stroke*spm*20,1)*.08)
def srp_metrics(plunger_in,stroke_in,spm,pump_depth_m,density,rod_d_in,rod_len_m,dp_psi,actual_oil,min_prl,max_prl):
 disp=pump_displacement_bpd(plunger_in,stroke_in,spm); rw=rod_weight_lbf(rod_len_m,rod_d_in); fluid=math.pi*(plunger_in*.0254)**2/4*dp_psi*6894.757/4.44822
 return {'theoretical_displacement_bpd':disp,'rod_weight_lbf':rw,'fluid_load_lbf':fluid,'rod_float_index':rod_float_index(min_prl,max_prl,rw,fluid),'impact_index':impact_index(min_prl,max_prl,stroke_in,spm),'pump_efficiency':max(0,min(1,actual_oil/disp if disp else 0))}
