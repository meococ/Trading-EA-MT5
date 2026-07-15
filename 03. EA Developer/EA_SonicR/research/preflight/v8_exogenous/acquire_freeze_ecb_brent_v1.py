#!/usr/bin/env python3
"""Acquire/freeze FRED ECBASSETSW + DCOILBRENTEU panels with lag contracts.

Authority: post PD-primary / cost-GAP — new exo outside killboard.
Does NOT authorize registry/prereg/EA/Model 0 by itself.

Banned densify: WALCL sign twin · WTI-USDCAD · HY/MOVE/DTWEX VIX sibling ·
PD/MMF/6J · COT · Wave1–9 · invent spreads.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_CB = HERE / "raw" / "cb_bs"
RAW_COM = HERE / "raw" / "commodity"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (PANEL, MANIFESTS, CONTRACTS):
    p.mkdir(parents=True, exist_ok=True)

ACQUIRED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def load_fred(path: Path, value_col: str) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("observation_date") or "").strip()
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


def main() -> None:
    ecb_raw = RAW_CB / "fred_ecbassetsw.csv"
    brent_raw = RAW_COM / "fred_dcoilbrenteu.csv"
    boj_raw = RAW_CB / "fred_jpnasassets.csv"
    assert ecb_raw.is_file(), "missing ECBASSETSW raw"
    assert brent_raw.is_file(), "missing Brent raw"

    # ECB weekly: observation typically Fri week-end; Eurosystem statement often
    # Tue → fail-closed available_at = observation + 5 calendar days.
    ecb_rows = []
    prev = None
    for obs, val in load_fred(ecb_raw, "ECBASSETSW"):
        avail = obs + timedelta(days=5)
        wow = "" if prev is None else f"{(val - prev) / prev:.8f}"
        ecb_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "ecb_assets_mn_eur": f"{val:.0f}",
                "wow_pct": wow,
            }
        )
        prev = val
    ecb_panel = write_panel(
        "fred_ecbassetsw_wow_w1_v1.csv",
        ecb_rows,
        ["observation_date", "available_at_utc", "ecb_assets_mn_eur", "wow_pct"],
    )

    # Brent: observation t → available_at = t + 1 calendar day (cash close lag)
    brent_rows = []
    for obs, val in load_fred(brent_raw, "DCOILBRENTEU"):
        avail = obs + timedelta(days=1)
        brent_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "brent_usd": f"{val:.4f}",
            }
        )
    brent_panel = write_panel(
        "fred_brent_dcoilbrenteu_d1_v1.csv",
        brent_rows,
        ["observation_date", "available_at_utc", "brent_usd"],
    )

    boj_note = "RAW_ONLY_MONTHLY_NO_PANEL" if boj_raw.is_file() else "MISSING"
    # JPNASSETS is monthly → too coarse for this H1 displace campaign; raw only.

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": [
            {
                "id": "ECBASSETSW",
                "panel": "fred_ecbassetsw_wow_w1_v1.csv",
                "lag_rule": "available_at = observation_date + 5 calendar days",
                "rationale": (
                    "Weekly Eurosystem financial statement; Fri observation often "
                    "Tue publish → +5d fail-closed vs same-week lookahead"
                ),
                "not_walcl_twin": True,
            },
            {
                "id": "DCOILBRENTEU",
                "panel": "fred_brent_dcoilbrenteu_d1_v1.csv",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": "FRED daily Brent cash; +1d vs same-day close lookahead",
                "not_wti_usdcad_clone": True,
            },
        ],
        "banned": [
            "WALCL_sign_gate_retune",
            "WTI_USDCAD_z_retune",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "PD_MMF_6J_densify",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_ECB_BRENT_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = []
    for p, url, note in [
        (ecb_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=ECBASSETSW", "ECB weekly assets"),
        (brent_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU", "Brent spot"),
        (boj_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=JPNASSETS", boj_note),
        (ecb_panel, "derived", "lag +5d panel with wow_pct"),
        (brent_panel, "derived", "lag +1d panel"),
        (contract_path, "derived", "lag contract"),
    ]:
        if not p.is_file():
            continue
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
        "schema": "v8_ecb_brent_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": "post_pd_primary_cost_gap_new_exo; no Model0 by acquire",
        "status": "ACQUISITION_EXECUTED",
        "banned_this_session": [
            "WALCL_sign_gate_retune",
            "WTI_USDCAD_z_retune",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "PD_MMF_6J_densify",
            "JPNASSETS_monthly_auto_probe",
            "invent_spreads",
        ],
        "files": files,
        "panel_sha256": {
            "fred_ecbassetsw_wow_w1_v1.csv": sha256_file(ecb_panel),
            "fred_brent_dcoilbrenteu_d1_v1.csv": sha256_file(brent_panel),
        },
        "contract_path": str(contract_path),
    }
    out = MANIFESTS / "20260715_ECB_BRENT_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(out), "panels": manifest["panel_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
