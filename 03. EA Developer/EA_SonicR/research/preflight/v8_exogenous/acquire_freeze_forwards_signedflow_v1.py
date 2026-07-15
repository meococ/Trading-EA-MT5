#!/usr/bin/env python3
"""Acquire/freeze highest-EV public surfaces: FX futures (forwards proxy),
signed flow (NY Fed PD / MMF), OIS-basis proxies — with lag contracts.

Authority: post WTI/WALCL kill — prefer true forwards / signed flow.
Does NOT authorize registry/prereg/EA/Model 0 by itself.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (RAW / "forwards", RAW / "signed_flow", RAW / "basis", PANEL, MANIFESTS, CONTRACTS):
    p.mkdir(parents=True, exist_ok=True)

ACQUIRED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
HEADERS = {"User-Agent": "Mozilla/5.0 (SonicR-research; offline-probe; local)"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def try_get(name: str, url: str, path: Path, timeout: int = 45) -> dict:
    t0 = time.time()
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        path.write_bytes(r.content)
        head = r.content[:160].decode("utf-8", errors="replace").replace("\n", " | ")
        ok = (
            r.status_code == 200
            and len(r.content) > 200
            and "<html" not in head.lower()[:50]
            and "requires javascript" not in head.lower()
        )
        return {
            "name": name,
            "url": url,
            "path": str(path),
            "status": r.status_code,
            "bytes": len(r.content),
            "ok": ok,
            "secs": round(time.time() - t0, 2),
            "sha256": sha256_file(path) if path.is_file() else None,
            "head": head[:180],
            "blocker": None if ok else "non_csv_or_empty_or_challenge",
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "path": str(path),
            "ok": False,
            "error": str(e),
            "blocker": type(e).__name__,
            "secs": round(time.time() - t0, 2),
        }


def load_fred_csv(path: Path, value_col: str) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("observation_date") or row.get("DATE") or "").strip()
            vs = (row.get(value_col) or "").strip()
            if not ds or not vs or vs in {".", "NA", "N/A"}:
                continue
            try:
                rows.append((date.fromisoformat(ds[:10]), float(vs)))
            except ValueError:
                continue
    rows.sort(key=lambda x: x[0])
    return rows


def write_panel(name: str, rows: list[dict], fields: list[str]) -> Path:
    path = PANEL / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def build_mmf_panel(raw: Path, col: str, out_name: str, lag_days: int = 2) -> Path | None:
    if not raw.is_file() or raw.stat().st_size < 200:
        return None
    # Reject HTML challenge bodies
    head = raw.read_bytes()[:80].decode("utf-8", errors="replace").lower()
    if "<html" in head:
        return None
    series = load_fred_csv(raw, col)
    if len(series) < 52:
        return None
    out = []
    prev = None
    for obs, val in series:
        avail = obs + timedelta(days=lag_days)
        wow = "" if prev is None else f"{(val - prev) / prev:.8f}"
        out.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "mmf_bn_usd": f"{val:.3f}",
                "wow_pct": wow,
            }
        )
        prev = val
    return write_panel(
        out_name,
        out,
        ["observation_date", "available_at_utc", "mmf_bn_usd", "wow_pct"],
    )


def build_pd_ust_net_panel(raw: Path) -> Path | None:
    """NY Fed Primary Dealer gov securities net — signed inventory flow.

    Canonical series: PDPOSGST-TOT (Government Securities Total, $mn).
    Not COT futures positioning — cash dealer inventory.
    """
    if not raw.is_file() or raw.stat().st_size < 1000:
        return None
    by_date: dict[date, float] = {}
    with raw.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (row.get("Time Series") or row.get("keyId") or "").strip()
            if key != "PDPOSGST-TOT":
                continue
            ds = (row.get("As Of Date") or row.get("asOfDate") or "").strip()
            vs = (row.get("Value (millions)") or row.get("value") or "").strip()
            if not ds or not vs or vs.upper() in {"N/A", "NA", "."}:
                continue
            try:
                by_date[date.fromisoformat(ds[:10])] = float(vs)
            except ValueError:
                continue
    if len(by_date) < 40:
        return None

    dates = sorted(by_date)
    out = []
    prev = None
    for obs in dates:
        val = by_date[obs]
        # Weekly release typically Thursday ~16:15 ET for prior week.
        # Fail-closed: observation_date + 8 calendar days available_at.
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

    panel = write_panel(
        "nyfed_pd_ust_net_pos_w1_v1.csv",
        out,
        [
            "observation_date",
            "available_at_utc",
            "pd_net_mn_usd",
            "wow_delta_mn",
            "agg_mode",
            "series_key",
        ],
    )
    meta = {
        "panel": panel.name,
        "agg_mode": "PDPOSGST-TOT",
        "series_key": "PDPOSGST-TOT",
        "n_dates": len(out),
        "n_keys_used": 1,
        "sample_keys": ["PDPOSGST-TOT"],
        "lag_contract": "available_at = observation_date + 8 calendar days (fail-closed vs Thu release)",
        "note": "v2 rebuild — prior tip/frn filter VOID; use GS total only",
    }
    (CONTRACTS / "20260714_NYFED_PD_UST_NET_AVAILABLE_AT_UTC_CONTRACT_V1.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return panel


def build_yahoo_futures_basis(
    fut_path: Path, spot_path: Path, out_name: str, lag_days: int = 1
) -> Path | None:
    """Futures close / spot − 1 as forward-points proxy (dimensionless)."""
    if not fut_path.is_file() or not spot_path.is_file():
        return None
    for p in (fut_path, spot_path):
        head = p.read_bytes()[:60].decode("utf-8", errors="replace").lower()
        if "<html" in head or "too many requests" in head:
            return None

    fut: dict[date, float] = {}
    with fut_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("Date") or "").strip()
            vs = (row.get("Adj Close") or row.get("Close") or "").strip()
            if not ds or not vs or vs in {"null", "None"}:
                continue
            try:
                fut[date.fromisoformat(ds[:10])] = float(vs)
            except ValueError:
                continue

    # CME 6J quoted as USD per JPY (e.g. 0.0068); FRED DEXJPUS is JPY per USD.
    # Convert spot to USDJPY inverse for comparable quote: spot_usd_per_jpy = 1/DEXJPUS
    spot: dict[date, float] = {}
    with spot_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("observation_date") or row.get("DATE") or row.get("Date") or "").strip()
            vs = (
                row.get("DEXJPUS")
                or row.get("Adj Close")
                or row.get("Close")
                or row.get("value")
                or ""
            ).strip()
            if not ds or not vs or vs in {".", "NA", "null"}:
                continue
            try:
                d = date.fromisoformat(ds[:10])
                raw = float(vs)
                # If values look like JPYUSD (>50), invert to USD per JPY
                spot[d] = (1.0 / raw) if raw > 1.0 else raw
            except ValueError:
                continue

    out = []
    for d in sorted(set(fut) & set(spot)):
        s = spot[d]
        if s == 0:
            continue
        basis = (fut[d] / s) - 1.0
        avail = d + timedelta(days=lag_days)
        out.append(
            {
                "observation_date": d.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "fut_close": f"{fut[d]:.8f}",
                "spot_usd_per_jpy": f"{s:.8f}",
                "fwd_basis": f"{basis:.8f}",
            }
        )
    if len(out) < 100:
        return None
    return write_panel(
        out_name,
        out,
        [
            "observation_date",
            "available_at_utc",
            "fut_close",
            "spot_usd_per_jpy",
            "fwd_basis",
        ],
    )


def main() -> None:
    attempts: list[dict] = []

    # --- Acquire attempts (highest EV first) ---
    targets = [
        (
            "NYFED_PD_ALL",
            "https://markets.newyorkfed.org/api/pd/get/all/timeseries.csv",
            RAW / "signed_flow" / "nyfed_pd_all_timeseries.csv",
            120,
        ),
        (
            "FRED_WRMFSL",
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WRMFSL",
            RAW / "signed_flow" / "fred_wrmfsl.csv",
            60,
        ),
        (
            "FRED_WIMFSL",
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WIMFSL",
            RAW / "signed_flow" / "fred_wimfsl.csv",
            60,
        ),
        (
            "FRED_DEXJPUS",
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXJPUS",
            RAW / "forwards" / "fred_dexjpus.csv",
            60,
        ),
        (
            "YAHOO_6J",
            "https://query1.finance.yahoo.com/v7/finance/download/6J%3DF?period1=1514764800&period2=1780000000&interval=1d&events=history&includeAdjustedClose=true",
            RAW / "forwards" / "yahoo_6j_f_daily.csv",
            45,
        ),
        (
            "YAHOO_6E",
            "https://query1.finance.yahoo.com/v7/finance/download/6E%3DF?period1=1514764800&period2=1780000000&interval=1d&events=history&includeAdjustedClose=true",
            RAW / "forwards" / "yahoo_6e_f_daily.csv",
            45,
        ),
        (
            "STOOQ_JF",
            "https://stooq.com/q/d/l/?s=jf.f&i=d",
            RAW / "forwards" / "stooq_jf_f_daily.csv",
            30,
        ),
        (
            "BOC_FX_DAILY",
            "https://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/csv?start_date=2018-01-01",
            RAW / "forwards" / "boc_fx_rates_daily.csv",
            45,
        ),
        (
            "OFR_NYPD_META",
            "https://data.financialresearch.gov/v1/series/dataset?dataset=nypd",
            RAW / "signed_flow" / "ofr_nypd_dataset.json",
            45,
        ),
        (
            "FRED_CP90",
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=RIFSPPFAAD90NB",
            RAW / "basis" / "fred_cp_aa_90d.csv",
            45,
        ),
    ]

    # Reuse existing NY Fed download if already large+valid
    existing_pd = RAW / "signed_flow" / "nyfed_pd_all_timeseries.csv"
    if existing_pd.is_file() and existing_pd.stat().st_size > 1_000_000:
        head = existing_pd.read_bytes()[:40].decode("utf-8", errors="replace")
        if "As Of Date" in head or "asOfDate" in head:
            attempts.append(
                {
                    "name": "NYFED_PD_ALL",
                    "url": "https://markets.newyorkfed.org/api/pd/get/all/timeseries.csv",
                    "path": str(existing_pd),
                    "ok": True,
                    "bytes": existing_pd.stat().st_size,
                    "sha256": sha256_file(existing_pd),
                    "reused_existing": True,
                    "blocker": None,
                }
            )
            # skip re-download of PD
            targets = [t for t in targets if t[0] != "NYFED_PD_ALL"]

    for name, url, path, timeout in targets:
        print(f"GET {name} ...", flush=True)
        res = try_get(name, url, path, timeout=timeout)
        attempts.append(res)
        print(
            f"  -> ok={res.get('ok')} bytes={res.get('bytes')} blocker={res.get('blocker') or res.get('error')}",
            flush=True,
        )

    panels: dict[str, str] = {}
    panel_notes: list[str] = []

    pd_panel = build_pd_ust_net_panel(existing_pd if existing_pd.is_file() else RAW / "signed_flow" / "nyfed_pd_all_timeseries.csv")
    if pd_panel:
        panels[pd_panel.name] = sha256_file(pd_panel)
        panel_notes.append("NYFED_PD_UST_NET signed inventory panel frozen")
    else:
        panel_notes.append("NYFED_PD_UST_NET panel FAILED")

    mmf = build_mmf_panel(
        RAW / "signed_flow" / "fred_wrmfsl.csv",
        "WRMFSL",
        "fred_retail_mmf_wow_w1_v1.csv",
        lag_days=2,
    )
    if mmf:
        panels[mmf.name] = sha256_file(mmf)
        panel_notes.append("WRMFSL retail MMF WoW panel frozen")
        (CONTRACTS / "20260714_FRED_WRMFSL_AVAILABLE_AT_UTC_CONTRACT_V1.json").write_text(
            json.dumps(
                {
                    "series": "WRMFSL",
                    "lag_days": 2,
                    "available_at": "observation_date + 2 calendar days",
                    "rationale": "weekly MMF assets; fail-closed vs same-week lookahead",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        panel_notes.append("WRMFSL panel FAILED (acquire miss or HTML)")

    basis = build_yahoo_futures_basis(
        RAW / "forwards" / "yahoo_6j_f_daily.csv",
        RAW / "forwards" / "fred_dexjpus.csv",
        "jpy_cme6j_spot_fwd_basis_d1_v1.csv",
        lag_days=1,
    )
    if basis:
        panels[basis.name] = sha256_file(basis)
        panel_notes.append("JPY CME6J vs DEXJPUS forward-basis panel frozen")
        (CONTRACTS / "20260714_JPY_CME6J_FWD_BASIS_AVAILABLE_AT_UTC_CONTRACT_V1.json").write_text(
            json.dumps(
                {
                    "fut": "Yahoo 6J=F daily settle proxy",
                    "spot": "FRED DEXJPUS",
                    "field": "fwd_basis = fut/spot_usd_per_jpy - 1",
                    "lag_days": 1,
                    "note": "continuous futures; not vendor-clean term structure",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        panel_notes.append("JPY forward-basis panel FAILED")

    ok_names = [a["name"] for a in attempts if a.get("ok")]
    fail_names = [
        {
            "name": a["name"],
            "blocker": a.get("blocker") or a.get("error") or a.get("head", "")[:80],
        }
        for a in attempts
        if not a.get("ok")
    ]

    manifest = {
        "schema": "v8_forwards_signedflow_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": "post_WTI_WALCL_kill_prefer_forwards_or_signed_flow; no Model0 by acquire",
        "status": "ACQUISITION_PARTIAL" if panels else "ACQUISITION_FAILED",
        "attempts": attempts,
        "ok_surfaces": ok_names,
        "failed_surfaces": fail_names,
        "panels_sha256": panels,
        "panel_notes": panel_notes,
        "banned_this_session": [
            "COT_z_or_size_retune",
            "WTI_z_USDCAD_displace_densify",
            "WALCL_sign_retune",
            "SOFR_SONIA_twin_rescue",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "price_twin_Wave1_9_densify",
        ],
    }
    out = MANIFESTS / "20260714_FORWARDS_SIGNEDFLOW_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(out), "panels": panels, "ok": ok_names, "fail": fail_names}, indent=2))


if __name__ == "__main__":
    main()
