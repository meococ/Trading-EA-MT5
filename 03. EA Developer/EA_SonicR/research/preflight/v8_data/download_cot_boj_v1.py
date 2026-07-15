#!/usr/bin/env python3
"""Acquire CFTC TFF futures-only yearly zips and parse BOJ overnight call HTML."""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research")
OUT = ROOT / "data" / "exogenous"
OUT.mkdir(parents=True, exist_ok=True)
PREFLIGHT = ROOT / "preflight" / "v8_data"
PREFLIGHT.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2018, 2027))
BOJ_HTML = Path(
    r"C:\Users\ADMIN\.cursor\projects\d-Trading-EA-MT5\agent-tools\f35097fe-464b-4f1d-aa2c-2522c8ae15b0.txt"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_cot() -> list[dict]:
    rows = []
    for year in YEARS:
        url = f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
        out = OUT / f"cftc_tff_fut_fin_{year}.zip"
        row = {"year": year, "url": url, "path": str(out)}
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                data = resp.read()
            out.write_bytes(data)
            row.update(
                {
                    "status": "ok",
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            )
            # Extract FX-relevant lines sample after unzip to sibling folder
            extract_dir = OUT / f"cftc_tff_fut_fin_{year}_extracted"
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(out) as zf:
                zf.extractall(extract_dir)
                names = zf.namelist()
            row["extracted_names"] = names
            print(f"OK COT {year} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            row.update({"status": f"fail:{exc}", "bytes": 0, "sha256": ""})
            print(f"FAIL COT {year}: {exc}")
        rows.append(row)
    return rows


def parse_boj_html() -> dict:
    if not BOJ_HTML.exists():
        return {"status": "missing_html_cache", "rows": 0}
    text = BOJ_HTML.read_text(encoding="utf-8", errors="replace")
    # Patterns like 1998/01/05 | 0.49  or markdown table cells
    pairs = re.findall(
        r"(20\d{2}/\d{2}/\d{2}|19\d{2}/\d{2}/\d{2})\s*\|\s*([-+]?\d+(?:\.\d+)?|NA)",
        text,
    )
    if not pairs:
        pairs = re.findall(
            r"(20\d{2}/\d{2}/\d{2}|19\d{2}/\d{2}/\d{2}).{0,40}?([-+]?\d+(?:\.\d+)?|NA)",
            text,
        )
    out_csv = OUT / "jpy_boj_uncollateralized_overnight_call_daily.csv"
    lines = ["observation_date,BOJ_CALL_ON"]
    kept = 0
    for d, v in pairs:
        iso = d.replace("/", "-")
        lines.append(f"{iso},{v}")
        kept += 1
    out_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "status": "ok" if kept else "parse_empty",
        "path": str(out_csv),
        "rows": kept,
        "sha256": sha256_file(out_csv) if kept else "",
        "source_html_cache": str(BOJ_HTML),
        "official_page": "https://www.stat-search.boj.or.jp/ssi/mtshtml/fm01_d_1.html",
        "series_code": "FM01'STRDCLUCON",
        "head": lines[1:4],
        "tail": lines[-3:],
    }


def main() -> int:
    cot = download_cot()
    boj = parse_boj_html()
    print("BOJ", boj.get("status"), "rows", boj.get("rows"))
    receipt = {
        "schema_version": "sonic.exogenous_cot_boj_manifest.v1",
        "date": "2026-07-13",
        "cot_tff": cot,
        "boj_overnight_call": boj,
        "notes": [
            "COT TFF futures-only yearly zips; Tuesday as-of / Friday release lag not yet joined.",
            "BOJ daily call rate parsed from cached official HTML mirror; fail closed if parse_empty.",
            "No probe/outcome join authorized by this acquisition alone.",
        ],
    }
    path = PREFLIGHT / "20260713_COT_BOJ_ACQUISITION_MANIFEST_V1.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print("manifest", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
