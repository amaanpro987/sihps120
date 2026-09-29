import pandas as pd
from sklearn.ensemble import RandomForestRegressor,RandomForestClassifier
from sklearn.metrics import mean_absolute_error,r2_score,roc_auc_score
from sklearn.model_selection import train_test_split
from .config import MODEL
FEATURES=['steam_volume_t','injection_pressure_psi','injection_temp_c','soak_hours','production_cutoff_days','stroke_in','spm','vfd_hz','motor_current_a','torque_lbf_ft','min_prl_lbf','max_prl_lbf','pump_fillage','fluid_temp_c','viscosity_cp','density_kg_m3','fluid_level_m']
def _prep(df):
 x=df.copy()
 for f in FEATURES:
  if f not in x:x[f]=0
 return x[FEATURES].apply(pd.to_numeric,errors='coerce').fillna(0)
def train_production_model(df,target='oil_rate_bpd'):
 if len(df)<MODEL.min_training_rows or target not in df or df[target].nunique()<2:return None
 x=_prep(df); y=pd.to_numeric(df[target]); xt,xv,yt,yv=train_test_split(x,y,test_size=.2,random_state=MODEL.random_state); m=RandomForestRegressor(n_estimators=300,min_samples_leaf=3,random_state=42,n_jobs=-1).fit(xt,yt); p=m.predict(xv); return m,{'mae_bpd':mean_absolute_error(yv,p),'r2':r2_score(yv,p),'rows':len(df)}
def train_failure_model(df):
 if len(df)<MODEL.min_training_rows or 'failure_label' not in df or df.failure_label.nunique()<2:return None
 x=_prep(df); y=df.failure_label.astype(int); xt,xv,yt,yv=train_test_split(x,y,test_size=.2,random_state=42,stratify=y); m=RandomForestClassifier(n_estimators=300,min_samples_leaf=2,class_weight='balanced',random_state=42,n_jobs=-1).fit(xt,yt); p=m.predict_proba(xv)[:,1]; return m,{'roc_auc':roc_auc_score(yv,p),'rows':len(df)}
