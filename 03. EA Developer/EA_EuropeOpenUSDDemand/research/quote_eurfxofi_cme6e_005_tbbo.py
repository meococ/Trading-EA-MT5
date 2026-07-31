#!/usr/bin/env python3
"""Free full-history CME 6E TBBO quote for HYP005."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib, importlib.metadata, importlib.util, json, math, re, sys
from pathlib import Path
from typing import Any

HYPOTHESIS_ID="HYP-EURFXOFI-EURUSD-M1-005"
QUOTE_ID="EURFXOFI005-TBBO-FREE-QUOTE-001"
BASE="03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL=BASE+"HYP-EURFXOFI-EURUSD-M1-005_TBBO_SOURCE_QUOTE_PLAN.md"
TOOL_REL=BASE+"quote_eurfxofi_cme6e_005_tbbo.py"
TEST_REL=BASE+"tests/test_quote_eurfxofi_cme6e_005_tbbo.py"
PARENT_REL=BASE+"quote_eurfxofi_cme6e_004_mbp1.py"
REGISTRY_REL="04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RUNTIME_REL="02. AlphaFactory/runtime/python-databento/Scripts/python.exe"
LEDGER_REL="02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001/signal_dates.jsonl"
FOUNDATION_REL="03. EA Developer/EA_SweepCascadeContinuation/research/acquire_cme6e_mbp10_windows.py"
OUTPUT_REL=f"02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/{HYPOTHESIS_ID}/{QUOTE_ID}/metadata_quote_receipt.json"
PLAN_SHA256="44DC9FB5A112D35A871FFBAF3AF3A53DB4E3D17324DD558EB4F24C4640307E32"
PARENT_SHA256="052E6B6036DFF74297AA201A6A2233FFECD167083CF5B7511718537DBF190F18"
LEDGER_SHA256="EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
SCHEMA="tbbo"; OWNER_CEILING_USD=2.25; EXPECTED_DATES=1359; SDK_VERSION="0.54.0"
REVIEWED_REGISTRY_ROW_SHA256: str|None="BD12D0F6F4F3BF4763B0B39D8977F88843729D19FDB888F7836C61CCFB16F878"
_SENTINEL_RE=re.compile(rb'^REVIEWED_REGISTRY_ROW_SHA256: str\|None=(?:None|"[A-F0-9]{64}")\r?$')

class QuoteError(RuntimeError): pass

def sha256_file(p:Path)->str:
 d=hashlib.sha256()
 with p.open('rb') as h:
  for c in iter(lambda:h.read(1<<20),b''): d.update(c)
 return d.hexdigest().upper()
def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest().upper()
def canonical_json(v:object)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def normalized_tool_base_sha256(payload:bytes)->str:
 lines=payload.splitlines(keepends=True); matches=[i for i,x in enumerate(lines) if _SENTINEL_RE.match(x.rstrip(b'\n'))]
 if len(matches)!=1: raise QuoteError('invalid registry sentinel')
 i=matches[0]; nl=b'\n' if lines[i].endswith(b'\n') else b''; lines[i]=b'REVIEWED_REGISTRY_ROW_SHA256: str|None=None'+nl
 return sha256_bytes(b''.join(lines))
def workspace_from_source()->Path:return Path(__file__).resolve().parents[3]
def require_d(p:Path,label:str)->Path:
 r=p.resolve()
 if r.drive.upper()!='D:':raise QuoteError(f'{label} must stay on D:')
 return r
def load_parent(p:Path)->Any:
 if sha256_file(p)!=PARENT_SHA256:raise QuoteError('parent tool hash mismatch')
 s=importlib.util.spec_from_file_location('eurfxofi005_parent',p)
 if s is None or s.loader is None:raise QuoteError('cannot load parent')
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def validate_authority(w:Path)->dict[str,str]:
 if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256)!=64:raise QuoteError('sentinel not armed')
 if sha256_file(w/PLAN_REL)!=PLAN_SHA256 or sha256_file(w/LEDGER_REL)!=LEDGER_SHA256:raise QuoteError('plan or ledger drift')
 payload=(w/TOOL_REL).read_bytes();base=normalized_tool_base_sha256(payload);test=sha256_file(w/TEST_REL);found=[]
 for raw in (w/REGISTRY_REL).read_bytes().splitlines():
  row=json.loads(raw)
  if row.get('hypothesis_id')==HYPOTHESIS_ID:found.append((row,raw+b'\n'))
 if not found:raise QuoteError('hypothesis absent')
 row,line=found[-1];v=row.get('validation',{});rowsha=sha256_bytes(line)
 exp={'source_quote_plan_sha256':PLAN_SHA256,'signal_date_ledger_sha256':LEDGER_SHA256,'reviewed_quote_tool_base_sha256':base,'reviewed_quote_test_sha256':test,'parent_quote_tool_sha256':PARENT_SHA256}
 if rowsha!=REVIEWED_REGISTRY_ROW_SHA256 or row.get('state')!='probe' or v.get('source_quote_authorized') is not True:raise QuoteError('registry authority mismatch')
 for k,val in exp.items():
  if v.get(k)!=val:raise QuoteError(f'registry binding mismatch: {k}')
 for k in ('paid_acquisition_authorized','economics_authorized','outcome_prices_authorized','mql5_authorized','model0_authorized','paper_trading_authorized','live_trading_authorized'):
  if v.get(k) is not False:raise QuoteError(f'forbidden authority open: {k}')
 return {'row':rowsha,'base':base,'file':sha256_bytes(payload),'test':test}
def execute(w:Path,workers:int)->Path:
 w=require_d(w,'workspace')
 if Path(sys.executable).resolve()!=require_d(w/RUNTIME_REL,'runtime') or importlib.metadata.version('databento')!=SDK_VERSION:raise QuoteError('runtime mismatch')
 a=validate_authority(w);p=load_parent(w/PARENT_REL);pp=p.load_parent(w/p.PARENT_TOOL_REL);rows=pp.load_dates(w/LEDGER_REL);windows=[pp.build_window(r) for r in rows]
 if len(windows)!=EXPECTED_DATES:raise QuoteError('window mismatch')
 foundation=pp.load_foundation(w/FOUNDATION_REL);key=foundation.load_api_key();old=p.SCHEMA;p.SCHEMA=SCHEMA
 try:q=p.quote_all(pp,lambda:foundation.make_client(key),windows,workers)
 finally:p.SCHEMA=old
 usd=float(sum(float(x['estimated_usd']) for x in q));size=int(sum(int(x['billable_bytes']) for x in q))
 if len(q)!=EXPECTED_DATES or not math.isfinite(usd):raise QuoteError('aggregate quote invalid')
 data={'schema_version':'eurfxofi005_tbbo_free_quote.v1','hypothesis_id':HYPOTHESIS_ID,'quote_id':QUOTE_ID,'created_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'status':'FREE_TBBO_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST','dataset':pp.DATASET,'schema':SCHEMA,'symbol':pp.SYMBOL,'request_window':'[14:14:45,14:15:00)_Europe/Berlin_DST','request_count':len(q),'owner_ceiling_usd':OWNER_CEILING_USD,'estimated_total_usd':usd,'estimated_total_billable_bytes':size,'within_owner_ceiling':usd<=OWNER_CEILING_USD,'quotes':q,'bindings':a,'api_method_counters':{'metadata.get_cost':sum(int(x['metadata_attempt']) for x in q),'metadata.get_billable_size':len(q),'timeseries.get_range':0,'batch.submit_job':0},'paid_request_made':False,'price_data_read':False,'outcome_fields_used':[]}
 out=require_d(w/OUTPUT_REL,'output')
 if out.exists() or out.parent.exists():raise QuoteError('exclusive output exists')
 out.parent.mkdir(parents=True,exist_ok=False);out.write_bytes(canonical_json(data)+b'\n');return out
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=Path,default=workspace_from_source());ap.add_argument('--workers',type=int,default=16);x=ap.parse_args()
 try:
  out=execute(x.workspace.resolve(),x.workers);r=json.loads(out.read_text());print(f"EURFXOFI005_TBBO_FREE_QUOTE_OK requests={r['request_count']} estimated_usd={r['estimated_total_usd']:.12f} bytes={r['estimated_total_billable_bytes']} within_ceiling={str(r['within_owner_ceiling']).lower()} paid=0");print(f'RECEIPT {out}');return 0
 except QuoteError as e:print(f'EURFXOFI005_TBBO_FREE_QUOTE_BLOCKED reason={e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
