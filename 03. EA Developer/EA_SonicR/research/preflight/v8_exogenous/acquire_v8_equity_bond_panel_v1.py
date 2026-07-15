#!/usr/bin/env python3
"""Acquire V8 equity-bond differential panel (key-free public sources).

Authority: Owner autonomous mandate + V8 self-research preflight.
Does NOT authorize ChatGPT, probe registry, prereg, compile, or backtest.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw" / "equity_bond"
MANIFESTS = HERE / "manifests"
RAW.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

UA = {
    "User-Agent": "SonicR-V8-Research/1.0 (lawful public archive; non-commercial)",
    "Accept": "text/csv,application/csv,text/plain,*/*",
}

EXOGENOUS = HERE.parent.parent / "data" / "exogenous"
MANIFEST_NAME = "20260713_V8_EQUITY_BOND_PANEL_ACQUISITION_V1.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return -1
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return 0
    # subtract header if present
    return max(0, len(lines) - 1)


def fetch(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_download(name: str, data: bytes, source_url: str, acquired_at: str) -> dict:
    path = RAW / name
    path.write_bytes(data)
    return {
        "name": name,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "source_url": source_url,
        "status": "OK",
        "acquired_at_utc": acquired_at,
        "path": str(path),
        "approx_data_rows": count_rows(path),
    }


def record_failure(name: str, source_url: str, exc: Exception, acquired_at: str) -> dict:
    return {
        "name": name,
        "bytes": 0,
        "sha256": None,
        "source_url": source_url,
        "status": "FAIL",
        "acquired_at_utc": acquired_at,
        "error": str(exc),
        "path": None,
        "approx_data_rows": 0,
    }


def mirror_or_bind_local(src: Path, dest_name: str, acquired_at: str, duplicate: bool = True) -> dict:
    source_url = f"local_workspace:{src}"
    if not src.is_file():
        return record_failure(dest_name, source_url, FileNotFoundError(str(src)), acquired_at)
    digest = sha256_file(src)
    nbytes = src.stat().st_size
    if duplicate:
        dest = RAW / dest_name
        shutil.copy2(src, dest)
        return {
            "name": dest_name,
            "bytes": nbytes,
            "sha256": digest,
            "source_url": source_url,
            "status": "OK_LOCAL_MIRROR",
            "acquired_at_utc": acquired_at,
            "path": str(dest),
            "source_path": str(src),
            "approx_data_rows": count_rows(dest),
        }
    return {
        "name": dest_name,
        "bytes": nbytes,
        "sha256": digest,
        "source_url": source_url,
        "status": "OK_LOCAL_BIND",
        "acquired_at_utc": acquired_at,
        "path": str(src),
        "source_path": str(src),
        "approx_data_rows": count_rows(src),
    }


def main() -> int:
    acquired_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    errors: list[str] = []

    # 1) US Treasury daily yield curve 2018-2026
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
            if len(data) < 80 or b"404" in data[:300].lower():
                raise RuntimeError(f"short_or_error_body bytes={len(data)}")
            rows.append(save_download(name, data, url, acquired_at))
            print(f"OK {name} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            rows.append(record_failure(name, url, exc, acquired_at))
            print(f"FAIL {name}: {exc}")

    # 2) ECB AAA yield curve selected maturities
    for tenor in ("SR_10Y", "SR_2Y"):
        name = f"ecb_aaa_yc_{tenor.lower()}.csv"
        url = (
            "https://data-api.ecb.europa.eu/service/data/YC/"
            f"B.U2.EUR.4F.G_N_A.SV_C_YM.{tenor}?format=csvdata"
        )
        try:
            data = fetch(url)
            if len(data) < 80:
                raise RuntimeError(f"short_body bytes={len(data)}")
            rows.append(save_download(name, data, url, acquired_at))
            print(f"OK {name} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            rows.append(record_failure(name, url, exc, acquired_at))
            print(f"FAIL {name}: {exc}")

    # 3) Equity risk / VIX / SP500 via FRED; Stooq fallback for SPX
    fred_targets = [
        ("fred_vixcls.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS"),
        ("fred_sp500.csv", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"),
    ]
    fred_sp500_ok = False
    for name, url in fred_targets:
        try:
            data = fetch(url)
            if len(data) < 80 or b"<html" in data[:200].lower():
                raise RuntimeError(f"blocked_or_html bytes={len(data)}")
            rows.append(save_download(name, data, url, acquired_at))
            print(f"OK {name} bytes={len(data)}")
            if name == "fred_sp500.csv":
                fred_sp500_ok = True
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}:{exc}")
            rows.append(record_failure(name, url, exc, acquired_at))
            print(f"FAIL {name}: {exc}")

    if not fred_sp500_ok:
        stooq_name = "stooq_spx.csv"
        stooq_url = "https://stooq.com/q/d/l/?s=^spx&i=d"
        try:
            data = fetch(stooq_url)
            if len(data) < 80:
                raise RuntimeError(f"short_body bytes={len(data)}")
            rows.append(save_download(stooq_name, data, stooq_url, acquired_at))
            print(f"OK {stooq_name} bytes={len(data)}")
            # remove FAIL for fred_sp500 from hard error list if stooq ok
            errors = [e for e in errors if not e.startswith("fred_sp500.csv:")]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{stooq_name}:{exc}")
            rows.append(record_failure(stooq_name, stooq_url, exc, acquired_at))
            print(f"FAIL {stooq_name}: {exc}")

    # 4) Bind/mirror existing DGS10 / DGS2
    for src_name, dest_name in (
        ("us_dgs10_DGS10.csv", "mirror_us_dgs10_DGS10.csv"),
        ("us_dgs2_DGS2.csv", "mirror_us_dgs2_DGS2.csv"),
    ):
        src = EXOGENOUS / src_name
        try:
            row = mirror_or_bind_local(src, dest_name, acquired_at, duplicate=True)
            rows.append(row)
            if row["status"].startswith("OK"):
                print(f"OK {dest_name} bytes={row['bytes']}")
            else:
                errors.append(f"{dest_name}:{row.get('error')}")
                print(f"FAIL {dest_name}: {row.get('error')}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{dest_name}:{exc}")
            rows.append(record_failure(dest_name, f"local_workspace:{src}", exc, acquired_at))
            print(f"FAIL {dest_name}: {exc}")

    ok_count = sum(1 for r in rows if str(r.get("status", "")).startswith("OK"))
    fail_count = sum(1 for r in rows if r.get("status") == "FAIL")
    manifest = {
        "schema": "v8_equity_bond_panel_acquisition.v1",
        "created_at_utc": acquired_at,
        "authority": (
            "Owner autonomous mandate 2026-07-13; equity-bond panel acquisition/"
            "hash-bind only; NO ChatGPT; NO git; NO probe/registry/prereg/compile/backtest"
        ),
        "status": "ACQUISITION_PARTIAL" if fail_count else "ACQUISITION_EXECUTED",
        "raw_dir": str(RAW),
        "files": rows,
        "summary": {
            "file_count": len(rows),
            "ok_count": ok_count,
            "fail_count": fail_count,
            "errors": errors,
        },
    }
    out = MANIFESTS / MANIFEST_NAME
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"MANIFEST {out}")
    print(f"STATUS {manifest['status']} ok={ok_count} fail={fail_count}")
    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
