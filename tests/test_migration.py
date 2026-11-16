import pytest
from core import fixture,repair,validate_contract,interpret
from fastapi.testclient import TestClient
from app import app

@pytest.mark.parametrize('index',[1,5,17,100,257])
def test_rename_preserves_outputs_and_literals(index):
    f=fixture(index);r=repair(f['source'],f['old'],f['new'])
    assert validate_contract(f['source'],f['cases'])['passed']==0
    assert validate_contract(r['source'],f['cases'])['passed']==5
    assert len(r['changes'])==1

@pytest.mark.parametrize('kind',['type_change','removed'])
def test_abstains_on_semantic_changes(kind):
    f=fixture(1,kind);assert repair(f['source'],f['old'],f['new'])['status']=='abstained'

@pytest.mark.parametrize('source',[
 'import os\ndef parse(x): return x',
 'def parse(x): return __import__("os").getcwd()',
 'def parse(x): return x.__class__',
 'def parse(x): return [v for v in x]',
 'def parse(x): return {**x}',
 '@print\ndef parse(x): return x'])
def test_no_code_execution(source):
    with pytest.raises(ValueError):interpret(source,{})

def test_api_and_bad_input():
    c=TestClient(app)
    assert c.post('/demo',json={'fixture_id':7}).json()['validated']
    assert c.post('/demo',json={'kind':'bad'}).status_code==400
