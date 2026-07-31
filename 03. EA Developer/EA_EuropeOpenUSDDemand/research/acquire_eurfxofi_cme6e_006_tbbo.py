#!/usr/bin/env python3
"""Live-requote and serially acquire the HYP006 CME 6E TBBO corpus."""

from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, importlib.metadata, importlib.util, json, math, os, re, sys, threading
from pathlib import Path
from typing import Any

HYPOTHESIS_ID="HYP-EURFXOFI-EURUSD-M1-006"; ATTEMPT_ID="EURFXOFI006-TBBO-SOURCE-001"
BASE="03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL=BASE+"HYP-EURFXOFI-EURUSD-M1-006_TBBO_ACQUISITION_PLAN.md"; TOOL_REL=BASE+"acquire_eurfxofi_cme6e_006_tbbo.py"; TEST_REL=BASE+"tests/test_acquire_eurfxofi_cme6e_006_tbbo.py"
REGISTRY_REL="04. Memory/research/CANDIDATE_REGISTRY.jsonl"; FOUNDATION_REL="03. EA Developer/EA_SweepCascadeContinuation/research/acquire_cme6e_mbp10_windows.py"
QUOTE_REL="02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/HYP-EURFXOFI-EURUSD-M1-005/EURFXOFI005-TBBO-FREE-QUOTE-001/metadata_quote_receipt.json"
RUNTIME_REL="02. AlphaFactory/runtime/python-databento/Scripts/python.exe"; ROOT_REL=f"02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PLAN_SHA256="007407F83C746A9E422231D142641527B2AF26181C3C80818F59DD1259F0BEF9"; QUOTE_SHA256="CAF5732E1C80EC1E4F0E32DA612C633ED5031D72DEB64342459B36FFDA35C5A7"; FOUNDATION_SHA256="1F7E38F8326743206CEDE0AE3AEA8760B6C1C4590E4DD7D7E544058CB5A8E78A"
DATASET="GLBX.MDP3";SCHEMA="tbbo";SYMBOL="6E.v.0";STYPE_IN="continuous";STYPE_OUT="instrument_id";COST_MODE="historical-streaming";SDK_VERSION="0.54.0";OWNER_CEILING_USD=2.25;EXPECTED=1359
REVIEWED_REGISTRY_ROW_SHA256: str|None="4CDC6F780543B679D648D6EF33ABC0B928F449DC7C06ADBDDF7D07A2BD57E27A"
_SENTINEL_RE=re.compile(rb'^REVIEWED_REGISTRY_ROW_SHA256: str\|None=(?:None|"[A-F0-9]{64}")\r?$')
class AcquisitionError(RuntimeError):pass
def now()->str:return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha256_file(p:Path)->str:
 d=hashlib.sha256()
 with p.open('rb') as h:
  for c in iter(lambda:h.read(1<<20),b''):d.update(c)
 return d.hexdigest().upper()
def sha256_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest().upper()
def normalized_tool_base_sha256(b:bytes)->str:
 lines=b.splitlines(keepends=True);m=[i for i,x in enumerate(lines) if _SENTINEL_RE.match(x.rstrip(b'\n'))]
 if len(m)!=1:raise AcquisitionError('invalid sentinel')
 i=m[0];nl=b'\n' if lines[i].endswith(b'\n') else b'';lines[i]=b'REVIEWED_REGISTRY_ROW_SHA256: str|None=None'+nl;return sha256_bytes(b''.join(lines))
def workspace_from_source()->Path:return Path(__file__).resolve().parents[3]
def require_d(p:Path,label:str)->Path:
 r=p.resolve()
 if r.drive.upper()!='D:':raise AcquisitionError(f'{label} must stay on D:')
 return r
def load_foundation(p:Path)->Any:
 if sha256_file(p)!=FOUNDATION_SHA256:raise AcquisitionError('foundation drift')
 s=importlib.util.spec_from_file_location('eurfxofi006_foundation',p)
 if s is None or s.loader is None:raise AcquisitionError('cannot load foundation')
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def filename(item:dict[str,Any])->str:return f"{item['request_id']}.dbn.zst"
def load_quote(p:Path)->dict[str,Any]:
 if sha256_file(p)!=QUOTE_SHA256:raise AcquisitionError('quote receipt drift')
 q=json.loads(p.read_text())
 if q.get('schema')!=SCHEMA or q.get('request_count')!=EXPECTED or q.get('within_owner_ceiling') is not True or q.get('paid_request_made') is not False or len(q.get('quotes',[]))!=EXPECTED:raise AcquisitionError('quote receipt contract invalid')
 ids=[x['request_id'] for x in q['quotes']]
 if len(ids)!=len(set(ids)) or ids!=sorted(ids):raise AcquisitionError('quote identities invalid')
 return q
