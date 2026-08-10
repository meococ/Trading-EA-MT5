#!/usr/bin/env python3
"""Outcome-blind native-H1 Supertrend 10/3 direction-flip source analyzer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID="HYP-ST-XAUUSD-H1-001"; ATTEMPT_ID="ST001-SOURCE-ATTEMPT-001"
PREREG_SHA256="DA955208E67D72BB4A584EEEB4AB14D51C36FF813C8E0FD488BCC1EC2EAF8621"
MANIFEST_SHA256="D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"; DATA_SHA256="B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
SOURCE_START=pd.Timestamp("2004-06-11T04:00:00Z"); DESIGN_START=pd.Timestamp("2018-01-01T00:00:00Z"); DESIGN_END=pd.Timestamp("2023-01-01T00:00:00Z")
ATR_PERIOD=10; FACTOR=3.0; DOWN=-1; UP=1
MIN_ROWS=25_000; MIN_FEATURE_COVERAGE=0.99; MIN_NEXT_COVERAGE=0.97; MIN_EVENTS=500; MIN_CADENCE=2.0; MAX_CADENCE=5.0; MIN_DIRECTION_SHARE=0.30; MAX_YEAR_SHARE=0.30; MIN_YEAR_CADENCE=1.25; MAX_YEAR_CADENCE=6.50
REQUIRED_COLUMNS=("symbol","timeframe","source_epoch","time_utc","utc_ambiguous","high","low","close")
EVENT_KEYS={"hypothesis_id","source_bar_time_utc","decision_time_utc","direction","prior_state","state","atr10","final_upper","final_lower","supertrend","source_close"}


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes: return (json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")
def jsonl_bytes(rows: list[dict[str,Any]]) -> bytes: return b"".join(json_bytes(row) for row in rows)
def atomic_write(path: Path,payload: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); temporary=path.with_name(f"{path.name}.{os.getpid()}.tmp"); temporary.write_bytes(payload); temporary.replace(path)
def finite_float(value: Any) -> float:
    result=float(value)
    if not math.isfinite(result): raise ValueError(f"non-finite output: {value!r}")
    return result
def year_weeks(year: int) -> float:
    start=max(DESIGN_START,pd.Timestamp(f"{year}-01-01T00:00:00Z")); end=min(DESIGN_END,pd.Timestamp(f"{year+1}-01-01T00:00:00Z")); return (end-start).total_seconds()/604800.0


def validate_selected_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing=sorted(set(REQUIRED_COLUMNS)-set(frame.columns))
    if missing: raise ValueError(f"missing columns: {missing}")
    data=frame.loc[:,REQUIRED_COLUMNS].copy(); data["time_utc"]=pd.to_datetime(data["time_utc"],utc=True,errors="raise"); data=data.reset_index(drop=True)
    if data.empty or data.at[0,"time_utc"]!=SOURCE_START: raise ValueError("source does not begin at manifest-declared first H1 timestamp")
    if (data["time_utc"]>=DESIGN_END).any(): raise ValueError("reader materialized sealed 2023+ rows")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any(): raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any(): raise ValueError("source_epoch must be unique and strictly increasing")
    if data["utc_ambiguous"].fillna(True).astype(bool).any(): raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["symbol"].eq("XAUUSD").all(): raise ValueError("rows are not exclusively XAUUSD")
    if not data["timeframe"].eq("H1").all(): raise ValueError("rows are not exclusively H1")
    for column in ("high","low","close"): data[column]=pd.to_numeric(data[column],errors="raise")
    values=data[["high","low","close"]].to_numpy(dtype=float)
    valid=np.isfinite(values).all(axis=1)&(values[:,0]>values[:,1])&(values[:,2]>=values[:,1])&(values[:,2]<=values[:,0])
    if not valid.all(): raise ValueError("all inception-through-design price rows must be geometrically valid")
    design_rows=int(((data["time_utc"]>=DESIGN_START)&(data["time_utc"]<DESIGN_END)).sum())
    if design_rows<MIN_ROWS: raise ValueError(f"design rows {design_rows} below {MIN_ROWS}")
    return data


def calculate_supertrend(data: pd.DataFrame) -> dict[str,np.ndarray]:
    high=data["high"].to_numpy(dtype=float); low=data["low"].to_numpy(dtype=float); close=data["close"].to_numpy(dtype=float); n=len(data)
    if n<ATR_PERIOD: raise ValueError("insufficient source rows for ATR seed")
    tr=np.empty(n,dtype=float); tr[0]=high[0]-low[0]
    tr[1:]=np.maximum.reduce((high[1:]-low[1:],np.abs(high[1:]-close[:-1]),np.abs(low[1:]-close[:-1])))
    atr=np.full(n,np.nan); seed=ATR_PERIOD-1; atr[seed]=float(np.mean(tr[:ATR_PERIOD]))
    for index in range(seed+1,n): atr[index]=((ATR_PERIOD-1)*atr[index-1]+tr[index])/ATR_PERIOD
    upper=np.full(n,np.nan); lower=np.full(n,np.nan); supertrend=np.full(n,np.nan); state=np.zeros(n,dtype=np.int8)
    hl2=(high+low)/2.0; upper[seed]=hl2[seed]+FACTOR*atr[seed]; lower[seed]=hl2[seed]-FACTOR*atr[seed]; state[seed]=DOWN; supertrend[seed]=upper[seed]
    for index in range(seed+1,n):
        basic_upper=hl2[index]+FACTOR*atr[index]; basic_lower=hl2[index]-FACTOR*atr[index]
        upper[index]=basic_upper if basic_upper<upper[index-1] or close[index-1]>upper[index-1] else upper[index-1]
        lower[index]=basic_lower if basic_lower>lower[index-1] or close[index-1]<lower[index-1] else lower[index-1]
        if supertrend[index-1]==upper[index-1]: state[index]=UP if close[index]>upper[index] else DOWN
        elif supertrend[index-1]==lower[index-1]: state[index]=DOWN if close[index]<lower[index] else UP
        else: raise ValueError("prior Supertrend line lost band identity")
        supertrend[index]=lower[index] if state[index]==UP else upper[index]
    feature_valid=(state!=0)&(np.roll(state,1)!=0)&np.isfinite(atr)&np.isfinite(upper)&np.isfinite(lower)&np.isfinite(supertrend); feature_valid[0]=False
    return {"tr":tr,"atr":atr,"upper":upper,"lower":lower,"supertrend":supertrend,"state":state,"feature_valid":feature_valid}


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str,Any]],dict[str,Any]]:
    data=frame.copy().reset_index(drop=True); data["time_utc"]=pd.to_datetime(data["time_utc"],utc=True,errors="raise")
    for column in ("high","low","close"): data[column]=pd.to_numeric(data[column],errors="raise")
    indicator=calculate_supertrend(data); state=indicator["state"]; usable=indicator["feature_valid"]; design=((data["time_utc"]>=DESIGN_START)&(data["time_utc"]<DESIGN_END)).to_numpy()
    prior=np.roll(state,1); prior[0]=0; raw_long=design&usable&(prior==DOWN)&(state==UP); raw_short=design&usable&(prior==UP)&(state==DOWN); conflicts=raw_long&raw_short; raw_long&=~conflicts; raw_short&=~conflicts; raw_mask=raw_long|raw_short
    exact_next=((data["time_utc"].shift(-1)-data["time_utc"])==pd.Timedelta(hours=1)).to_numpy(); event_mask=raw_mask&exact_next
    events=[]
    for index in np.flatnonzero(event_mask):
        bar_time=data.at[index,"time_utc"]
        events.append({"hypothesis_id":HYPOTHESIS_ID,"source_bar_time_utc":bar_time.isoformat().replace("+00:00","Z"),"decision_time_utc":(bar_time+pd.Timedelta(hours=1)).isoformat().replace("+00:00","Z"),"direction":"LONG" if raw_long[index] else "SHORT","prior_state":"DOWN" if prior[index]==DOWN else "UP","state":"UP" if state[index]==UP else "DOWN","atr10":finite_float(indicator["atr"][index]),"final_upper":finite_float(indicator["upper"][index]),"final_lower":finite_float(indicator["lower"][index]),"supertrend":finite_float(indicator["supertrend"][index]),"source_close":finite_float(data.at[index,"close"])})
    raw_count=int(raw_mask.sum()); count=len(events); gap_rejected=raw_count-count; design_rows=int(design.sum()); feature_coverage=int((usable&design).sum())/max(design_rows,1); next_coverage=count/max(raw_count,1); elapsed_weeks=(DESIGN_END-DESIGN_START).total_seconds()/604800.0; cadence=count/elapsed_weeks
    longs=sum(row["direction"]=="LONG" for row in events); shorts=count-longs; long_share=longs/count if count else 0.0; short_share=shorts/count if count else 0.0
    event_years=pd.Series([pd.Timestamp(row["source_bar_time_utc"]).year for row in events],dtype="int64"); yearly={}
    for year in range(2018,2023):
        year_count=int((event_years==year).sum()) if count else 0; weeks=year_weeks(year); yearly[str(year)]={"events":year_count,"elapsed_weeks":weeks,"cadence_per_week":year_count/weeks,"share":year_count/count if count else 0.0}
    max_year_share=max((row["share"] for row in yearly.values()),default=0.0)
    gates={"minimum_design_rows":design_rows>=MIN_ROWS,"feature_coverage":feature_coverage>=MIN_FEATURE_COVERAGE,"raw_event_exact_next_coverage":next_coverage>=MIN_NEXT_COVERAGE,"minimum_events":count>=MIN_EVENTS,"pooled_cadence":MIN_CADENCE<=cadence<=MAX_CADENCE,"direction_balance":long_share>=MIN_DIRECTION_SHARE and short_share>=MIN_DIRECTION_SHARE,"year_concentration":max_year_share<=MAX_YEAR_SHARE,"each_year_cadence":all(MIN_YEAR_CADENCE<=row["cadence_per_week"]<=MAX_YEAR_CADENCE for row in yearly.values()),"zero_direction_conflicts":int(conflicts.sum())==0}
    passed=all(gates.values()); report={"schema_version":"supertrend10x3_source_report.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"epistemic_scope":"OUTCOME_BLIND_SUPERTREND10X3_STATE_FLIPS_AND_CADENCE_ONLY","source_window":{"from":data.at[0,"time_utc"].isoformat(),"to_exclusive":DESIGN_END.isoformat()},"scored_window":{"from":DESIGN_START.isoformat(),"to_exclusive":DESIGN_END.isoformat()},"parameters":{"timeframe":"H1","atr_period":10,"factor":3.0,"atr_smoothing":"sma_seeded_wilder_rma","initial_state":"DOWN"},"funnel":{"source_rows":int(len(data)),"design_rows":design_rows,"feature_usable_design_rows":int((usable&design).sum()),"raw_events":raw_count,"executable_events":count,"gap_rejected_events":gap_rejected,"direction_conflicts":int(conflicts.sum()),"long_events":longs,"short_events":shorts},"metrics":{"elapsed_weeks":elapsed_weeks,"feature_coverage":feature_coverage,"raw_event_exact_next_coverage":next_coverage,"event_cadence_per_week":cadence,"long_share":long_share,"short_share":short_share,"max_year_event_share":max_year_share},"yearly":yearly,"gates":gates,"all_gates_pass":passed,"verdict":"SCREENED_SOURCE_PASS_MQL5_DIRECT_SUPERTREND_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_SUPERTREND10X3_FLIP","prohibitions":{"post_event_ohlc_read":False,"returns_computed":False,"trades_simulated":False,"economics_executed":False,"validation_opened":False,"holdout_opened":False,"mql5_build_authorized_by_attempt":passed,"economic_build_authorized":False,"native_supertrend_claim_authorized":False,"live_trading_authorized":False}}
    return events,report


def assert_outcome_blind(events: list[dict[str,Any]],report: dict[str,Any]) -> None:
    for row in events:
        if set(row)!=EVENT_KEYS: raise ValueError(f"event-ledger keys differ from allowlist: {sorted(set(row))}")
    if report["prohibitions"]["post_event_ohlc_read"] is not False: raise ValueError("outcome-blind report contract failed")


def validate_manifest(manifest_path: Path,data_path: Path) -> None:
    if sha256_file(manifest_path)!=MANIFEST_SHA256: raise ValueError("manifest SHA mismatch")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); matches=[item for item in manifest.get("files",[]) if str(item.get("path","")).replace("\\","/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    if len(matches)!=1 or matches[0].get("sha256")!=DATA_SHA256 or matches[0].get("first_time_utc")!="2004-06-11T04:00:00Z": raise ValueError("manifest does not bind frozen H1 data/inception")
    if not data_path.as_posix().endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"): raise ValueError("unexpected H1 data path")


def validate_registry_authority(registry_path: Path) -> dict[str,str]:
    matches=[]
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row=json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id")==HYPOTHESIS_ID: matches.append((raw,row))
    if not matches: raise ValueError("missing registry authority")
    raw,row=matches[-1]; validation=row.get("validation",{}); metrics=row.get("metrics",{})
    checks={"probe":row.get("state")=="probe","verdict":row.get("verdict")=="FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN","prereg":row.get("prereg_sha256")==PREREG_SHA256,"attempt":validation.get("source_feasibility_attempt_id")==ATTEMPT_ID,"one_attempt":validation.get("source_feasibility_attempt_limit")==1,"unconsumed":metrics.get("source_feasibility_attempts_consumed")==0,"source_run":validation.get("source_run_authorized") is True,"source_only":validation.get("source_feasibility_only") is True,"analyzer":validation.get("reviewed_analyzer_sha256")==sha256_file(Path(__file__).resolve()),"prehistory":validation.get("prehistory_source_access_authorized") is True,"no_outcomes":validation.get("outcome_prices_authorized") is False,"no_economics":validation.get("economics_authorized") is False,"no_validation":validation.get("research_validation_access_authorized") is False,"no_holdout":validation.get("research_holdout_access_authorized") is False,"no_mt5":validation.get("mt5_authorized") is False,"no_mql5":validation.get("mql5_authorized") is False,"no_live":validation.get("live_trading_authorized") is False}
    failed=[name for name,ok in checks.items() if not ok]
    if failed: raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256":sha256_file(registry_path),"latest_row_sha256":hashlib.sha256(raw).hexdigest().upper()}


def claim_attempt(output_dir: Path,authority: dict[str,str]) -> tuple[str,Path]:
    if output_dir.exists() and any(output_dir.iterdir()): raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True,exist_ok=True); marker_path=output_dir/"attempt_started.json"; started=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"); marker={"schema_version":"supertrend_attempt_started.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"started_at_utc":started,"process_id":os.getpid(),"registry_sha256":authority["registry_sha256"],"latest_hypothesis_row_sha256":authority["latest_row_sha256"],"analyzer_sha256":sha256_file(Path(__file__).resolve()),"status":"ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"}
    try:
        with marker_path.open("xb") as handle: handle.write(json_bytes(marker)); handle.flush(); os.fsync(handle.fileno())
    except FileExistsError as exc: raise ValueError("attempt already claimed") from exc
    return started,marker_path


def execute(root: Path) -> dict[str,Any]:
    prereg=root/"03. EA Developer/EA_SupertrendStateFlip/research/HYP-ST-XAUUSD-H1-001_FROZEN_PREREG.md"; manifest=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"; data_path=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"; registry=root/"04. Memory/research/CANDIDATE_REGISTRY.jsonl"; output_dir=root/"03. EA Developer/EA_SupertrendStateFlip/research/evidence/HYP-ST-XAUUSD-H1-001/ST001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg)!=PREREG_SHA256: raise ValueError("preregistration SHA mismatch")
    authority=validate_registry_authority(registry); started,start_path=claim_attempt(output_dir,authority); validate_manifest(manifest,data_path)
    if sha256_file(data_path)!=DATA_SHA256: raise ValueError("H1 data SHA mismatch")
    if not set(REQUIRED_COLUMNS)<=set(pq.ParquetFile(data_path).schema_arrow.names): raise ValueError("Parquet schema missing required columns")
    raw=pd.read_parquet(data_path,columns=list(REQUIRED_COLUMNS),filters=[("time_utc","<",DESIGN_END.to_pydatetime())],engine="pyarrow"); selected=validate_selected_frame(raw); events,report=analyze_frame(selected); assert_outcome_blind(events,report); replay_events,replay_report=analyze_frame(selected)
    if jsonl_bytes(events)!=jsonl_bytes(replay_events) or json_bytes(report)!=json_bytes(replay_report): raise ValueError("deterministic replay failed")
    report_bytes=json_bytes(report); ledger_bytes=jsonl_bytes(events); report_path=output_dir/"st_001_source_report.json"; ledger_path=output_dir/"st_001_event_ledger.jsonl"; atomic_write(report_path,report_bytes); atomic_write(ledger_path,ledger_bytes)
    receipt={"schema_version":"supertrend_source_receipt.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"started_at_utc":started,"completed_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"bindings":{"preregistration":{"path":prereg.relative_to(root).as_posix(),"sha256":sha256_file(prereg)},"manifest":{"path":manifest.relative_to(root).as_posix(),"sha256":sha256_file(manifest)},"data":{"path":data_path.relative_to(root).as_posix(),"sha256":sha256_file(data_path)},"analyzer":{"path":Path(__file__).resolve().relative_to(root).as_posix(),"sha256":sha256_file(Path(__file__).resolve())},"candidate_registry":{"path":registry.relative_to(root).as_posix(),**authority},"attempt_started":{"path":start_path.relative_to(root).as_posix(),"sha256":sha256_file(start_path)},"report":{"path":report_path.relative_to(root).as_posix(),"sha256":hashlib.sha256(report_bytes).hexdigest().upper()},"event_ledger":{"path":ledger_path.relative_to(root).as_posix(),"sha256":hashlib.sha256(ledger_bytes).hexdigest().upper()}},"outcome_blind_counters":{"post_event_ohlc_rows_read":0,"returns_computed":0,"trades_simulated":0,"pnl_computed":0,"profit_factor_computed":0,"validation_rows_read":0,"holdout_rows_read":0},"verdict":report["verdict"]}
    receipt_bytes=json_bytes(receipt); receipt_path=output_dir/"source_feasibility_receipt.json"; atomic_write(receipt_path,receipt_bytes); terminal={"schema_version":"supertrend_attempt_terminal.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"completed_at_utc":receipt["completed_at_utc"],"status":"COMPLETE","verdict":report["verdict"],"source_feasibility_receipt_sha256":hashlib.sha256(receipt_bytes).hexdigest().upper(),"same_id_retry_authorized":False}; atomic_write(output_dir/"attempt_terminal.json",json_bytes(terminal)); return {"report":report,"receipt":receipt,"output_dir":str(output_dir)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--execute",action="store_true"); args=parser.parse_args()
    if not args.execute: parser.error("--execute is required")
    result=execute(Path(__file__).resolve().parents[3]); print(json_bytes(result["report"]).decode("utf-8"),end=""); return 0


if __name__=="__main__": raise SystemExit(main())
