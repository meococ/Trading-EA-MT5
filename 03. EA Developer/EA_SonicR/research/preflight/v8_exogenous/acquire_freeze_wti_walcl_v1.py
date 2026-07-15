#!/usr/bin/env python3
"""Acquire/freeze FRED WTI + WALCL panels with lag contracts.

Authority: post COT size+|z| / Wave7 / dichotomy empty — new exo surfaces only.
Does NOT authorize registry/prereg/EA/Model 0 by itself.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "commodity"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
for p in (RAW, PANEL, MANIFESTS):
    p.mkdir(parents=True, exist_ok=True)

ACQUIRED_AT = datetime.now(timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def load_fred(path: Path, value_col: str) -> list[tuple[date, float]]:
    rows: list[tuple[date, float]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            ds = (row.get("observation_date") or "").strip()
            vs = (row.get(value_col) or "").strip()
            if not ds or not vs or vs in {".", "NA", "N/A"}:
                continue
            try:
                d = date.fromisoformat(ds[:10])
                rows.append((d, float(vs)))
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
    wti_raw = RAW / "fred_dcoilwtico.csv"
    walcl_raw = RAW / "fred_walcl.csv"
    t10yie_raw = RAW / "fred_t10yie.csv"
    assert wti_raw.is_file(), "missing WTI raw"
    assert walcl_raw.is_file(), "missing WALCL raw"

    # WTI: observation t → available_at = t + 1 calendar day (FRED cash close lag)
    wti_rows = []
    for obs, val in load_fred(wti_raw, "DCOILWTICO"):
        avail = obs + timedelta(days=1)
        wti_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "wti_usd": f"{val:.4f}",
            }
        )
    wti_panel = write_panel(
        "fred_wti_dcoilwtico_d1_v1.csv",
        wti_rows,
        ["observation_date", "available_at_utc", "wti_usd"],
    )

    # WALCL weekly: observation t → available_at = t + 2 calendar days
    # (Fed H.4.1 often Thu release; +2 fail-closed vs same-day lookahead)
    walcl_rows = []
    prev = None
    for obs, val in load_fred(walcl_raw, "WALCL"):
        avail = obs + timedelta(days=2)
        wow = "" if prev is None else f"{(val - prev) / prev:.8f}"
        walcl_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "walcl_mn_usd": f"{val:.0f}",
                "wow_pct": wow,
            }
        )
        prev = val
    walcl_panel = write_panel(
        "fred_walcl_wow_w1_v1.csv",
        walcl_rows,
        ["observation_date", "available_at_utc", "walcl_mn_usd", "wow_pct"],
    )

    # Keep T10YIE raw on disk but DO NOT build RR2 gate panel this session
    # (twin-risk vs D2 yield-z after dichotomy kill).
    t10_note = "RAW_ONLY_NO_PANEL" if t10yie_raw.is_file() else "MISSING"

    files = []
    for p, url, note in [
        (wti_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILWTICO", "WTI spot"),
        (walcl_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL", "Fed total assets"),
        (t10yie_raw, "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10YIE", t10_note),
        (wti_panel, "derived", "lag +1d panel"),
        (walcl_panel, "derived", "lag +2d panel with wow_pct"),
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
        "schema": "v8_wti_walcl_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": "post_COT_size_kill_new_exo_acquire; no Model0 by acquire",
        "status": "ACQUISITION_EXECUTED",
        "banned_this_session": [
            "T10YIE_as_RR2_zgate_twin_of_D2",
            "HY_OAS_MOVE_DTWEX_vix_sibling",
            "COT_z_or_size_retune",
        ],
        "files": files,
        "panel_sha256": {
            "fred_wti_dcoilwtico_d1_v1.csv": sha256_file(wti_panel),
            "fred_walcl_wow_w1_v1.csv": sha256_file(walcl_panel),
        },
    }
    out = MANIFESTS / "20260714_WTI_WALCL_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(out), "panels": manifest["panel_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