def validate_authority(w:Path)->dict[str,str]:
 if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256)!=64:raise AcquisitionError('sentinel not armed')
 if sha256_file(w/PLAN_REL)!=PLAN_SHA256:raise AcquisitionError('plan drift')
 payload=(w/TOOL_REL).read_bytes();base=normalized_tool_base_sha256(payload);test=sha256_file(w/TEST_REL);found=[]
 for raw in (w/REGISTRY_REL).read_bytes().splitlines():
  r=json.loads(raw)
  if r.get('hypothesis_id')==HYPOTHESIS_ID:found.append((r,raw+b'\n'))
 if not found:raise AcquisitionError('hypothesis absent')
 row,line=found[-1];v=row.get('validation',{});rowsha=sha256_bytes(line);exp={'acquisition_plan_sha256':PLAN_SHA256,'quote_receipt_sha256':QUOTE_SHA256,'reviewed_acquisition_tool_base_sha256':base,'reviewed_acquisition_test_sha256':test,'foundation_sha256':FOUNDATION_SHA256}
 if rowsha!=REVIEWED_REGISTRY_ROW_SHA256 or row.get('state')!='probe' or v.get('paid_acquisition_authorized') is not True:raise AcquisitionError('registry authority mismatch')
 for k,val in exp.items():
  if v.get(k)!=val:raise AcquisitionError(f'registry binding mismatch: {k}')
 for k in ('economics_authorized','outcome_prices_authorized','mql5_authorized','model0_authorized','paper_trading_authorized','live_trading_authorized'):
  if v.get(k) is not False:raise AcquisitionError(f'forbidden authority open: {k}')
 return {'row_sha':rowsha,'tool_base_sha':base,'tool_file_sha':sha256_bytes(payload),'test_sha':test}
def call_args(x:dict[str,Any])->dict[str,Any]:return {'dataset':DATASET,'schema':SCHEMA,'symbols':[SYMBOL],'stype_in':STYPE_IN,'start':x['start'],'end':x['end']}
def live_quote(factory:Any,windows:list[dict[str,Any]],workers:int)->list[dict[str,Any]]:
 if not 1<=workers<=16:raise AcquisitionError('quote workers out of range')
 local=threading.local()
 def one(x):
  if not hasattr(local,'client'):local.client=factory()
  a=call_args(x);cost=float(local.client.metadata.get_cost(mode=COST_MODE,**a));size=int(local.client.metadata.get_billable_size(**a))
  if not math.isfinite(cost) or cost<0 or size<0:raise AcquisitionError('invalid live quote')
  return {**x,'live_estimated_usd':cost,'live_billable_bytes':size}
 with ThreadPoolExecutor(max_workers=workers) as pool:return sorted(pool.map(one,windows),key=lambda x:x['request_id'])
def verify_completed(root:Path,manifest:dict[str,Any],foundation:Any)->dict[str,dict[str,Any]]:
 out={}
 for x in manifest.get('downloads',[]):
  p=root/'raw'/x['filename'];records=foundation.validate_dbn_file(p,allow_zero=x.get('source_empty') is True)
  if records!=x['records'] or sha256_file(p)!=x['sha256'] or p.stat().st_size!=x['bytes']:raise AcquisitionError('checkpoint validation failed')
  out[x['filename']]=x
 return out
