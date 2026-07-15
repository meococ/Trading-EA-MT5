#!/usr/bin/env python3
"""Rebuild PD GS-total panel + freeze CME 6J forward-basis from Yahoo chart JSON."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

EXO = Path(__file__).resolve().parent
RAW_F = EXO / "raw" / "forwards"
RAW_S = EXO / "raw" / "signed_flow"
PANEL = EXO / "panels"
CONTRACTS = EXO / "contracts"
MANIFESTS = EXO / "manifests"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def main() -> None:
    # --- Yahoo chart JSON -> daily CSV ---
    jpath = RAW_F / "yahoo_chart_6j.json"
    if not jpath.is_file():
        raise SystemExit(f"missing {jpath}")
    data = json.loads(jpath.read_text(encoding="utf-8"))
    res = data["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    by: dict[date, float] = {}
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = datetime.fromtimestamp(int(t), timezone.utc).date()
        by[d] = float(c)
    csv_path = RAW_F / "yahoo_6j_f_from_chart_daily.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Close"])
        for d in sorted(by):
            w.writerow([d.isoformat(), f"{by[d]:.8f}"])
    print("6J rows", len(by), sha(csv_path))

    # --- PD PDPOSGST-TOT ---
    pd_raw = RAW_S / "nyfed_pd_all_timeseries.csv"
    pd_by: dict[date, float] = {}
    with pd_raw.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("Time Series") != "PDPOSGST-TOT":
                continue
            vs = (row.get("Value (millions)") or "").strip()
            if not vs or vs.upper() in {"N/A", "NA", "."}:
                continue
            pd_by[date.fromisoformat(row["As Of Date"][:10])] = float(vs)
    out = []
    prev = None
    for obs in sorted(pd_by):
        val = pd_by[obs]
        avail = obs + timedelta(days=8)
        wow = "" if prev is None else f"{(val - prev):.4f}"
        out.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "pd_net_mn_usd": f"{val:.4f}",
                "wow_delta_mn": wow,
                "agg_mode": "PDPOSGST-TOT",
                "series_key": "PDPOSGST-TOT",
            }
        )
        prev = val
    pd_panel = PANEL / "nyfed_pd_ust_net_pos_w1_v1.csv"
    with pd_panel.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print("PD panel", len(out), sha(pd_panel), "first", out[0], "last", out[-1])
    (CONTRACTS / "20260714_NYFED_PD_UST_NET_AVAILABLE_AT_UTC_CONTRACT_V1.json").write_text(
        json.dumps(
            {
                "panel": pd_panel.name,
                "agg_mode": "PDPOSGST-TOT",
                "series_key": "PDPOSGST-TOT",
                "n_dates": len(out),
                "lag_contract": "available_at = observation_date + 8 calendar days",
                "note": "v2 GS total only; tip/frn filter VOID",
                "panel_sha256": sha(pd_panel),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # --- Forward basis ---
    spot: dict[date, float] = {}
    with (RAW_F / "fred_dexjpus.csv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("observation_date") or row.get("DATE") or "").strip()
            vs = (row.get("DEXJPUS") or "").strip()
            if not ds or not vs or vs in {".", "NA"}:
                continue
            spot[date.fromisoformat(ds[:10])] = float(vs)
    basis_rows = []
    for d, fut in sorted(by.items()):
        if d not in spot:
            continue
        s = 1.0 / spot[d]
        basis = fut / s - 1.0
        avail = d + timedelta(days=1)
        basis_rows.append(
            {
                "observation_date": d.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "fut_close": f"{fut:.8f}",
                "spot_usd_per_jpy": f"{s:.8f}",
                "fwd_basis": f"{basis:.8f}",
            }
        )
    bp = PANEL / "jpy_cme6j_spot_fwd_basis_d1_v1.csv"
    with bp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(basis_rows[0].keys()))
        w.writeheader()
        w.writerows(basis_rows)
    bs = [float(r["fwd_basis"]) for r in basis_rows]
    print(
        "basis",
        len(basis_rows),
        sha(bp),
        "mean",
        round(sum(bs) / len(bs), 6),
        "min",
        round(min(bs), 6),
        "max",
        round(max(bs), 6),
    )
    (CONTRACTS / "20260714_JPY_CME6J_FWD_BASIS_AVAILABLE_AT_UTC_CONTRACT_V1.json").write_text(
        json.dumps(
            {
                "fut": "Yahoo chart API 6J=F continuous",
                "spot": "FRED DEXJPUS",
                "field": "fwd_basis=fut/(1/DEXJPUS)-1",
                "lag_days": 1,
                "n": len(basis_rows),
                "panel_sha256": sha(bp),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    man_path = MANIFESTS / "20260714_FORWARDS_SIGNEDFLOW_ACQUISITION_V1.json"
    m = json.loads(man_path.read_text(encoding="utf-8"))
    mmf = PANEL / "fred_retail_mmf_wow_w1_v1.csv"
    m["panels_sha256"] = {
        "nyfed_pd_ust_net_pos_w1_v1.csv": sha(pd_panel),
        "fred_retail_mmf_wow_w1_v1.csv": sha(mmf) if mmf.is_file() else None,
        "jpy_cme6j_spot_fwd_basis_d1_v1.csv": sha(bp),
        "yahoo_6j_f_from_chart_daily.csv": sha(csv_path),
    }
    m["panel_notes"] = [
        "NYFED PDPOSGST-TOT signed inventory panel frozen (v2)",
        "WRMFSL retail MMF WoW panel frozen",
        "JPY CME6J vs DEXJPUS forward-basis panel frozen (Yahoo chart API)",
    ]
    m["status"] = "ACQUISITION_EXECUTED"
    m["forwards_blocker_stooq"] = "JS_challenge"
    m["forwards_blocker_yahoo_v7_download"] = "empty_or_crumb; chart_v8_ok"
    m["updated_at_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    man_path.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print("manifest", man_path)


if __name__ == "__main__":
    main()
