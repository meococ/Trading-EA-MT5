import importlib.util,sys
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'quote_eurfxofi_cme6e_005_tbbo.py'
s=importlib.util.spec_from_file_location('q5',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def test_frozen_contract():
 assert m.SCHEMA=='tbbo' and m.EXPECTED_DATES==1359 and m.OWNER_CEILING_USD==2.25
