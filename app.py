from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from core import fixture,repair,validate_contract
from ui import page

app=FastAPI(title='ContractForge',version='0.1.0')
class Demo(BaseModel):
    fixture_id:int=Field(default=42,ge=0,le=1000)
    kind:str='rename'
class Migration(BaseModel):
    old:dict
    new:dict
    source:str=Field(max_length=10000)
    cases:list[dict]=Field(max_length=50)

@app.get('/',response_class=HTMLResponse)
def home():return page('ContractForge','Compare OpenAPI response contracts, generate bounded Python AST migrations, and inspect contract results. Client code is interpreted, never executed.',{'fixture_id':42,'kind':'rename'})
@app.post('/repair')
def migrate(m:Migration):
    try:
        result=repair(m.source,m.old,m.new)
        result['before']=validate_contract(m.source,m.cases)
        result['after']=validate_contract(result['source'],m.cases)
        result['validated']=result['after']['total']>0 and result['after']['passed']==result['after']['total']
        return result
    except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,str(e))
@app.post('/demo')
def demo(c:Demo):
    if c.kind not in ['rename','type_change','removed']:raise HTTPException(400,'Unknown fixture')
    f=fixture(c.fixture_id,c.kind)
    return migrate(Migration(**{k:f[k] for k in ['old','new','source','cases']}))
