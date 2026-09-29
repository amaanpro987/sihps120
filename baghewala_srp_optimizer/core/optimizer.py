from .physics import srp_metrics
def optimize_srp(base,safety):
 best=None; rows=[]
 for stroke in [48,61,74,86]:
  for spm in [.5,1,1.5,2,2.5,3]:
   hz=base.get('current_hz',0)*spm/max(base.get('current_spm',1),.1) if base.get('current_hz',0)>0 else spm*10
   if spm>safety.max_spm or hz>safety.max_vfd_hz: continue
   m=srp_metrics(base['plunger_in'],stroke,spm,base['pump_depth_m'],base['density'],base['rod_d_in'],base['rod_len_m'],base['dp_psi'],base.get('oil_rate',0),base.get('min_prl',0),base.get('max_prl',0)); risk=min(1,.55*m['rod_float_index']+.45*m['impact_index']); predicted=m['theoretical_displacement_bpd']*base.get('baseline_fillage',.65); score=predicted-100*risk-.15*abs(spm-base.get('current_spm',spm)); row={'stroke_in':stroke,'spm':spm,'vfd_hz':hz,**m,'predicted_oil_bpd':predicted,'risk':risk,'score':score}; rows.append(row)
   if best is None or row['score']>best['score']: best=row
 return best,rows
