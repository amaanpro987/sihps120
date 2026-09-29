import pandas as pd
from .db import con,log
TABLES={'production':'production','srp_operations':'srp_operations','css_cycles':'css_cycles','failures':'failures','unsetting':'unsetting','fluid_properties':'fluid_properties','rod_cards':'rod_cards'}
def ingest_csv(path,table,well_id='BGW-04'):
 if table not in TABLES: raise ValueError('Unsupported table')
 df=pd.read_csv(path); df['well_id']=well_id
 c=con(); df.to_sql(table,c,if_exists='append',index=False); c.commit(); c.close(); log('INGEST_CSV',table,{'path':str(path),'rows':len(df),'well_id':well_id}); return len(df)
def quality(table):
 c=con(); d=pd.read_sql_query('select * from '+table,c); c.close()
 if d.empty:return {'rows':0,'null_pct':{},'duplicate_rows':0}
 return {'rows':len(d),'null_pct':(d.isna().mean()*100).round(2).to_dict(),'duplicate_rows':int(d.duplicated().sum())}
