#!/usr/bin/env python3
"""Outcome-blind EURUSD H1 Ultimate Oscillator re-entry source screen."""
from __future__ import annotations
import argparse, hashlib, json, math, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

HYPOTHESIS_ID="HYP-UO-EURUSD-H1-001"; ATTEMPT_ID="UO001-SOURCE-ATTEMPT-001"
PREREG_SHA256="34C5A9C42562EF66423B3FDC491F0492AC9BC8DDEE08386EC89FB1505E27FFF2"; TEST_SHA256="5AEA19B8FA4592561A21DA699D0340770859FF1A43258062E7FD702F958850A7"
MANIFEST_SHA256="D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256="78BF655C67392A23690C80DB127E24997D0CD14264B573A3832D167C9361FCF3"
DESIGN_START=pd.Timestamp("2018-01-01T00:00:00Z"); DESIGN_END=pd.Timestamp("2023-01-01T00:00:00Z")
MIN_ROWS=25_000
REQUIRED_COLUMNS=("symbol","timeframe","source_epoch","time_utc","utc_ambiguous","high","low","close")
EVENT_KEYS={"hypothesis_id","source_bar_time_utc","source_epoch","decision_time_utc",
            "decision_source_epoch","direction","prior_uo","uo","avg7","avg14","avg28"}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest().upper()

def json_bytes(x:Any)->bytes:
    return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()

def jsonl_bytes(rows:list[dict[str,Any]])->bytes: return b"".join(json_bytes(r) for r in rows)

def exclusive_write(path:Path,payload:bytes)->None:
    with path.open("xb") as f: f.write(payload); f.flush(); os.fsync(f.fileno())

def validate_frame(frame:pd.DataFrame)->pd.DataFrame:
    missing=sorted(set(REQUIRED_COLUMNS)-set(frame.columns))
    if missing: raise ValueError(f"missing columns {missing}")
    d=frame.loc[:,REQUIRED_COLUMNS].copy(); d["time_utc"]=pd.to_datetime(d["time_utc"],utc=True,errors="raise")
    if (d["time_utc"]>=DESIGN_END).any(): raise ValueError("sealed row materialized")
    if not d["time_utc"].is_monotonic_increasing or d["time_utc"].duplicated().any(): raise ValueError("UTC order")
    if not d["source_epoch"].is_monotonic_increasing or d["source_epoch"].duplicated().any(): raise ValueError("epoch order")
    if d["utc_ambiguous"].fillna(True).astype(bool).any(): raise ValueError("ambiguous UTC")
    if not d["symbol"].eq("EURUSD").all() or not d["timeframe"].eq("H1").all(): raise ValueError("identity")
    for c in ("high","low","close"): d[c]=pd.to_numeric(d[c],errors="raise")
    v=d.loc[:,["high","low","close"]].to_numpy(float)
    valid=(np.isfinite(v).all(1)&(v>0).all(1)&(v[:,0]>=v[:,1])&(v[:,2]>=v[:,1])&(v[:,2]<=v[:,0]))
    if not bool(valid.all()): raise ValueError("price geometry")
    if int(((d["time_utc"]>=DESIGN_START)&(d["time_utc"]<DESIGN_END)).sum())<MIN_ROWS: raise ValueError("rows")
    return d.reset_index(drop=True)

def ultimate(high:np.ndarray,low:np.ndarray,close:np.ndarray)->tuple[np.ndarray,...]:
    n=len(close); bp=np.full(n,np.nan); tr=np.full(n,np.nan)
    bp[1:]=close[1:]-np.minimum(low[1:],close[:-1])
    tr[1:]=np.maximum(high[1:],close[:-1])-np.minimum(low[1:],close[:-1])
    avgs=[]
    for p in (7,14,28):
        avg=np.full(n,np.nan)
        for i in range(p,n):
            bpsum=float(np.sum(bp[i-p+1:i+1])); trsum=float(np.sum(tr[i-p+1:i+1]))
            if math.isfinite(bpsum) and math.isfinite(trsum) and trsum>0: avg[i]=bpsum/trsum
        avgs.append(avg)
    uo=100.0*(4.0*avgs[0]+2.0*avgs[1]+avgs[2])/7.0
    return bp,tr,avgs[0],avgs[1],avgs[2],uo

def year_weeks(y:int)->float:
    return (min(DESIGN_END,pd.Timestamp(f"{y+1}-01-01T00:00:00Z"))-max(DESIGN_START,pd.Timestamp(f"{y}-01-01T00:00:00Z"))).total_seconds()/604800

