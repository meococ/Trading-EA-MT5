#!/usr/bin/env python3
"""Download lawful public FRED rate series for V8 exogenous carry surface."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "exogenous"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERIES = [
    ("DFF", "us_fed_funds"),
    ("ECBDFR", "eur_ecb_deposit"),
    ("IUDSOIA", "gbp_sonia"),
    ("ECBESTRVOLWGTTRMDMNRT", "eur_estr"),
    ("SOFR", "us_sofr"),
    ("IRSTCI01JPM156N", "jpy_call_money_monthly"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    manifest = {
        "schema_version": "sonic.exogenous_fred_manifest.v1",
        "date": "2026-07-13",
        "source": "https://fred.stlouisfed.org/graph/fredgraph.csv",
        "series": [],
    }
    for series_id, name in SERIES:
        out = OUT_DIR / f"{name}_{series_id}.csv"
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        row = {
            "series_id": series_id,
            "name": name,
            "url": url,
            "path": str(out.relative_to(ROOT.parents[2])),
        }
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = resp.read()
            out.write_bytes(data)
            text = data.decode("utf-8", errors="replace")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            row.update(
                {
                    "status": "ok",
                    "bytes": len(data),
                    "lines": len(lines),
                    "sha256": sha256_file(out),
                    "head": lines[:3],
                    "tail": lines[-2:],
                }
            )
            print(f"OK {series_id} lines={len(lines)} bytes={len(data)}")
        except Exception as exc:  # noqa: BLE001
            row.update({"status": f"fail:{exc}", "bytes": 0, "lines": 0, "sha256": ""})
            print(f"FAIL {series_id}: {exc}")
        manifest["series"].append(row)

    receipt = Path(__file__).with_name("20260713_FRED_SERIES_MANIFEST_V1.json")
    receipt.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest_written {receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
