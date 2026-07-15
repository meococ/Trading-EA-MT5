#!/usr/bin/env python3
"""Acquire/freeze Yahoo NG=F natgas + ZW=F wheat for AUD ToT exo (W25).

Authority: post W24 ironore+CNY ALL_KILL — new public exo outside killboard.
No Model0 by acquire alone. ChatGPT login wall remains Owner-parallel only.

Independent of: TIO iron ore · USDCNY/CNY · XLK/XLF sector · HG/GC CuGold ·
WTI/Brent oil · VIX/MOVE/HY/DTWEX siblings · WALCL/ECB/MMF/G10 overnight /
COT FRED boards · W1–W24 OHLC densify.

Lag: daily close → available_at = observation_date + 1 calendar day.

Mechanisms:
  NG=F  — Henry Hub natgas as LNG/energy-export ToT proxy for AUD (≠ crude oil).
  ZW=F  — CBOT wheat as ag softs ToT proxy for AUD (≠ bulk ore / metals).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_COM = HERE / "raw" / "commodity"
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


def main() -> None:
    ng_raw = RAW_COM / "yahoo_ng_f_chart.json"
    zw_raw = RAW_COM / "yahoo_zw_f_chart.json"
    assert ng_raw.is_file(), f"missing raw {ng_raw}"
    assert zw_raw.is_file(), f"missing raw {zw_raw}"

    ng = load_yahoo_closes(ng_raw)
    zw = load_yahoo_closes(zw_raw)
    assert len(ng) >= 200, f"natgas too short n={len(ng)}"
    assert len(zw) >= 200, f"wheat too short n={len(zw)}"

    ng_rows = []
    for obs, px in ng:
        avail = obs + timedelta(days=1)
        ng_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "ng_close": f"{px:.6f}",
            }
        )
    ng_panel = write_panel(
        "yahoo_ng_natgas_d1_v1.csv",
        ng_rows,
        ["observation_date", "available_at_utc", "ng_close"],
    )

    zw_rows = []
    for obs, px in zw:
        avail = obs + timedelta(days=1)
        zw_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "zw_close": f"{px:.6f}",
            }
        )
    zw_panel = write_panel(
        "yahoo_zw_wheat_d1_v1.csv",
        zw_rows,
        ["observation_date", "available_at_utc", "zw_close"],
    )

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": [
            {
                "id": "NG_NATGAS_LNG_PROXY",
                "panel": "yahoo_ng_natgas_d1_v1.csv",
                "source": "Yahoo Finance chart NG=F (NYMEX Henry Hub natgas) daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Australia LNG/energy-export ToT factor; Henry Hub proxy for "
                    "global gas complex; ≠ WTI/Brent crude oil ToT; ≠ TIO iron ore"
                ),
                "not_wti_brent_oil_clone": True,
                "not_ironore_clone": True,
            },
            {
                "id": "ZW_WHEAT_AG_TOT",
                "panel": "yahoo_zw_wheat_d1_v1.csv",
                "source": "Yahoo Finance chart ZW=F (CBOT wheat) daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Australia ag softs ToT channel; ≠ bulk ore; ≠ HG/GC metals; "
                    "≠ XLK/XLF sector relative"
                ),
                "not_cugold_clone": True,
                "not_sector_xlkxlf_twin": True,
            },
        ],
        "unavailable_this_pass": [],
        "banned": [
            "TIO_ironore_retune",
            "USDCNY_CNY_strength_retune",
            "XLK_XLF_sector_retune",
            "HG_GC_cugold_retune",
            "VIXCLS_riskoff_USDJPY_retune",
            "SPX_DGS10_equity_bond_retune",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "WTI_USDCAD_z_retune",
            "BRENT_EURUSD_importer_retune",
            "WALCL_ECB_MMF_G10_overnight_fred_retune",
            "COT_size_z_retune",
            "W1_W24_OHLC_densify",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_NATGAS_WHEAT_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = []
    for p, url, note in [
        (
            ng_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/NG=F",
            "NYMEX natgas NG=F",
        ),
        (
            zw_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/ZW=F",
            "CBOT wheat ZW=F",
        ),
        (ng_panel, "derived", "NG natgas lag +1d"),
        (zw_panel, "derived", "ZW wheat lag +1d"),
        (contract_path, "derived", "lag contract"),
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
        "schema": "v8_natgas_wheat_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "post_W24_ironore_cny_ALL_KILL_new_exo; ChatGPT login wall parallel; "
            "no Model0 by acquire"
        ),
        "status": "ACQUISITION_EXECUTED",
        "surface_class": "aud_lng_energy_tot + aud_ag_wheat_tot",
        "banned_this_session": contract["banned"],
        "files": files,
        "panel_sha256": {
            "yahoo_ng_natgas_d1_v1.csv": sha256_file(ng_panel),
            "yahoo_zw_wheat_d1_v1.csv": sha256_file(zw_panel),
        },
        "row_counts": {
            "natgas": len(ng_rows),
            "wheat": len(zw_rows),
        },
        "contract_path": str(contract_path),
    }
    out = MANIFESTS / "20260715_NATGAS_WHEAT_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(out),
                "panels": manifest["panel_sha256"],
                "rows": manifest["row_counts"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
