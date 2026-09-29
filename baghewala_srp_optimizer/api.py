from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from core.db import init,seed
from core.pipeline import status,recommend
init();seed();app=FastAPI(title='Baghewala Well-to-Surface Digital Twin API',version='1.0')
class Scenario(BaseModel):
 plunger_in:float=Field(gt=0);pump_depth_m:float=Field(gt=0);density:float=Field(gt=0);rod_d_in:float=Field(gt=0);rod_len_m:float=Field(gt=0);dp_psi:float=Field(ge=0);oil_rate:float=Field(ge=0);min_prl:float=Field(ge=0);max_prl:float=Field(ge=0);current_spm:float=Field(gt=0);current_hz:float=Field(ge=0);baseline_fillage:float=Field(gt=0,le=1)
@app.get('/health')
def health():return {'status':'ok'}
@app.get('/wells/{well_id}/status')
def well_status(well_id:str):return status(well_id)
@app.post('/wells/{well_id}/recommend')
def rec(well_id:str,s:Scenario):return recommend(well_id,s.model_dump())