def execute(w:Path,workers:int)->Path:
 w=require_d(w,'workspace');runtime=require_d(w/RUNTIME_REL,'runtime')
 if Path(sys.executable).resolve()!=runtime or importlib.metadata.version('databento')!=SDK_VERSION:raise AcquisitionError('runtime mismatch')
 a=validate_authority(w);q=load_quote(w/QUOTE_REL);foundation=load_foundation(w/FOUNDATION_REL);key=foundation.load_api_key();windows=list(q['quotes']);live=live_quote(lambda:foundation.make_client(key),windows,workers)
 if len(live)!=EXPECTED:raise AcquisitionError('live quote coverage mismatch')
 total=sum(float(x['live_estimated_usd']) for x in live)
 if total>OWNER_CEILING_USD:raise AcquisitionError(f'live quote {total:.12f} exceeds ceiling {OWNER_CEILING_USD:.2f}')
 root=require_d(w/ROOT_REL,'output root');plan_path=root/'acquisition_plan.json';manifest_path=root/'download_manifest.json'
 plan={'schema_version':'eurfxofi006_tbbo_acquisition_plan.v1','hypothesis_id':HYPOTHESIS_ID,'attempt_id':ATTEMPT_ID,'created_at_utc':now(),'quote_receipt_sha256':QUOTE_SHA256,'registry_row_sha256':a['row_sha'],'tool_base_sha256':a['tool_base_sha'],'tool_file_sha256':a['tool_file_sha'],'test_sha256':a['test_sha'],'owner_ceiling_usd':OWNER_CEILING_USD,'live_estimated_total_usd':total,'live_estimated_total_bytes':sum(x['live_billable_bytes'] for x in live),'windows':live,'paid_calls_serial_only':True,'outcomes_authorized':False}
 if root.exists():
  if not plan_path.is_file() or not manifest_path.is_file():raise AcquisitionError('incomplete existing output root')
  old=json.loads(plan_path.read_text())
  for k in ('hypothesis_id','attempt_id','quote_receipt_sha256','registry_row_sha256','tool_base_sha256','test_sha256','owner_ceiling_usd'):
   if old.get(k)!=plan.get(k):raise AcquisitionError(f'existing plan mismatch: {k}')
  manifest=json.loads(manifest_path.read_text())
 else:
  root.mkdir(parents=True);foundation.write_json_atomic(plan_path,plan);manifest={'schema_version':'eurfxofi006_tbbo_download_manifest.v1','status':'LIVE_QUOTED_NOT_DOWNLOADED','updated_at_utc':now(),'attempt_id':ATTEMPT_ID,'live_estimated_total_usd':total,'downloads':[],'source_empty_windows':[],'in_flight':None,'paid_requests_completed':0,'outcome_fields_used':False};foundation.write_json_atomic(manifest_path,manifest)
 done=verify_completed(root,manifest,foundation)
 if manifest.get('in_flight'):
  f=manifest['in_flight']['filename'];final=root/'raw'/f;partial=final.with_suffix(final.suffix+'.partial')
  candidate=final if final.exists() else partial if partial.exists() else None
  if candidate is None:raise AcquisitionError('in-flight paid request has no recoverable file; no automatic retry')
  records=foundation.validate_dbn_file(candidate,allow_zero=True)
  if candidate==partial:os.replace(partial,final)
  item={**manifest['in_flight'],'bytes':final.stat().st_size,'sha256':sha256_file(final),'records':records,'source_empty':records==0,'recovered_in_flight':True};manifest['downloads'].append(item);manifest['in_flight']=None;foundation.write_json_atomic(manifest_path,manifest);done[item['filename']]=item
 raw=root/'raw';raw.mkdir(exist_ok=True);empty_ids={x['request_id'] for x in manifest['source_empty_windows']};paid_client=foundation.make_client(key)
 for x in live:
  f=filename(x)
  if f in done:continue
  if x['live_billable_bytes']==0:
   if x['request_id'] not in empty_ids:
    manifest['source_empty_windows'].append({'request_id':x['request_id'],'start':x['start'],'end':x['end'],'live_estimated_usd':x['live_estimated_usd'],'live_billable_bytes':0});empty_ids.add(x['request_id']);foundation.write_json_atomic(manifest_path,manifest)
   continue
  final=raw/f;partial=final.with_suffix(final.suffix+'.partial')
  if final.exists() or partial.exists():raise AcquisitionError('unmanifested output collision')
  inflight={'request_id':x['request_id'],'local_date':x['local_date'],'split':x['split'],'start':x['start'],'end':x['end'],'filename':f,'started_at_utc':now(),'estimated_cost_usd':x['live_estimated_usd'],'billable_bytes':x['live_billable_bytes']};manifest['status']='DOWNLOADING';manifest['in_flight']=inflight;manifest['updated_at_utc']=now();foundation.write_json_atomic(manifest_path,manifest)
  try:paid_client.timeseries.get_range(**call_args(x),stype_out=STYPE_OUT,path=partial)
  except Exception as e:raise AcquisitionError(f"paid request failed for {x['request_id']}: {e}") from e
  records=foundation.validate_dbn_file(partial,allow_zero=True);os.replace(partial,final);item={**inflight,'bytes':final.stat().st_size,'sha256':sha256_file(final),'records':records,'source_empty':records==0};manifest['downloads'].append(item);manifest['in_flight']=None;manifest['paid_requests_completed']=len(manifest['downloads']);manifest['updated_at_utc']=now();foundation.write_json_atomic(manifest_path,manifest);done[f]=item
 manifest['status']='DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED';manifest['updated_at_utc']=now();manifest['paid_requests_completed']=len(manifest['downloads']);manifest['downloaded_bytes']=sum(x['bytes'] for x in manifest['downloads']);manifest['records']=sum(x['records'] for x in manifest['downloads']);foundation.write_json_atomic(manifest_path,manifest);return manifest_path
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument('--workspace',type=Path,default=workspace_from_source());ap.add_argument('--quote-workers',type=int,default=16);x=ap.parse_args()
 try:
  p=execute(x.workspace.resolve(),x.quote_workers);m=json.loads(p.read_text());print(f"EURFXOFI006_TBBO_ACQUIRE_OK status={m['status']} paid_requests={m['paid_requests_completed']} source_empty={len(m['source_empty_windows'])} bytes={m['downloaded_bytes']} records={m['records']}");print(f'MANIFEST {p}');return 0
 except AcquisitionError as e:print(f'EURFXOFI006_TBBO_ACQUIRE_BLOCKED reason={e}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
