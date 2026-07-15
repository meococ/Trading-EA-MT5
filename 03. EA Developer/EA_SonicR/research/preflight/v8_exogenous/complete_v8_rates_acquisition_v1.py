#!/usr/bin/env python3
"""Complete V8 public short-rate acquisition (key-free where possible).

Authority: Owner autonomous mandate + V8 rates-only data contract.
Does NOT authorize probe / registry / prereg / compile / backtest.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
MANIFESTS = HERE / "manifests"
RAW.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "SonicR-V8-Research/1.0 (lawful public archive; non-commercial)"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        "path": str(path.relative_to(HERE.parent.parent)),
    }


def main() -> int:
    rows: list[dict] = []
    errors: list[str] = []

    # ECB deposit facility rate (daily) — official SDMX, no key
    ecb_url = (
        "https://data-api.ecb.europa.eu/service/data/FM/"
        "D.U2.EUR.4F.KR.DFR.LEV?format=csvdata"
    )
    try:
        rows.append(save_raw("ecb_dfr_daily.csv", fetch(ecb_url), ecb_url))
        print("OK ecb_dfr_daily.csv")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ecb_dfr:{exc}")
        print(f"FAIL ecb_dfr: {exc}")

    # US Treasury bill rates by year (key-free official CSV)
    for year in range(2018, 2027):
        name = f"us_treasury_bill_rates_{year}.csv"
        url = (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv/"
            f"{year}/all?type=daily_treasury_bill_rates"
            f"&field_tdr_date_value={year}&page&_format=csv"
        )
        try:
            data = fetch(url)
            if len(data) < 50 or b"404" in data[:200].lower():
                raise RuntimeError(f"short_or_error_body bytes={len(data)}")
            rows.append(save_raw(name, data, url))
            print(f"OK {name} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            print(f"FAIL {name}: {exc}")

    # BoE Bank Rate history page export (HTML table may fail; record attempt)
    boe_url = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"
    try:
        data = fetch(boe_url)
        rows.append(save_raw("boe_bank_rate_page.html", data, boe_url))
        print(f"OK boe_bank_rate_page.html bytes={len(data)}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"boe:{exc}")
        print(f"FAIL boe: {exc}")

    # Verify FRED mirror if present under research/data/exogenous
    fred_dir = HERE.parent.parent / "data" / "exogenous"
    fred_files = []
    if fred_dir.is_dir():
        for p in sorted(fred_dir.glob("*.csv")):
            data = p.read_bytes()
            fred_files.append(
                {
                    "name": p.name,
                    "status": "OK_LOCAL",
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                    "source_url": "local_fred_mirror",
                    "path": str(p.relative_to(HERE.parent.parent)),
                }
            )
            print(f"LOCAL {p.name} bytes={len(data)}")

    manifest = {
        "schema": "v8_exogenous_acquisition_manifest.v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": (
            "Owner autonomous mandate 2026-07-13 + V8 rates-only contract; "
            "acquisition/hash only; NO probe/registry/prereg/compile/backtest"
        ),
        "status": "ACQUISITION_PARTIAL" if errors else "ACQUISITION_EXECUTED",
        "v8_scope_note": (
            "Rates/policy/money-market only for V8. COT downloads are out of "
            "V8 packet scope even if stored elsewhere."
        ),
        "join_rule_note": (
            "Do not join into probes until coordinator freezes available_at_utc "
            "rules after Deep Research V8 Owner-confirmed submit + local audit."
        ),
        "errors": errors,
        "files": rows,
        "fred_local_mirrors": fred_files,
        "authority_flags": {
            "probe_authorized": False,
            "registry_append_authorized": False,
            "prereg_freeze_authorized": False,
            "ea_build_authorized": False,
            "compile_authorized": False,
            "backtest_authorized": False,
            "deep_research_v8_submit_authorized": False,
        },
    }
    out = MANIFESTS / "20260713_V8_EXOGENOUS_ACQUISITION_MANIFEST_V2.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest_written {out}")
    print(f"files_ok={len(rows)} fred_local={len(fred_files)} errors={len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
