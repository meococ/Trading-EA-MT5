#!/usr/bin/env python3
"""Build lagged US bill-slope z panel CSV for EA_UsBillSlopeBasket.

Frozen contract:
  03. EA Developer/EA_SonicR/research/preflight/v8_exogenous/20260713_V8_USBILL_SLOPE_USD_BASKET_PROBE_CONTRACT_V1.md

Output columns (ASCII CSV for MQL5 FileOpen CSV):
  available_at,obs_date,slope,z,abs_z_gate
where available_at = obs_date + 1 calendar day (already lagged).
z uses prior 60 available slope obs (exclude t), need >=40.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

WORKSPACE = Path(r"d:\Trading EA MT5")
EA_DIR = WORKSPACE / "03. EA Developer" / "EA_UsBillSlopeBasket"
RAW = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "v8_exogenous"
    / "raw"
)
OUT_CSV = EA_DIR / "usbill_slope_z_d1.csv"
OUT_MANIFEST = EA_DIR / "usbill_slope_z_d1_build_manifest.json"

Z_LOOKBACK = 60
Z_MIN_OBS = 40
Z_THRESH = 0.75
MAX_GAP_DAYS = 3


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def parse_ymd(s: str) -> date:
    s = s.strip()
    if "/" in s:
        m, d, y = [int(x) for x in s.split("/")[:3]]
        return date(y, m, d)
    return date.fromisoformat(s.replace(".", "-")[:10])


def load_bill_slope() -> tuple[dict[date, float], str, list[dict]]:
    long_keys = ("26 WEEKS COUPON EQUIVALENT", "26 WEEKS BANK DISCOUNT")
    short_keys = ("4 WEEKS COUPON EQUIVALENT", "4 WEEKS BANK DISCOUNT")
    fallback_long = ("13 WEEKS COUPON EQUIVALENT", "13 WEEKS BANK DISCOUNT")
    slopes: dict[date, float] = {}
    used_primary = 0
    used_fallback = 0
    file_meta: list[dict] = []

    for year in range(2018, 2027):
        path = RAW / f"us_treasury_bill_rates_{year}.csv"
        if not path.is_file():
            continue
        file_meta.append(
            {
                "path": str(path.relative_to(WORKSPACE)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
        with path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                raw_d = row.get("Date") or row.get("date")
                if not raw_d:
                    continue
                try:
                    d = parse_ymd(raw_d)
                except Exception:
                    continue

                def first_float(keys: tuple[str, ...]) -> float | None:
                    for k in keys:
                        if k in row and row[k] not in (None, "", "N/A", "NA"):
                            try:
                                v = float(row[k])
                            except ValueError:
                                continue
                            if math.isfinite(v):
                                return v
                    return None

                short_v = first_float(short_keys)
                long_v = first_float(long_keys)
                if long_v is None:
                    long_v = first_float(fallback_long)
                    if long_v is not None and short_v is not None:
                        used_fallback += 1
                elif short_v is not None:
                    used_primary += 1
                if short_v is None or long_v is None:
                    continue
                slopes[d] = long_v - short_v

    label = "26W-4W" if used_primary >= used_fallback else "13W-4W_FALLBACK_DOMINANT"
    if used_primary == 0 and used_fallback > 0:
        label = "13W-4W_ONLY"
    return slopes, label, file_meta


def build_z(slope_avail: dict[date, float]) -> dict[date, float]:
    dates = sorted(slope_avail)
    zmap: dict[date, float] = {}
    for i, d in enumerate(dates):
        window: list[float] = []
        j = i - 1
        while j >= 0 and len(window) < Z_LOOKBACK:
            window.append(slope_avail[dates[j]])
            j -= 1
        if len(window) < Z_MIN_OBS:
            continue
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        if var <= 0:
            continue
        zmap[d] = (slope_avail[d] - mean) / math.sqrt(var)
    return zmap


def main() -> int:
    EA_DIR.mkdir(parents=True, exist_ok=True)
    slopes, tenor, file_meta = load_bill_slope()
    if not slopes:
        raise SystemExit("no bill slope rows")

    slope_avail = {d + timedelta(days=1): v for d, v in slopes.items()}
    # Map available_at -> obs_date
    avail_to_obs = {d + timedelta(days=1): d for d in slopes}
    zmap = build_z(slope_avail)

    rows = []
    for avail in sorted(zmap):
        rows.append(
            {
                "available_at": avail.isoformat(),
                "obs_date": avail_to_obs[avail].isoformat(),
                "slope": f"{slope_avail[avail]:.8f}",
                "z": f"{zmap[avail]:.8f}",
                "abs_z_gate": f"{Z_THRESH:.2f}",
            }
        )

    with OUT_CSV.open("w", encoding="ascii", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["available_at", "obs_date", "slope", "z", "abs_z_gate"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)

    # Stage to Common\Files and terminal Files for tester visibility.
    common_files = Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
    common_files.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_CSV, common_files / OUT_CSV.name)

    term_files = Path(
        r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal"
        r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"
    )
    if term_files.is_dir():
        shutil.copy2(OUT_CSV, term_files / OUT_CSV.name)

    manifest = {
        "schema": "usbill_slope_z_d1_build.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "HYP-SR-FX-USBILL-SLOPE-USD-BASKET-001",
        "tenor_label": tenor,
        "z_lookback": Z_LOOKBACK,
        "z_min_obs": Z_MIN_OBS,
        "z_thresh": Z_THRESH,
        "max_gap_days": MAX_GAP_DAYS,
        "lag": "obs_date+1_calendar_day",
        "rows": len(rows),
        "csv_path": str(OUT_CSV.relative_to(WORKSPACE)).replace("\\", "/"),
        "csv_sha256": sha256_file(OUT_CSV),
        "source_bill_files": file_meta,
        "staged_common_files": str(common_files / OUT_CSV.name),
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
