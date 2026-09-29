import math
def css_response(steam_t,pressure_psi,temp_c,soak_hr,cutoff_days,base_temp_c=47,viscosity_cp=15000):
 heat=min(1,.25*(steam_t/300)**.7+.25*(pressure_psi/2400)**.4+.15*(temp_c/340)**.6); soak=min(1,soak_hr/72); cool=min(.35,max(0,(cutoff_days-3)*.025)); heating=base_temp_c+150*heat*(.55+.45*soak); viscosity=max(100,viscosity_cp*math.exp(-.018*(heating-base_temp_c))); recovery=max(1,steam_t*(.20+.55*heat+.15*soak)*(1-cool)); sor=steam_t/recovery; energy=steam_t*.72+pressure_psi/1000*8
 return {'heating_index':heat,'estimated_reservoir_temp_c':heating,'estimated_viscosity_cp':viscosity,'estimated_recovery_bbl':recovery,'estimated_sor':sor,'estimated_energy_mwh':energy}
def optimize_css(current,limits=None):
 L=limits or {'steam_min':100,'steam_max':400,'pressure_min':1200,'pressure_max':2400,'soak_min':12,'soak_max':96,'cutoff_min':1,'cutoff_max':14}; best=None
 for steam in range(L['steam_min'],L['steam_max']+1,25):
  for p in range(L['pressure_min'],L['pressure_max']+1,200):
   for soak in range(L['soak_min'],L['soak_max']+1,12):
    for cut in range(L['cutoff_min'],L['cutoff_max']+1):
     r=css_response(steam,p,current.get('temp_c',340),soak,cut,current.get('base_temp_c',47),current.get('viscosity_cp',15000)); score=r['estimated_recovery_bbl']-8*r['estimated_sor']-.6*r['estimated_energy_mwh']
     if best is None or score>best['score']: best={**r,'steam_t':steam,'pressure_psi':p,'soak_hr':soak,'production_cutoff_days':cut,'score':score}
 return best
