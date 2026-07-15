#!/usr/bin/env python3
"""Acquire + freeze V8 overnight RFR / OIS-proxy differential panel.

Authority: Owner self-research (no GPT; no Real login). Lawful public archives.
Builds SOFR−€STR (and SOFR−SONIA companion) with available_at_utc lag.
Optionally attempts MoF JGB 10Y for a separate non-US yield surface.

Does NOT authorize registry / prereg / EA / Model 0 by itself.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
WORKSPACE = RESEARCH.parents[2]
EXO = RESEARCH / "data" / "exogenous"
RAW = HERE / "raw" / "ois_rfr"
PANEL = HERE / "panels"
MANIFESTS = HERE / "manifests"
CONTRACTS = HERE / "contracts"
for p in (RAW, PANEL, MANIFESTS, CONTRACTS):
    p.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "SonicR-V8-Research/1.0 (lawful public archive; non-commercial)"}
ACQUIRED_AT = datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fetch(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_raw(name: str, data: bytes, source_url: str, note: str = "") -> dict:
    path = RAW / name
    path.write_bytes(data)
    return {
        "name": name,
        "status": "OK",
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "source_url": source_url,
        "note": note,
        "relative_path": str(path.relative_to(HERE)).replace("\\", "/"),
    }


def copy_existing(src: Path, name: str, source_url: str, note: str) -> dict:
    if not src.is_file():
        return {
            "name": name,
            "status": "MISSING",
            "source_url": source_url,
            "note": note,
            "expected_src": str(src),
        }
    data = src.read_bytes()
    return save_raw(name, data, source_url, note=f"copied_from_workspace; {note}")


def load_two_col_csv(path: Path, date_key: str | None = None, value_key: str | None = None) -> dict[date, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    if not fieldnames:
        return {}
    dk = date_key or fieldnames[0]
    vk = value_key or fieldnames[1]
    out: dict[date, float] = {}
    for row in reader:
        ds = (row.get(dk) or "").strip()
        vs = (row.get(vk) or "").strip()
        if not ds or not vs or vs.upper() in {".", "NA", "N/A"}:
            continue
        try:
            d = date.fromisoformat(ds.replace(".", "-")[:10])
            out[d] = float(vs)
        except ValueError:
            continue
    return out


def load_ecb_estr(path: Path) -> dict[date, float]:
    """ECB SDMX csvdata for €STR if present; else two-col FRED format."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if "TIME_PERIOD" in text and "OBS_VALUE" in text:
        out: dict[date, float] = {}
        for row in csv.DictReader(io.StringIO(text)):
            tp = (row.get("TIME_PERIOD") or "").strip()
            ov = (row.get("OBS_VALUE") or "").strip()
            if not tp or not ov:
                continue
            try:
                out[date.fromisoformat(tp[:10])] = float(ov)
            except ValueError:
                continue
        return out
    return load_two_col_csv(path)


