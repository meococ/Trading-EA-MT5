#!/usr/bin/env python3
"""Build carry_rates_d1.csv (date,usd,eur,gbp,jpy) for EA_CarryPublicRates.

Merges existing V8 exogenous / FRED mirrors under preflight/v8_exogenous/raw
and research/data/exogenous into one daily panel.

Prefer:
  USD: us_fed_funds_DFF.csv (fallback: 13W T-bill coupon equivalent)
  EUR: eur_ecb_deposit_ECBDFR.csv (fallback: ecb_dfr_daily.csv)
  GBP: boe_bank_rate.csv (fallback: gbp_sonia_IUDSOIA.csv)
  JPY: jpy_boj_uncollateralized_overnight_call_daily.csv (forward-fill NA)

Writes:
  03. EA Developer/EA_CarryPublicRates/carry_rates_d1.csv
  MT5 MQL5/Files/carry_rates_d1.csv when terminal data path is known
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Trading EA MT5
EA_DIR = Path(__file__).resolve().parent
RAW = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "v8_exogenous" / "raw"
EXO = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "data" / "exogenous"
MT5_FILES = Path(
    r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal"
    r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"
)
COMMON_FILES = Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_ymd(s: str) -> date | None:
    s = (s or "").strip().strip('"')
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%m/%d/%Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # BoE style sometimes: "02 Jan 2018"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})$", s)
    if m:
        try:
            return datetime.strptime(s, "%d %b %Y").date()
        except ValueError:
            return None
    return None


def load_two_col(path: Path, date_key_hints: list[str], value_key_hints: list[str]) -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return out
        fields = [c.strip() for c in reader.fieldnames]
        lower = {c.lower(): c for c in fields}

        def pick(hints: list[str]) -> str | None:
            for h in hints:
                if h.lower() in lower:
                    return lower[h.lower()]
            # positional fallback for simple 2-col files
            if len(fields) >= 2:
                return None
            return None

        dcol = pick(date_key_hints)
        vcol = pick(value_key_hints)
        if dcol is None and len(fields) >= 1:
            dcol = fields[0]
        if vcol is None and len(fields) >= 2:
            vcol = fields[1]
        if dcol is None or vcol is None:
            return out
        for row in reader:
            d = parse_ymd(str(row.get(dcol, "")))
            raw = str(row.get(vcol, "")).strip().strip('"')
            if d is None or raw.upper() in {"", "NA", "N/A", "."}:
                continue
            try:
                out[d] = float(raw)
            except ValueError:
                continue
    return out


def load_ecb_raw(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = parse_ymd(str(row.get("TIME_PERIOD", "")))
            raw = str(row.get("OBS_VALUE", "")).strip()
            if d is None or not raw:
                continue
            try:
                out[d] = float(raw)
            except ValueError:
                continue
    return out


def load_tbill_13w(raw_dir: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    for year in range(2018, 2027):
        path = raw_dir / f"us_treasury_bill_rates_{year}.csv"
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = parse_ymd(str(row.get("Date", "")))
                # Prefer 13 WEEKS COUPON EQUIVALENT
                raw = None
                for key in row:
                    k = key.strip().upper()
                    if "13 WEEKS" in k and "COUPON" in k:
                        raw = str(row[key]).strip().strip('"')
                        break
                if d is None or not raw:
                    continue
                try:
                    out[d] = float(raw)
                except ValueError:
                    continue
    return out


def ffill(series: dict[date, float], days: list[date]) -> dict[date, float]:
    out: dict[date, float] = {}
    last: float | None = None
    for d in days:
        if d in series:
            last = series[d]
        if last is not None:
            out[d] = last
    return out


def main() -> int:
    usd = load_two_col(
        EXO / "us_fed_funds_DFF.csv",
        ["observation_date", "date"],
        ["DFF", "value"],
    )
    if not usd:
        usd = load_tbill_13w(RAW)

    eur = load_two_col(
        EXO / "eur_ecb_deposit_ECBDFR.csv",
        ["observation_date", "date"],
        ["ECBDFR", "value"],
    )
    if not eur:
        eur = load_ecb_raw(RAW / "ecb_dfr_daily.csv")

    gbp = load_two_col(
        RAW / "boe_bank_rate.csv",
        ["DATE", "date", "observation_date"],
        ["IUDBEDR", "value", "bank_rate"],
    )
    if not gbp:
        gbp = load_two_col(
            EXO / "gbp_sonia_IUDSOIA.csv",
            ["observation_date", "date"],
            ["IUDSOIA", "value"],
        )

    jpy = load_two_col(
        RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv",
        ["observation_date", "date"],
        ["BOJ_CALL_ON", "value"],
    )

    if not (usd and eur and gbp and jpy):
        missing = [
            name
            for name, s in (("usd", usd), ("eur", eur), ("gbp", gbp), ("jpy", jpy))
            if not s
        ]
        raise SystemExit(f"Missing rate legs after merge: {missing}")

    start = max(min(usd), min(eur), min(gbp), min(jpy))
    end = min(max(usd), max(eur), max(gbp), max(jpy))
    all_days = []
    cur = start
    from datetime import timedelta

    while cur <= end:
        all_days.append(cur)
        cur += timedelta(days=1)

    usd_f = ffill(usd, all_days)
    eur_f = ffill(eur, all_days)
    gbp_f = ffill(gbp, all_days)
    jpy_f = ffill(jpy, all_days)

    rows: list[tuple[date, float, float, float, float]] = []
    for d in all_days:
        if d in usd_f and d in eur_f and d in gbp_f and d in jpy_f:
            rows.append((d, usd_f[d], eur_f[d], gbp_f[d], jpy_f[d]))

    if len(rows) < 100:
        raise SystemExit(f"Panel too short: {len(rows)} rows")

    out_paths = [EA_DIR / "carry_rates_d1.csv"]
    if MT5_FILES.parent.is_dir():
        MT5_FILES.mkdir(parents=True, exist_ok=True)
        out_paths.append(MT5_FILES / "carry_rates_d1.csv")
    if COMMON_FILES.parent.is_dir():
        COMMON_FILES.mkdir(parents=True, exist_ok=True)
        out_paths.append(COMMON_FILES / "carry_rates_d1.csv")

    header = ["date", "usd", "eur", "gbp", "jpy"]
    for path in out_paths:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for d, u, e, g, j in rows:
                w.writerow([d.isoformat(), f"{u:.6f}", f"{e:.6f}", f"{g:.6f}", f"{j:.6f}"])

    primary = out_paths[0]
    manifest = {
        "schema": "carry_rates_d1_build.v1",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
        "start": rows[0][0].isoformat(),
        "end": rows[-1][0].isoformat(),
        "outputs": [
            {"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in out_paths
        ],
        "sources": {
            "usd_rows": len(usd),
            "eur_rows": len(eur),
            "gbp_rows": len(gbp),
            "jpy_rows": len(jpy),
        },
    }
    man_path = EA_DIR / "carry_rates_d1_build_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"PRIMARY_SHA256={sha256_file(primary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
