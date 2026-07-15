#!/usr/bin/env python3
"""Acquire/freeze Yahoo UUP TW-USD ETF + FRED DTWEXBGS dollar TWI (W27).

Authority: Owner HARD PIVOT W27 — post W26 credit+MOVE ALL_KILL.
UUP was SHA-frozen spare in W26; promote to primary panel + probe.
DTWEXBGS = Trade Weighted U.S. Dollar Index: Broad, Goods (Fed/FRED).

FORBIDDEN densify: commodity→AUD ToT · credit-MOVE (HYG/LQD/^MOVE) ·
VIXCLS equity-vol twin · W1–W26 OHLC densify · FVG / R-series.

Lag: daily close → available_at = observation_date + 1 calendar day.
No Model0 by acquire alone. ChatGPT login wall remains Owner-parallel only.

Mechanisms:
  UUP↑ / DTWEXBGS↑ → USD strength → short AUDUSD displace (invert risk-on).
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_CR = HERE / "raw" / "credit"
RAW_USD = HERE / "raw" / "usd_twi"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (PANEL, MANIFESTS, CONTRACTS, RAW_USD):
    p.mkdir(parents=True, exist_ok=True)

ACQUIRED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
UA = "TradingEAMT5Research/1.0 (personal; dollar-TWI research; contact: local)"
FRED_DTWEXBGS = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS"


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


def load_fred_csv(path: Path, value_col: str) -> list[tuple[date, float]]:
    out: list[tuple[date, float]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            raw = (row.get(value_col) or "").strip()
            if not raw or raw.upper() == ".":
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            if val <= 0 or math.isnan(val):
                continue
            out.append((date.fromisoformat(row["observation_date"]), val))
    out.sort(key=lambda x: x[0])
    return out


def write_panel(name: str, rows: list[dict], fields: list[str]) -> Path:
    path = PANEL / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def fetch_fred(url: str, out: Path) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = resp.read()
        out.write_bytes(body)
        return {
            "result": "OK",
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest().upper(),
            "path": str(out),
        }
    except Exception as e:  # noqa: BLE001
        return {"result": "ERROR", "error": f"{type(e).__name__}: {e}"}


def main() -> None:
    uup_raw = RAW_CR / "yahoo_uup_chart.json"
    assert uup_raw.is_file(), f"missing W26 spare UUP raw: {uup_raw}"

    dtwex_raw = RAW_USD / "fred_dtwexbgs.csv"
    dtwex_fetch = fetch_fred(FRED_DTWEXBGS, dtwex_raw)

    uup = load_yahoo_closes(uup_raw)
    assert len(uup) >= 200, f"UUP too short n={len(uup)}"

    uup_rows = []
    for obs, px in uup:
        avail = obs + timedelta(days=1)
        uup_rows.append(
            {
                "observation_date": obs.isoformat(),
                "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                "uup_close": f"{px:.6f}",
            }
        )
    uup_panel = write_panel(
        "yahoo_uup_twusd_d1_v1.csv",
        uup_rows,
        ["observation_date", "available_at_utc", "uup_close"],
    )

    dtwex_ok = dtwex_fetch.get("result") == "OK" and dtwex_raw.is_file()
    dtwex_rows: list[dict] = []
    dtwex_panel = None
    dtwex_series: list[tuple[date, float]] = []
    if dtwex_ok:
        dtwex_series = load_fred_csv(dtwex_raw, "DTWEXBGS")
        if len(dtwex_series) < 200:
            dtwex_ok = False
        else:
            for obs, px in dtwex_series:
                avail = obs + timedelta(days=1)
                dtwex_rows.append(
                    {
                        "observation_date": obs.isoformat(),
                        "available_at_utc": f"{avail.isoformat()}T00:00:00Z",
                        "dtwexbgs_close": f"{px:.6f}",
                    }
                )
            dtwex_panel = write_panel(
                "fred_dtwexbgs_d1_v1.csv",
                dtwex_rows,
                ["observation_date", "available_at_utc", "dtwexbgs_close"],
            )

    series = [
        {
            "id": "UUP_TWUSD_ETF",
            "panel": "yahoo_uup_twusd_d1_v1.csv",
            "source": "Yahoo Finance chart UUP daily close (Invesco DB USD Index Bullish)",
            "lag_rule": "available_at = observation_date + 1 calendar day",
            "rationale": (
                "Trade-weighted USD ETF proxy. UUP↑ → USD strength → short AUDUSD "
                "H1 displace (invert). ≠ commodity ToT; ≠ credit-MOVE densify; "
                "Owner W27 promote of W26 spare."
            ),
            "not_commodity_tot_clone": True,
            "not_credit_move_densify": True,
            "not_vixcls_retune": True,
            "owner_authorized_w27": True,
            "w26_spare_promoted": True,
        }
    ]
    unavailable = []
    if dtwex_ok and dtwex_panel is not None:
        series.append(
            {
                "id": "DTWEXBGS_BROAD_GOODS_TWI",
                "panel": "fred_dtwexbgs_d1_v1.csv",
                "source": "FRED DTWEXBGS Trade Weighted U.S. Dollar Index: Broad, Goods",
                "lag_rule": "available_at = observation_date + 1 calendar day",
                "rationale": (
                    "Official Fed broad-goods dollar TWI. DTWEX↑ → USD strength → "
                    "short AUDUSD (invert). Independent public surface vs UUP ETF; "
                    "≠ VIX densify twin; ≠ credit-MOVE; Owner W27 dollar-TWI reopen."
                ),
                "not_vix_sibling_shopping": True,
                "not_credit_move_densify": True,
                "not_commodity_tot_clone": True,
                "owner_authorized_w27": True,
            }
        )
    else:
        unavailable.append(
            {
                "id": "DTWEXBGS",
                "reason": dtwex_fetch.get("error")
                or f"rows={len(dtwex_series)} fetch={dtwex_fetch.get('result')}",
            }
        )

    contract = {
        "schema": "exo_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "series": series,
        "unavailable_this_pass": unavailable,
        "banned": [
            "HYG_LQD_credit_z_densify",
            "MOVE_bondvol_z_densify",
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
            "W1_W26_OHLC_densify",
            "commodity_yahoo_aud_tot_clones",
            "invent_spreads",
        ],
    }
    contract_path = CONTRACTS / "20260715_UUP_DTWEX_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    files = [
        {
            "name": uup_raw.name,
            "bytes": uup_raw.stat().st_size,
            "sha256": sha256_file(uup_raw),
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/UUP",
            "note": "UUP TW-USD ETF (W26 spare → W27 primary)",
            "path": str(uup_raw),
        },
        {
            "name": uup_panel.name,
            "bytes": uup_panel.stat().st_size,
            "sha256": sha256_file(uup_panel),
            "source_url": "derived",
            "note": "UUP lag +1d panel",
            "path": str(uup_panel),
        },
        {
            "name": contract_path.name,
            "bytes": contract_path.stat().st_size,
            "sha256": sha256_file(contract_path),
            "source_url": "derived",
            "note": "lag contract",
            "path": str(contract_path),
        },
    ]
    if dtwex_ok and dtwex_panel is not None:
        files.insert(
            1,
            {
                "name": dtwex_raw.name,
                "bytes": dtwex_raw.stat().st_size,
                "sha256": sha256_file(dtwex_raw),
                "source_url": FRED_DTWEXBGS,
                "note": "FRED DTWEXBGS broad-goods dollar TWI",
                "path": str(dtwex_raw),
            },
        )
        files.insert(
            2,
            {
                "name": dtwex_panel.name,
                "bytes": dtwex_panel.stat().st_size,
                "sha256": sha256_file(dtwex_panel),
                "source_url": "derived",
                "note": "DTWEXBGS lag +1d panel",
                "path": str(dtwex_panel),
            },
        )

    panel_sha = {"yahoo_uup_twusd_d1_v1.csv": sha256_file(uup_panel)}
    row_counts = {"uup": len(uup_rows)}
    if dtwex_ok and dtwex_panel is not None:
        panel_sha["fred_dtwexbgs_d1_v1.csv"] = sha256_file(dtwex_panel)
        row_counts["dtwexbgs"] = len(dtwex_rows)

    manifest = {
        "schema": "v8_uup_dtwex_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "Owner_W27_HARD_PIVOT_dollar_TWI_UUP_DTWEX_after_W26_credit_MOVE_ALL_KILL; "
            "ChatGPT login wall parallel; no Model0 by acquire; "
            "FORBIDDEN commodity_ToT + credit_MOVE densify"
        ),
        "status": "ACQUISITION_EXECUTED",
        "surface_class": "dollar_twi_uup + dtwexbgs_broad_goods",
        "dtwex_fetch": dtwex_fetch,
        "banned_this_session": contract["banned"],
        "files": files,
        "panel_sha256": panel_sha,
        "row_counts": row_counts,
        "contract_path": str(contract_path),
        "unavailable": unavailable,
    }
    out = MANIFESTS / "20260715_UUP_DTWEX_ACQUISITION_V1.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "manifest": str(out),
                "panels": manifest["panel_sha256"],
                "rows": manifest["row_counts"],
                "dtwex_ok": dtwex_ok,
                "unavailable": unavailable,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