def build_diff_panel(
    name: str,
    left: dict[date, float],
    right: dict[date, float],
    left_col: str,
    right_col: str,
    diff_col: str,
) -> tuple[Path, dict]:
    dates = sorted(set(left) & set(right))
    path = PANEL / name
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "observation_date",
                "available_at_utc",
                left_col,
                right_col,
                diff_col,
            ]
        )
        for d in dates:
            avail = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
            w.writerow(
                [
                    d.isoformat(),
                    avail.strftime("%Y-%m-%dT00:00:00Z"),
                    f"{left[d]:.6f}",
                    f"{right[d]:.6f}",
                    f"{(left[d] - right[d]):.6f}",
                ]
            )
    meta = {
        "path": str(path.relative_to(WORKSPACE)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "joined_days": len(dates),
        "first_obs": dates[0].isoformat() if dates else None,
        "last_obs": dates[-1].isoformat() if dates else None,
        "lag": "observation_date+1_calendar_day_00Z",
        "diff_col": diff_col,
    }
    return path, meta


def try_fetch_refresh() -> list[dict]:
    """Best-effort official refresh; fail soft if blocked."""
    attempts: list[dict] = []
    targets = [
        (
            "nyfed_sofr_avg.csv",
            "https://markets.newyorkfed.org/api/rates/all/search.json?startDate=2018-01-01&endDate=2026-07-13&type=rate",
            "NY Fed markets API SOFR search JSON (may 403)",
        ),
        (
            "ecb_estr_sdmx.csv",
            "https://data-api.ecb.europa.eu/service/data/EST/B.EU000A2X2A25.WT?format=csvdata&startPeriod=2019-10-01",
            "ECB SDMX €STR volume-weighted trimmed mean",
        ),
        (
            "mof_jgb_current.csv",
            "https://www.mof.go.jp/english/jgbs/reference/interest_rate/jgbcme.csv",
            "MoF JGB reference yields (English CSV)",
        ),
        (
            "mof_jgb_historical.csv",
            "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
            "MoF JGB historical all tenors CSV",
        ),
    ]
    for name, url, note in targets:
        try:
            data = fetch(url)
            # Reject obvious HTML error pages
            head = data[:200].lstrip().lower()
            if head.startswith(b"<!doctype") or head.startswith(b"<html"):
                attempts.append(
                    {
                        "name": name,
                        "status": "HTML_BLOCKED",
                        "source_url": url,
                        "note": note,
                        "bytes": len(data),
                    }
                )
                continue
            attempts.append(save_raw(name, data, url, note=note))
        except Exception as exc:  # noqa: BLE001 — acquisition fail-soft
            attempts.append(
                {
                    "name": name,
                    "status": "FETCH_FAIL",
                    "source_url": url,
                    "note": note,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return attempts


def _parse_mof_date(ds: str) -> date | None:
    """Parse MoF English YYYY/M/D or Japanese-era S/H/R/T/M dates."""
    import re

    ds = ds.strip().strip('"')
    if not ds:
        return None
    if "/" in ds and ds[0].isdigit():
        y, m, d = ds.replace("-", "/").split("/")[:3]
        return date(int(y), int(m), int(d))
    era_base = {"M": 1867, "T": 1911, "S": 1925, "H": 1988, "R": 2018}
    m = re.match(r"^([MTSHR])(\d+)\.(\d+)\.(\d+)$", ds)
    if not m:
        try:
            return date.fromisoformat(ds[:10])
        except ValueError:
            return None
    return date(
        era_base[m.group(1)] + int(m.group(2)),
        int(m.group(3)),
        int(m.group(4)),
    )


def parse_mof_jgb_10y(path: Path) -> dict[date, float]:
    raw = path.read_bytes()
    text = None
    for enc in ("utf-8", "cp932", "shift_jis"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("latin-1", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return {}
    # English current file: row0 title, row1 Date,1Y,...,10Y
    # Japanese historical: row0 title, row1 基準日,1年,...,10年
    header_idx = 1 if ("Date" in ",".join(rows[0]) or "10Y" not in ",".join(rows[0])) and len(rows) > 2 else 0
    # Prefer the row that looks like a column header
    for i, row in enumerate(rows[:3]):
        joined = ",".join(row)
        if "10Y" in joined or "10年" in joined or (len(row) >= 11 and "1Y" in joined):
            header_idx = i
            break
    header = [h.strip() for h in rows[header_idx]]
    date_idx = 0
    ten_idx = None
    for i, h in enumerate(header):
        hl = h.lower().replace(" ", "")
        if hl in {"10y", "10yr"} or "10年" in h:
            ten_idx = i
        if "date" in hl or "基準日" in h or "日付" in h:
            date_idx = i
    if ten_idx is None and len(header) >= 11:
        ten_idx = 10  # Date + 1Y..9Y + 10Y
    if ten_idx is None:
        return {}
    out: dict[date, float] = {}
    for row in rows[header_idx + 1 :]:
        if len(row) <= max(date_idx, ten_idx):
            continue
        dt = _parse_mof_date(row[date_idx])
        vs = row[ten_idx].strip().strip('"')
        if dt is None or not vs or vs in {"-", ""}:
            continue
        try:
            out[dt] = float(vs)
        except ValueError:
            continue
    return out


def load_us_10y_from_treasury() -> dict[date, float]:
    """Reuse already-frozen Treasury curve files under raw/bond_yields."""
    bond_raw = HERE / "raw" / "bond_yields"
    out: dict[date, float] = {}
    for year in range(2018, 2027):
        path = bond_raw / f"us_treasury_yield_curve_{year}.csv"
        if not path.is_file():
            # also try exogenous_data copy
            alt = (
                RESEARCH
                / "exogenous_data"
                / "v8_public"
                / "rates"
                / f"daily_treasury_yield_curve_{year}.csv"
            )
            path = alt if alt.is_file() else path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for row in csv.DictReader(io.StringIO(text)):
            ds = (row.get("Date") or "").strip()
            v = (row.get("10 Yr") or row.get("10 Yr ") or "").strip()
            if not ds or not v:
                continue
            try:
                m, d, y = ds.split("/")
                out[date(int(y), int(m), int(d))] = float(v)
            except ValueError:
                continue
    return out


def main() -> int:
    sources: list[dict] = []

    # 1) Freeze existing workspace FRED/official mirrors (already used as inputs
    #    to killed *rank* carry, but not as a single-pair OIS z-diff panel).
    sources.append(
        copy_existing(
            EXO / "us_sofr_SOFR.csv",
            "fred_sofr.csv",
            "https://fred.stlouisfed.org/series/SOFR",
            "NY Fed SOFR via FRED mirror already on disk",
        )
    )
    sources.append(
        copy_existing(
            EXO / "eur_estr_ECBESTRVOLWGTTRMDMNRT.csv",
            "fred_estr.csv",
            "https://fred.stlouisfed.org/series/ECBESTRVOLWGTTRMDMNRT",
            "ECB €STR via FRED mirror already on disk",
        )
    )
    sources.append(
        copy_existing(
            EXO / "gbp_sonia_IUDSOIA.csv",
            "fred_sonia.csv",
            "https://fred.stlouisfed.org/series/IUDSOIA",
            "BoE SONIA via FRED mirror already on disk",
        )
    )

    # 2) Best-effort official refresh + MoF JGB
    sources.extend(try_fetch_refresh())

    sofr = load_two_col_csv(RAW / "fred_sofr.csv")
    estr = load_ecb_estr(RAW / "fred_estr.csv")
    # Prefer ECB SDMX refresh if parsed denser/newer
    if (RAW / "ecb_estr_sdmx.csv").is_file():
        estr_sdmx = load_ecb_estr(RAW / "ecb_estr_sdmx.csv")
        if len(estr_sdmx) >= len(estr) * 0.8:
            estr = estr_sdmx
    sonia = load_two_col_csv(RAW / "fred_sonia.csv")

    panels: list[dict] = []
    _, meta_eu = build_diff_panel(
        "us_eu_ois_rfr_diff_d1_v1.csv",
        sofr,
        estr,
        "sofr",
        "estr",
        "diff_sofr_minus_estr",
    )
    panels.append(meta_eu)

    _, meta_uk = build_diff_panel(
        "us_uk_ois_rfr_diff_d1_v1.csv",
        sofr,
        sonia,
        "sofr",
        "sonia",
        "diff_sofr_minus_sonia",
    )
    panels.append(meta_uk)

    # Optional US–JP 10Y if MoF CSV acquired
    jgb_panel = None
    jgb_series: dict[date, float] = {}
    for cand in ("mof_jgb_historical.csv", "mof_jgb_current.csv"):
        p = RAW / cand
        if p.is_file() and any(
            s.get("name") == cand and s.get("status") == "OK" for s in sources
        ):
            jgb_series = parse_mof_jgb_10y(p)
            if jgb_series:
                break
    if jgb_series:
        us10 = load_us_10y_from_treasury()
        _, jgb_panel = build_diff_panel(
            "us_jp_bond_yield_diff_d1_v1.csv",
            us10,
            jgb_series,
            "us_10y",
            "jp_jgb_10y",
            "diff_us_jp_10y",
        )
        panels.append(jgb_panel)

    contract = {
        "schema": "v8_ois_rfr_available_at_utc_contract.v1",
        "created_at_utc": ACQUIRED_AT,
        "join_rule": (
            "FX closed bar may use an OIS/RFR observation only if "
            "bar_close_utc >= available_at_utc. No silent forward-fill > 3 calendar days."
        ),
        "available_at_rule": "observation_date + 1 calendar day 00:00:00Z (conservative vs NY Fed/ECB/BoE next-business-day publish)",
        "series": [
            {
                "series_id": "USD_SOFR",
                "publisher": "NY Fed via FRED SOFR",
                "lag_calendar_days": 1,
            },
            {
                "series_id": "EUR_ESTR",
                "publisher": "ECB €STR via FRED ECBESTRVOLWGTTRMDMNRT (SDMX refresh if OK)",
                "lag_calendar_days": 1,
            },
            {
                "series_id": "GBP_SONIA",
                "publisher": "BoE SONIA via FRED IUDSOIA",
                "lag_calendar_days": 1,
            },
        ],
        "explicit_non_claims": [
            "Not vendor FX forward points / outright forwards curve",
            "Not multi-tenor OIS swap curve (1Y/2Y/5Y/10Y); overnight RFR proxies only",
            "Not QFSI Real cost provenance",
            "Not a rescue of killed weekly/daily/rate-event rank-carry books",
        ],
    }
    contract_path = CONTRACTS / "20260713_V8_OIS_RFR_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    contract_bytes = (json.dumps(contract, indent=2) + "\n").encode("utf-8")
    contract_path.write_bytes(contract_bytes)

    manifest = {
        "schema": "v8_ois_rfr_panel_acquisition.v1",
        "created_at_utc": ACQUIRED_AT,
        "authority": "Owner unlimited-GOAL self-research; no ChatGPT; no Real login",
        "status": "ACQUIRED_HASH_BOUND",
        "sources": sources,
        "panels": panels,
        "lag_contract": {
            "path": str(contract_path.relative_to(WORKSPACE)).replace("\\", "/"),
            "sha256": sha256_bytes(contract_bytes),
        },
        "jgb_acquired": bool(jgb_panel),
        "primary_probe_surface": "us_eu_ois_rfr_diff_d1_v1.csv",
        "companion_surface": "us_uk_ois_rfr_diff_d1_v1.csv",
        "not_claimed": contract["explicit_non_claims"],
    }
    man_path = MANIFESTS / "20260713_V8_OIS_RFR_PANEL_ACQUISITION_V1.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "manifest": str(man_path),
                "panels": panels,
                "jgb_acquired": bool(jgb_panel),
                "source_statuses": [
                    {"name": s.get("name"), "status": s.get("status")} for s in sources
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
