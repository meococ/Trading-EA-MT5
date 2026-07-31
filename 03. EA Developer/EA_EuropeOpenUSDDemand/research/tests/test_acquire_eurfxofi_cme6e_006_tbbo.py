import importlib.util,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'acquire_eurfxofi_cme6e_006_tbbo.py';s=importlib.util.spec_from_file_location('a6',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_frozen_contract():assert m.SCHEMA=='tbbo' and m.EXPECTED==1359 and m.OWNER_CEILING_USD==2.25
def test_filename_is_request_identity():assert m.filename({'request_id':'ECBFX-2020-01-02'})=='ECBFX-2020-01-02.dbn.zst'
def test_call_args_are_exact():
 x={'start':'a','end':'b'};assert m.call_args(x)=={'dataset':'GLBX.MDP3','schema':'tbbo','symbols':['6E.v.0'],'stype_in':'continuous','start':'a','end':'b'}
