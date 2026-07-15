#!/usr/bin/env python3
"""Acquire + freeze V8 public bond-yield differential panel (US + ECB).

Authority: Owner autonomous data-state change after V8 self-research
fail-closed (2026-07-13). Lawful public archives only. No broker login.
Does NOT authorize Model 0 / registry / EA by itself.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "bond_yields"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (RAW, PANEL, MANIFESTS, CONTRACTS):
    p.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "SonicR-V8-Research/1.0 (lawful public archive; non-commercial)"}
ACQUIRED_AT = datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def fetch(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_raw(name: str, data: bytes, source_url: str) -> dict:
    path = RAW / name
    path.write_bytes(data)
    return {
        "name": name,
        "status": "OK",
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "source_url": source_url,
        "relative_path": str(path.relative_to(HERE)).replace("\\", "/"),
    }


def parse_us_date(s: str) -> date:
    m, d, y = s.strip().split("/")
    return date(int(y), int(m), int(d))


def load_us_10y(raw_rows: list[dict]) -> dict[date, float]:
    out: dict[date, float] = {}
    for meta in raw_rows:
        if not meta["name"].startswith("us_treasury_yield_curve_"):
            continue
        text = (RAW / meta["name"]).read_text(encoding="utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            ds = (row.get("Date") or "").strip()
            v = (row.get("10 Yr") or row.get("10 Yr ") or "").strip()
            if not ds or not v:
                continue
            try:
                out[parse_us_date(ds)] = float(v)
            except ValueError:
                continue
    return out


def load_ecb_tenor(filename: str) -> dict[date, float]:
    text = (RAW / filename).read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out: dict[date, float] = {}
    for row in reader:
        tp = (row.get("TIME_PERIOD") or "").strip()
        ov = (row.get("OBS_VALUE") or "").strip()
        if not tp or not ov:
            continue
        try:
            out[date.fromisoformat(tp[:10])] = float(ov)
        except ValueError:
            continue
    return out


def build_panel(us10: dict[date, float], eu10: dict[date, float], eu2: dict[date, float]) -> Path:
    """Frozen join panel: observation_date + available_at_utc + differentials."""
    dates = sorted(set(us10) & set(eu10))
    path = PANEL / "us_eu_bond_yield_diff_d1_v1.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "observation_date",
                "available_at_utc",
                "us_10y",
                "eu_aaa_gov_10y",
                "eu_aaa_gov_2y",
                "diff_us_eu_10y",
                "eu_curve_10y_minus_2y",
            ]
        )
        for d in dates:
            # Conservative: next calendar day 00:00 UTC after observation date.
            avail = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
            eu2v = eu2.get(d)
            row = [
                d.isoformat(),
                avail.strftime("%Y-%m-%dT00:00:00Z"),
                f"{us10[d]:.6f}",
                f"{eu10[d]:.6f}",
                "" if eu2v is None else f"{eu2v:.6f}",
                f"{(us10[d] - eu10[d]):.6f}",
                "" if eu2v is None else f"{(eu10[d] - eu2v):.6f}",
            ]
            w.writerow(row)
    return path


def main() -> int:
    rows: list[dict] = []
    errors: list[str] = []

    # US Treasury daily par yield curve (key-free official CSV)
    for year in range(2018, 2027):
        name = f"us_treasury_yield_curve_{year}.csv"
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv/"
            f"{year}/all?type=daily_treasury_yield_curve"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        try:
            data = fetch(url)
            if len(data) < 80 or b"404" in data[:200].lower():
                raise RuntimeError(f"short_or_error_body bytes={len(data)}")
            rows.append(save_raw(name, data, url))
            print(f"OK {name} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            print(f"FAIL {name}: {exc}")

    # ECB euro-area AAA government spot rates (official SDMX, no key)
    ecb_series = {
        "ecb_yc_aaa_gov_sr_10y.csv": (
            "https://data-api.ecb.europa.eu/service/data/YC/"
            "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?format=csvdata"
        ),
        "ecb_yc_aaa_gov_sr_2y.csv": (
            "https://data-api.ecb.europa.eu/service/data/YC/"
            "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata"
        ),
    }
    for name, url in ecb_series.items():
        try:
            data = fetch(url)
            if len(data) < 200:
                raise RuntimeError(f"short_body bytes={len(data)}")
            rows.append(save_raw(name, data, url))
            print(f"OK {name} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            print(f"FAIL {name}: {exc}")

    ok = [r for r in rows if r.get("status") == "OK"]
    panel_meta = None
    if any(r["name"].startswith("us_treasury_yield_curve_") for r in ok) and any(
        r["name"].startswith("ecb_yc_aaa_gov_sr_10y") for r in ok
    ):
        us10 = load_us_10y(ok)
        eu10 = load_ecb_tenor("ecb_yc_aaa_gov_sr_10y.csv")
        eu2 = (
            load_ecb_tenor("ecb_yc_aaa_gov_sr_2y.csv")
            if (RAW / "ecb_yc_aaa_gov_sr_2y.csv").exists()
            else {}
        )
        panel_path = build_panel(us10, eu10, eu2)
        panel_bytes = panel_path.read_bytes()
        panel_meta = {
            "name": panel_path.name,
            "status": "OK",
            "bytes": len(panel_bytes),
            "sha256": sha256_bytes(panel_bytes),
            "relative_path": str(panel_path.relative_to(HERE)).replace("\\", "/"),
            "joined_observation_days": sum(1 for _ in panel_path.open(encoding="utf-8")) - 1,
            "us_10y_obs": len(us10),
            "eu_10y_obs": len(eu10),
            "eu_2y_obs": len(eu2),
            "lag_rule": (
                "available_at_utc = observation_date + 1 calendar day 00:00Z; "
                "FX closed bar may use row only if bar_close_utc >= available_at_utc"
            ),
        }
        print(
            f"OK panel {panel_path.name} days={panel_meta['joined_observation_days']} "
            f"sha={panel_meta['sha256'][:16]}..."
        )

    contract = {
        "schema": "v8_bond_yield_available_at_utc_contract.v1",
        "status": "FROZEN_CONTRACT / PANEL_READY / NO_MODEL_0",
        "created_at_utc": ACQUIRED_AT,
        "authority": (
            "Owner autonomous data-state change after V8 fail-closed. "
            "Authorizes hash-bound panel + one later offline probe if de-dup clear. "
            "Does not authorize registry/prereg/EA/Model 0 without probe survivor."
        ),
        "join_rule": (
            "FX closed bar may use a bond-yield observation only if "
            "bar_close_utc >= available_at_utc. No silent forward-fill > 3 calendar days."
        ),
        "series": [
            {
                "series_id": "USD_TREASURY_PAR_YIELD_10Y",
                "local_glob": "raw/bond_yields/us_treasury_yield_curve_YYYY.csv",
                "field": "10 Yr",
                "observation_clock": "US Treasury daily par yield curve publish date",
                "publication_lag_rule": (
                    "available_at_utc = observation_date + 1 calendar day 00:00 UTC "
                    "(conservative; do not use same-day for Tokyo/London morning FX)"
                ),
                "license": "https://home.treasury.gov/ (U.S. government public data)",
            },
            {
                "series_id": "EUR_ECB_AAA_GOV_SPOT_10Y",
                "local_file": "raw/bond_yields/ecb_yc_aaa_gov_sr_10y.csv",
                "field": "OBS_VALUE for KEY YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
                "observation_clock": "ECB euro-area AAA government bond spot rate",
                "publication_lag_rule": (
                    "Same conservative next-calendar-day 00:00 UTC availability as US leg "
                    "for differential joins; ECB SDMX TIME_PERIOD is observation date."
                ),
                "license": "https://www.ecb.europa.eu/stats/ (ECB open data)",
            },
            {
                "series_id": "EUR_ECB_AAA_GOV_SPOT_2Y",
                "local_file": "raw/bond_yields/ecb_yc_aaa_gov_sr_2y.csv",
                "field": "OBS_VALUE for KEY YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
                "observation_clock": "ECB euro-area AAA government bond spot rate",
                "publication_lag_rule": "Same as EUR 10Y companion for EU curve slope.",
                "license": "https://www.ecb.europa.eu/stats/ (ECB open data)",
            },
        ],
        "frozen_panel": panel_meta,
        "explicit_non_claims": [
            "Not true FX forwards/OIS (vendor surface still missing)",
            "Not UK gilt / JGB histories (BoE CSV export returned HTML; not frozen)",
            "Not equity-index closes (Stooq JS-blocked; FRED needs API key)",
            "Not QFSI Real cost provenance",
        ],
    }
    contract_path = CONTRACTS / "20260713_V8_BOND_YIELD_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "v8_bond_yield_acquisition_manifest.v1",
        "acquired_at_utc": ACQUIRED_AT,
        "status": "OK" if panel_meta and not errors else ("PARTIAL" if panel_meta else "FAIL"),
        "raw_files": rows,
        "panel": panel_meta,
        "contract_path": str(contract_path.relative_to(HERE)).replace("\\", "/"),
        "contract_sha256": sha256_bytes(contract_path.read_bytes()),
        "errors": errors,
        "qfsi_note": (
            "QFSI Real remains Owner broker-login action "
            "(FivePercentOnline-Real); not blocking this public panel."
        ),
    }
    man_path = MANIFESTS / "20260713_V8_BOND_YIELD_PANEL_ACQUISITION_V1.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(man_path), "status": manifest["status"], "errors": errors}, indent=2))
    return 0 if panel_meta else 1


if __name__ == "__main__":
    raise SystemExit(main())
