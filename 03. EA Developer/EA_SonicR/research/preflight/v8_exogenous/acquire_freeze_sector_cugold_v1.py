#!/usr/bin/env python3
"""Acquire/freeze Yahoo XLK/XLF sector relative + HG/GC copper-gold ratio.

Authority: post W22 ALL_KILL / OHLC HARD PIVOT saturated / ChatGPT login wall —
new public exo outside killboard. No Model0 by acquire alone.

Independent of: VIXCLS risk-off · SPX−DGS10 · WTI/Brent oil ToT · WALCL/ECB BS ·
MOVE/HY/DTWEX VIX siblings · COT · G10 overnight carry · W1–W22 OHLC densify.

Lag: US cash/futures daily close → available_at = observation_date + 1 calendar day.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_EQ = HERE / "raw" / "equity_sector"
RAW_COM = HERE / "raw" / "commodity"
RAW_VOL = HERE / "raw" / "vol"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (PANEL, MANIFESTS, CONTRACTS):
    p.mkdir(parents=True, exist_ok=True)

ACQUIRED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def load_yahoo_closes(path: Path) -> list[tuple[date, float]]:
    j = json.loads(path.read_text(encoding="utf-8"))
    res = (j.get("chart") or {}).get("result") or []
    if not res:
        raise RuntimeError(f"no yahoo result in {path}")
    r0 = res[0]
    ts = r0.get("timestamp") or []
    closes = ((r0.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    out: list[tuple[date, float]] = []
    for t, c in zip(ts, closes):
        if c is None or (isinstance(c, float) and (math.isnan(c) or c <= 0)):
            continue
        d = datetime.fromtimestamp(int(t), timezone.utc).date()
        out.append((d, float(c)))
    out.sort(key=lambda x: x[0])
    # de-dup keep last
    dedup: dict[date, float] = {}
    for d, c in out:
        dedup[d] = c
    return sorted(dedup.items(), key=lambda x: x[0])


def write_panel(name: str, rows: list[dict], fields: list[str]) -> Path:
    path = PANEL / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def aligned_ratio(
    a: list[tuple[date, float]], b: list[tuple[date, float]]
) -> list[tuple[date, float, float, float]]:
    mb = dict(b)
    out = []
    for d, va in a:
        vb = mb.get(d)
        if vb is None or va <= 0 or vb <= 0:
            continue
        out.append((d, va / vb, va, vb))
    return out


def main() -> None:
    xlk_raw = RAW_EQ / "yahoo_xlk_chart.json"
    xlf_raw = RAW_EQ / "yahoo_xlf_chart.json"
    hg_raw = RAW_COM / "yahoo_hg_f_chart.json"
    gc_raw = RAW_COM / "yahoo_gc_f_chart.json"
    for p in (xlk_raw, xlf_raw, hg_raw, gc_raw):
        assert p.is_file(), f"missing raw {p}"

    xlk = load_yahoo_closes(xlk_raw)
    xlf = load_yahoo_closes(xlf_raw)
    hg = load_yahoo_closes(hg_raw)
    gc = load_yahoo_closes(gc_raw)

    sector_rows = []
    for obs, ratio, va, vb in aligned_ratio(xlk, xlf):
        avail = obs + timedelta(days=1)
        sector_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "xlk_close": f"{va:.6f}",
                "xlf_close": f"{vb:.6f}",
                "xlk_xlf_ratio": f"{ratio:.8f}",
            }
        )
    sector_panel = write_panel(
        "yahoo_xlk_xlf_ratio_d1_v1.csv",
        sector_rows,
        [
            "observation_date",
            "available_at_utc",
            "xlk_close",
            "xlf_close",
            "xlk_xlf_ratio",
        ],
    )

    cugold_rows = []
    for obs, ratio, va, vb in aligned_ratio(hg, gc):
        avail = obs + timedelta(days=1)
        cugold_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "hg_close": f"{va:.6f}",
                "gc_close": f"{vb:.6f}",
                "cu_gold_ratio": f"{ratio:.8f}",
            }
        )
    cugold_panel = write_panel(
        "yahoo_hg_gc_cugold_ratio_d1_v1.csv",
        cugold_rows,
        [
            "observation_date",
            "available_at_utc",
            "hg_close",
            "gc_close",
            "cu_gold_ratio",
        ],
    )

    # Document EVZ/OVX attempt status if present
    evz_note = "UNAVAILABLE_THIS_PASS"
    for cand in (
        RAW_VOL / "yahoo_EVZ_chart.json",
        RAW_VOL / "fred_evzcls.csv",
        RAW_VOL / "dbnomics_fred_evzcls.json",
    ):
        if cand.is_file() and cand.stat().st_size > 2000:
            evz_note = f"RAW_PRESENT:{cand.name}"
            break

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": [
            {
                "id": "XLK_XLF_RATIO",
                "panel": "yahoo_xlk_xlf_ratio_d1_v1.csv",
                "source": "Yahoo Finance chart XLK + XLF daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "US equity sector ETF cash close; +1d fail-closed vs same-day "
                    "FX H1 use (no intraday ETF lookahead)"
                ),
                "not_vix_riskoff_twin": True,
                "not_spx_dgs10_twin": True,
            },
            {
                "id": "HG_GC_CUGOLD_RATIO",
                "panel": "yahoo_hg_gc_cugold_ratio_d1_v1.csv",
                "source": "Yahoo Finance chart HG=F + GC=F daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Copper vs gold futures ratio as industrial/growth factor; "
                    "+1d vs same-day FX; ≠ WTI/Brent oil spot ToT"
                ),
                "not_wti_brent_oil_clone": True,
            },
        ],
        "unavailable_this_pass": [
            {
                "id": "EVZCLS_FX_VOL",
                "attempts": [
                    "fred.stlouisfed.org/graph/fredgraph.csv?id=EVZCLS → TimeoutError",
                    "api.db.nomics.world FRED/EVZCLS → 404",
                    "Yahoo EVZ/^EVZ → no usable series this pass",
                ],
                "status": evz_note,
                "ruling": "PROVE_UNAVAILABLE_PICK_NEXT__SECTOR_CUGOLD_SELECTED",
            }
        ],
        "banned": [
            "VIXCLS_riskoff_USDJPY_retune",
            "SPX_DGS10_equity_bond_retune",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "WTI_USDCAD_z_retune",
            "BRENT_EURUSD_importer_retune",
            "W1_W22_OHLC_densify",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_SECTOR_CUGOLD_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = []
    for p, url, note in [
        (
            xlk_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/XLK",
            "XLK daily chart json",
        ),
        (
            xlf_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/XLF",
            "XLF daily chart json",
        ),
        (
            hg_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/HG=F",
            "Copper futures HG=F",
        ),
        (
            gc_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
            "Gold futures GC=F",
        ),
        (sector_panel, "derived", "XLK/XLF ratio lag +1d"),
        (cugold_panel, "derived", "HG/GC copper-gold ratio lag +1d"),
        (contract_path, "derived", "lag contract + EVZ unavailable receipt"),
    ]:
        files.append(
            {
                "name": p.name,
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "source_url": url,
                "note": note,
                "path": str(p),
            }
        )

    manifest = {
        "schema": "v8_sector_cugold_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "post_W22_ALL_KILL_new_exo; ChatGPT login wall parallel; "
            "no Model0 by acquire"
        ),
        "status": "ACQUISITION_EXECUTED",
        "surface_class": "equity_sector_relative + commodity_curve_factor_beyond_oil",
        "evz_fx_vol_status": evz_note,
        "banned_this_session": contract["banned"],
        "files": files,
        "panel_sha256": {
            "yahoo_xlk_xlf_ratio_d1_v1.csv": sha256_file(sector_panel),
            "yahoo_hg_gc_cugold_ratio_d1_v1.csv": sha256_file(cugold_panel),
        },
        "row_counts": {
            "sector_ratio": len(sector_rows),
            "cugold_ratio": len(cugold_rows),
        },
        "contract_path": str(contract_path),
    }
    out = MANIFESTS / "20260715_SECTOR_CUGOLD_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(out),
                "panels": manifest["panel_sha256"],
                "rows": manifest["row_counts"],
                "evz": evz_note,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
