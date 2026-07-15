#!/usr/bin/env python3
"""Acquire/freeze Yahoo TIO=F iron ore + USDCNY China FX strength proxy.

Authority: post W23 sector+cugold ALL_KILL — new public exo outside killboard.
No Model0 by acquire alone. ChatGPT login wall remains Owner-parallel only.

Independent of: XLK/XLF sector · HG/GC CuGold · WTI/Brent oil · VIX/MOVE/HY/DTWEX/
EVZ siblings · WALCL/ECB/MMF/G10 overnight FRED boards · W1–W23 OHLC densify.

Lag: daily close → available_at = observation_date + 1 calendar day.

CNH=X / USDCNH=X proved unusable this pass (n≈1) → pick USDCNY=X + invert to
CNY strength (1/USDCNY). Iron ore uses SGX TIO=F (≠ HG copper).
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
RAW_FX = HERE / "raw" / "fx_china"
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
    tio_raw = RAW_COM / "yahoo_tio_f_chart.json"
    usdcny_raw = RAW_FX / "yahoo_usdcny_x_chart.json"
    cnh_raw = RAW_FX / "yahoo_cnh_x_chart.json"
    usdcnh_raw = RAW_FX / "yahoo_USDCNH-X_chart.json"
    assert tio_raw.is_file(), f"missing raw {tio_raw}"
    assert usdcny_raw.is_file(), f"missing raw {usdcny_raw}"

    tio = load_yahoo_closes(tio_raw)
    usdcny = load_yahoo_closes(usdcny_raw)
    assert len(tio) >= 200, f"iron ore too short n={len(tio)}"
    assert len(usdcny) >= 200, f"usdcny too short n={len(usdcny)}"

    iron_rows = []
    for obs, px in tio:
        avail = obs + timedelta(days=1)
        iron_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "tio_close": f"{px:.6f}",
            }
        )
    iron_panel = write_panel(
        "yahoo_tio_ironore_d1_v1.csv",
        iron_rows,
        ["observation_date", "available_at_utc", "tio_close"],
    )

    cny_rows = []
    for obs, px in usdcny:
        if px <= 0:
            continue
        strength = 1.0 / px  # CNY strength vs USD (↑ = CNY stronger)
        avail = obs + timedelta(days=1)
        cny_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "usdcny_close": f"{px:.8f}",
                "cny_usd_strength": f"{strength:.10f}",
            }
        )
    cny_panel = write_panel(
        "yahoo_usdcny_cny_strength_d1_v1.csv",
        cny_rows,
        [
            "observation_date",
            "available_at_utc",
            "usdcny_close",
            "cny_usd_strength",
        ],
    )

    # Document CNH offshore attempt
    cnh_note = "UNAVAILABLE_THIS_PASS"
    for cand in (cnh_raw, usdcnh_raw):
        if not cand.is_file():
            continue
        try:
            n = len(load_yahoo_closes(cand))
        except Exception:
            n = 0
        if n >= 200:
            cnh_note = f"RAW_USABLE:{cand.name}:n={n}"
            break
        cnh_note = f"RAW_PRESENT_BUT_SPARSE:{cand.name}:n={n}"

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": [
            {
                "id": "TIO_IRON_ORE",
                "panel": "yahoo_tio_ironore_d1_v1.csv",
                "source": "Yahoo Finance chart TIO=F (SGX iron ore) daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Australia dominant bulk export ToT factor; ≠ WTI/Brent oil; "
                    "≠ HG/GC copper-gold industrial/haven ratio"
                ),
                "not_wti_brent_oil_clone": True,
                "not_cugold_clone": True,
            },
            {
                "id": "CNY_USD_STRENGTH",
                "panel": "yahoo_usdcny_cny_strength_d1_v1.csv",
                "source": "Yahoo Finance chart USDCNY=X inverted to CNY strength",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "China demand / CNY strength channel for AUD; "
                    "CNH offshore sparse → USDCNY proxy; ≠ VIX risk-off twin"
                ),
                "not_vix_riskoff_twin": True,
                "not_sector_xlkxlf_twin": True,
            },
        ],
        "unavailable_this_pass": [
            {
                "id": "CNH_OFFSHORE_USDCNH",
                "attempts": [
                    "Yahoo CNH=X → n≈1 unusable",
                    "Yahoo USDCNH=X → n≈1 unusable",
                ],
                "status": cnh_note,
                "ruling": "PROVE_UNAVAILABLE_PICK_NEXT__USDCNY_STRENGTH_SELECTED",
            }
        ],
        "banned": [
            "XLK_XLF_sector_retune",
            "HG_GC_cugold_retune",
            "VIXCLS_riskoff_USDJPY_retune",
            "SPX_DGS10_equity_bond_retune",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "WTI_USDCAD_z_retune",
            "BRENT_EURUSD_importer_retune",
            "WALCL_ECB_MMF_G10_overnight_fred_retune",
            "W1_W23_OHLC_densify",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_IRONORE_CNY_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = []
    for p, url, note in [
        (
            tio_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/TIO=F",
            "SGX iron ore TIO=F",
        ),
        (
            usdcny_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/USDCNY=X",
            "USDCNY=X daily",
        ),
        (iron_panel, "derived", "TIO iron ore lag +1d"),
        (cny_panel, "derived", "CNY strength=1/USDCNY lag +1d"),
        (contract_path, "derived", "lag contract + CNH unavailable receipt"),
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
        "schema": "v8_ironore_cny_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "post_W23_sector_cugold_ALL_KILL_new_exo; ChatGPT login wall parallel; "
            "no Model0 by acquire"
        ),
        "status": "ACQUISITION_EXECUTED",
        "surface_class": "aud_bulk_export_tot + china_fx_demand_channel",
        "cnh_offshore_status": cnh_note,
        "banned_this_session": contract["banned"],
        "files": files,
        "panel_sha256": {
            "yahoo_tio_ironore_d1_v1.csv": sha256_file(iron_panel),
            "yahoo_usdcny_cny_strength_d1_v1.csv": sha256_file(cny_panel),
        },
        "row_counts": {
            "iron_ore": len(iron_rows),
            "cny_strength": len(cny_rows),
        },
        "contract_path": str(contract_path),
    }
    out = MANIFESTS / "20260715_IRONORE_CNY_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(out),
                "panels": manifest["panel_sha256"],
                "rows": manifest["row_counts"],
                "cnh": cnh_note,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