def analyze_frame(d:pd.DataFrame)->tuple[list[dict[str,Any]],dict[str,Any]]:
    d=d.copy().reset_index(drop=True); d["time_utc"]=pd.to_datetime(d["time_utc"],utc=True)
    bp,tr,a7,a14,a28,uo=ultimate(d.high.to_numpy(float),d.low.to_numpy(float),d.close.to_numpy(float))
    design=((d.time_utc>=DESIGN_START)&(d.time_utc<DESIGN_END)).to_numpy()
    feature=design&np.isfinite(uo)&np.isfinite(np.roll(uo,1)); feature[0]=False
    lr=feature&(np.roll(uo,1)<=30)&(uo>30); sr=feature&(np.roll(uo,1)>=70)&(uo<70); lr[0]=False; sr[0]=False
    conflict=lr&sr; lr&=~conflict; sr&=~conflict; raw=lr|sr
    nt=d.time_utc.shift(-1); ne=d.source_epoch.shift(-1)
    exact=(((nt-d.time_utc)==pd.Timedelta(hours=1)).to_numpy()&
           (ne.to_numpy(float)==d.source_epoch.to_numpy(float)+3600.0)&(nt<DESIGN_END).fillna(False).to_numpy())
    events=[]
    for i in np.flatnonzero(raw&exact):
        st=d.at[i,"time_utc"]
        events.append({"hypothesis_id":HYPOTHESIS_ID,"source_bar_time_utc":st.isoformat().replace("+00:00","Z"),
                       "source_epoch":int(d.at[i,"source_epoch"]),"decision_time_utc":nt.iloc[i].isoformat().replace("+00:00","Z"),
                       "decision_source_epoch":int(ne.iloc[i]),"direction":"LONG" if lr[i] else "SHORT",
                       "prior_uo":float(uo[i-1]),"uo":float(uo[i]),"avg7":float(a7[i]),"avg14":float(a14[i]),"avg28":float(a28[i])})
    dr=int(design.sum()); usable=int(feature.sum()); rc=int(raw.sum()); count=len(events); longs=sum(e["direction"]=="LONG" for e in events); shorts=count-longs
    elapsed=(DESIGN_END-DESIGN_START).total_seconds()/604800; years=pd.Series([pd.Timestamp(e["decision_time_utc"]).year for e in events],dtype="int64")
    yearly={}
    for y in range(2018,2023):
        num=int((years==y).sum()) if count else 0; weeks=year_weeks(y)
        yearly[str(y)]={"events":num,"elapsed_weeks":weeks,"cadence_per_week":num/weeks,"share":num/count if count else 0.0}
    fc=usable/max(dr,1); nc=count/max(rc,1); cad=count/elapsed; ls=longs/count if count else 0; ss=shorts/count if count else 0; mys=max((x["share"] for x in yearly.values()),default=0)
    gates={"minimum_design_rows":dr>=MIN_ROWS,"feature_coverage":fc>=.99,"raw_event_exact_next_coverage":nc>=.97,
           "minimum_events":count>=500,"pooled_cadence":2<=cad<=5,"direction_balance":ls>=.30 and ss>=.30,
           "year_concentration":mys<=.30,"each_year_cadence":all(1.25<=x["cadence_per_week"]<=6.5 for x in yearly.values()),
           "zero_direction_conflicts":int(conflict.sum())==0}
    passed=all(gates.values())
    report={"schema_version":"uo_reentry_source_report.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,
            "scope":"OUTCOME_BLIND_UO_REENTRY_SOURCE_AND_CADENCE_ONLY","formula":{"periods":[7,14,28],"levels":[30,70]},
            "funnel":{"materialized_history_rows":len(d),"design_rows":dr,"feature_usable_rows":usable,"raw_events":rc,
                      "executable_events":count,"gap_rejected_events":rc-count,"long_events":longs,"short_events":shorts,
                      "direction_conflicts":int(conflict.sum())},
            "metrics":{"elapsed_weeks":elapsed,"feature_coverage":fc,"raw_event_exact_next_coverage":nc,
                       "event_cadence_per_week":cad,"long_share":ls,"short_share":ss,"max_year_event_share":mys},
            "yearly":yearly,"gates":gates,"all_gates_pass":passed,
            "verdict":"SCREENED_SOURCE_PASS_UO_MQL5_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_UO_REENTRY",
            "prohibitions":{"next_row_ohlc_read":False,"post_event_ohlc_read":False,"returns_computed":False,
                            "trades_simulated":False,"profit_factor_computed":False,"economics_executed":False,
                            "validation_opened":False,"holdout_opened":False,"mt5_opened":False,"mql5_created":False,
                            "live_trading_authorized":False}}
    return events,report

def claim_attempt(out:Path)->tuple[str,Path,str]:
    if out.exists(): raise ValueError("attempt root exists")
    out.mkdir(parents=True,exist_ok=False); started=datetime.now(timezone.utc).isoformat().replace("+00:00","Z"); ash=sha256_file(Path(__file__).resolve())
    marker={"schema_version":"uo_source_attempt_started.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,
            "started_at_utc":started,"analyzer_sha256":ash,"status":"CLAIMED_BEFORE_BOUND_SOURCE_READ"}
    p=out/"attempt_started.json"; exclusive_write(p,json_bytes(marker)); return started,p,ash

