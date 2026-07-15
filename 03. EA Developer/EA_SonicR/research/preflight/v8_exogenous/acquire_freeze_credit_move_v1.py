#!/usr/bin/env python3
"""Acquire/freeze Yahoo HYG/LQD credit relative + ^MOVE bond vol (W26).

Authority: Owner HARD PIVOT W26 — post W23–W25 commodity/sector ToT ALL_KILL.
FORBIDDEN densify: Yahoo commodity→AUD ToT (NG/ZW/TIO/Cu/Gold/WTI/Brent clones).
Owner-authorized reopen of parked credit/bond-vol class (≠ VIXCLS densify twin).

No Model0 by acquire alone. ChatGPT login wall remains Owner-parallel only.

Lag: US ETF/index daily close → available_at = observation_date + 1 calendar day.

Mechanisms:
  HYG/LQD — high-yield vs IG credit relative (risk appetite / credit stress).
  ^MOVE   — ICE BofA MOVE bond-vol index (rates-vol risk-off for AUD).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_CR = HERE / "raw" / "credit"
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
    hyg_raw = RAW_CR / "yahoo_hyg_chart.json"
    lqd_raw = RAW_CR / "yahoo_lqd_chart.json"
    move_raw = RAW_CR / "yahoo_move_chart.json"
    uup_raw = RAW_CR / "yahoo_uup_chart.json"  # acquired spare; not primary freeze
    for p in (hyg_raw, lqd_raw, move_raw):
        assert p.is_file(), f"missing raw {p}"

    hyg = load_yahoo_closes(hyg_raw)
    lqd = load_yahoo_closes(lqd_raw)
    move = load_yahoo_closes(move_raw)
    assert len(hyg) >= 200, f"HYG too short n={len(hyg)}"
    assert len(lqd) >= 200, f"LQD too short n={len(lqd)}"
    assert len(move) >= 200, f"MOVE too short n={len(move)}"

    credit_rows = []
    for obs, ratio, va, vb in aligned_ratio(hyg, lqd):
        avail = obs + timedelta(days=1)
        credit_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "hyg_lqd_ratio": f"{ratio:.8f}",
                "hyg_close": f"{va:.6f}",
                "lqd_close": f"{vb:.6f}",
            }
        )
    credit_panel = write_panel(
        "yahoo_hyg_lqd_credit_rel_d1_v1.csv",
        credit_rows,
        [
            "observation_date",
            "available_at_utc",
            "hyg_lqd_ratio",
            "hyg_close",
            "lqd_close",
        ],
    )

    move_rows = []
    for obs, px in move:
        avail = obs + timedelta(days=1)
        move_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "move_close": f"{px:.6f}",
            }
        )
    move_panel = write_panel(
        "yahoo_move_bondvol_d1_v1.csv",
        move_rows,
        ["observation_date", "available_at_utc", "move_close"],
    )

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": [
            {
                "id": "HYG_LQD_CREDIT_RELATIVE",
                "panel": "yahoo_hyg_lqd_credit_rel_d1_v1.csv",
                "source": "Yahoo Finance chart HYG/LQD daily closes (ratio)",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Credit risk appetite: HY vs IG relative. HY outperformance "
                    "(ratio↑) → risk-on for AUDUSD; ratio↓ → credit stress / risk-off. "
                    "≠ commodity ToT; ≠ VIXCLS equity-vol densify twin; Owner W26 reopen."
                ),
                "not_commodity_tot_clone": True,
                "not_vixcls_retune": True,
                "owner_authorized_w26": True,
            },
            {
                "id": "MOVE_BOND_VOL",
                "panel": "yahoo_move_bondvol_d1_v1.csv",
                "source": "Yahoo Finance chart ^MOVE (ICE BofA MOVE Index) daily close",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Bond/rates vol risk-off for AUD: MOVE↑ → short AUDUSD displace; "
                    "MOVE↓ calm → long AUDUSD. ≠ equity VIX densify; ≠ commodity ToT."
                ),
                "not_vixcls_retune": True,
                "not_commodity_tot_clone": True,
                "owner_authorized_w26": True,
            },
        ],
        "acquired_spare_not_primary": [
            {
                "id": "UUP_TWUSD_ETF_PROXY",
                "raw": "yahoo_uup_chart.json",
                "note": "trade-weighted USD ETF proxy acquired; not used in W26 probes",
                "present": uup_raw.is_file(),
            }
        ],
        "unavailable_this_pass": [],
        "banned": [
            "NG_ZW_natgas_wheat_commodity_tot_densify",
            "TIO_ironore_retune",
            "USDCNY_CNY_strength_retune",
            "XLK_XLF_sector_retune",
            "HG_GC_cugold_retune",
            "WTI_USDCAD_z_retune",
            "BRENT_EURUSD_importer_retune",
            "VIXCLS_riskoff_USDJPY_retune",
            "SPX_DGS10_equity_bond_retune",
            "WALCL_ECB_MMF_G10_overnight_fred_retune",
            "COT_size_z_retune",
            "W1_W25_OHLC_densify",
            "commodity_yahoo_aud_tot_clones",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_CREDIT_MOVE_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = []
    for p, url, note in [
        (
            hyg_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/HYG",
            "iShares HYG high-yield corporate bond ETF",
        ),
        (
            lqd_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/LQD",
            "iShares LQD IG corporate bond ETF",
        ),
        (
            move_raw,
            "https://query1.finance.yahoo.com/v8/finance/chart/%5EMOVE",
            "ICE BofA MOVE bond-vol index",
        ),
        (credit_panel, "derived", "HYG/LQD credit relative lag +1d"),
        (move_panel, "derived", "MOVE bond-vol lag +1d"),
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
    if uup_raw.is_file():
        files.append(
            {
                "name": uup_raw.name,
                "bytes": uup_raw.stat().st_size,
                "sha256": sha256_file(uup_raw),
                "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/UUP",
                "note": "UUP TW-USD ETF spare (not primary W26 probe)",
                "path": str(uup_raw),
            }
        )

    manifest = {
        "schema": "v8_credit_move_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "Owner_W26_HARD_PIVOT_non_commodity_after_W23_W25_commodity_ToT_ALL_KILL; "
            "ChatGPT login wall parallel; no Model0 by acquire"
        ),
        "status": "ACQUISITION_EXECUTED",
        "surface_class": "credit_hyg_lqd_relative + bondvol_move",
        "banned_this_session": contract["banned"],
        "files": files,
        "panel_sha256": {
            "yahoo_hyg_lqd_credit_rel_d1_v1.csv": sha256_file(credit_panel),
            "yahoo_move_bondvol_d1_v1.csv": sha256_file(move_panel),
        },
        "row_counts": {
            "credit_hyg_lqd": len(credit_rows),
            "move": len(move_rows),
        },
        "contract_path": str(contract_path),
    }
    out = MANIFESTS / "20260715_CREDIT_MOVE_ACQUISITION_V1.json"
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
