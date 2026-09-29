import pandas as pd,json,uuid
from datetime import datetime
from .db import con,log
from .css import optimize_css
from .optimizer import optimize_srp
from .config import SAFETY
def table_df(name):
 c=con(); d=pd.read_sql_query('SELECT * FROM '+name,c); c.close(); return d
def status(well_id='BGW-04'):
 names=['production','srp_operations','css_cycles','failures','unsetting']; o={'well_id':well_id,'records':{n:len(table_df(n)) for n in names}}
 for n,key in [('srp_operations','latest_srp'),('production','latest_production')]:
  d=table_df(n)
  if len(d):o[key]=d.iloc[-1].to_dict()
 return o
def recommend(well_id,base):
 sb,_=optimize_srp(base,SAFETY); cb=optimize_css(base.get('css',{})); rec={'rec_id':str(uuid.uuid4()),'ts':datetime.now().isoformat(),'well_id':well_id,'css_action':json.dumps(cb),'stroke_in':sb['stroke_in'],'spm':sb['spm'],'vfd_hz':sb['vfd_hz'],'expected_oil_bpd':sb['predicted_oil_bpd'],'expected_sor':cb['estimated_sor'],'risk_score':sb['risk'],'confidence':max(.2,1-sb['risk']),'status':'ADVISORY','reason':'Physics-constrained scenario recommendation; requires field validation.'}; c=con(); c.execute('INSERT INTO recommendations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',tuple(rec.values())); c.commit(); c.close(); log('CREATE_RECOMMENDATION','recommendations',rec); return rec