def execute(root:Path)->dict[str,Any]:
    prereg=root/"03. EA Developer/EA_UltimateOscillatorReentry/research/HYP-UO-EURUSD-H1-001_FROZEN_PREREG.md"
    manifest=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet"
    analyzer=Path(__file__).resolve(); test=root/"03. EA Developer/EA_UltimateOscillatorReentry/research/tests/test_analyze_uo_h1_source.py"
    out=root/"03. EA Developer/EA_UltimateOscillatorReentry/research/evidence/HYP-UO-EURUSD-H1-001/UO001-SOURCE-ATTEMPT-001"
    started,marker,claimed=claim_attempt(out)
    try:
        bound={"prereg":prereg,"manifest":manifest,"data":data,"analyzer":analyzer,"test":test}; initial={k:sha256_file(v) for k,v in bound.items()}
        if initial["analyzer"]!=claimed: raise ValueError("analyzer drift")
        if initial["prereg"]!=PREREG_SHA256 or initial["test"]!=TEST_SHA256: raise ValueError("package SHA")
        if initial["manifest"]!=MANIFEST_SHA256 or initial["data"]!=DATA_SHA256: raise ValueError("data SHA")
        mj=json.loads(manifest.read_text(encoding="utf-8")); matches=[r for r in mj.get("files",[]) if str(r.get("path","")).replace("\\","/").endswith("EURUSD/EURUSD_H1_ALL_AVAILABLE_20260801.parquet")]
        if len(matches)!=1 or matches[0].get("sha256")!=DATA_SHA256: raise ValueError("manifest entry")
        frame=pd.read_parquet(data,columns=list(REQUIRED_COLUMNS),filters=[("time_utc","<",DESIGN_END.to_pydatetime())],engine="pyarrow")
        selected=validate_frame(frame); events,report=analyze_frame(selected)
        if any(set(e)!=EVENT_KEYS for e in events) or any(report["prohibitions"].values()): raise ValueError("outcome boundary")
        e2,r2=analyze_frame(selected)
        if jsonl_bytes(events)!=jsonl_bytes(e2) or json_bytes(report)!=json_bytes(r2): raise ValueError("replay")
        if {k:sha256_file(v) for k,v in bound.items()}!=initial: raise ValueError("bound input drift")
        lb,rb=jsonl_bytes(events),json_bytes(report); lp=out/"uo_001_event_ledger.jsonl"; rp=out/"uo_001_source_report.json"
        exclusive_write(lp,lb); exclusive_write(rp,rb); completed=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
        bindings={k:{"path":v.relative_to(root).as_posix(),"sha256":initial[k]} for k,v in bound.items()}
        bindings.update({"attempt_started":{"path":marker.relative_to(root).as_posix(),"sha256":sha256_file(marker)},
                         "ledger":{"path":lp.relative_to(root).as_posix(),"sha256":hashlib.sha256(lb).hexdigest().upper()},
                         "report":{"path":rp.relative_to(root).as_posix(),"sha256":hashlib.sha256(rb).hexdigest().upper()}})
        receipt={"schema_version":"uo_source_receipt.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,
                 "started_at_utc":started,"completed_at_utc":completed,"bindings":bindings,
                 "outcome_blind_counters":{"next_row_ohlc_reads":0,"post_event_ohlc_reads":0,"returns_computed":0,
                                             "trades_simulated":0,"profit_factor_computed":0,"validation_rows_read":0,
                                             "holdout_rows_read":0,"mt5_launches":0,"mql5_files_created":0},"verdict":report["verdict"]}
        rec=json_bytes(receipt); exclusive_write(out/"source_feasibility_receipt.json",rec)
        terminal={"schema_version":"uo_source_attempt_terminal.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,
                  "completed_at_utc":completed,"status":"COMPLETE","verdict":report["verdict"],
                  "receipt_sha256":hashlib.sha256(rec).hexdigest().upper(),"same_id_retry_authorized":False}
        exclusive_write(out/"attempt_terminal.json",json_bytes(terminal)); return report
    except Exception as exc:
        tp=out/"attempt_terminal.json"
        if not tp.exists(): exclusive_write(tp,json_bytes({"schema_version":"uo_source_attempt_terminal.v1","hypothesis_id":HYPOTHESIS_ID,
            "attempt_id":ATTEMPT_ID,"completed_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "status":"FAILED","error":str(exc),"same_id_retry_authorized":False}))
        raise

def main()->int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--execute",action="store_true"); a=p.parse_args()
    if not a.execute: p.error("--execute is required")
    print(json_bytes(execute(Path(__file__).resolve().parents[3])).decode(),end=""); return 0
if __name__=="__main__": raise SystemExit(main())
