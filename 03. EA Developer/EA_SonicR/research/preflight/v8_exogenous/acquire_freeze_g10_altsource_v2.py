#!/usr/bin/env python3
"""G10 overnight/policy alt-source acquire+freeze (post RBA403/BoC404/FRED timeout).

Tries legal public mirrors only. Builds daily panel if ≥AUD+CAD (+USD anchor)
have usable daily rows. Does NOT probe — panel readiness only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
EXO = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight" / "v8_exogenous"
RAW = EXO / "raw" / "g10_overnight"
PANELS = EXO / "panels"
MAN = EXO / "manifests"
CONTRACTS = EXO / "contracts"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"

UA = "TradingEAMT5Research/1.0 (personal; rates research; contact: local)"
TIMEOUT = 45


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def fetch(url: str, out: Path, *, note: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read()
            status = getattr(resp, "status", 200)
            ctype = resp.headers.get("Content-Type", "")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(body)
        return {
            "url": url,
            "note": note,
            "result": "OK",
            "http_status": status,
            "content_type": ctype,
            "path": str(out.relative_to(ROOT)).replace("\\", "/"),
            "bytes": len(body),
            "sha256": sha256_bytes(body),
            "elapsed_s": round(time.time() - t0, 2),
        }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "note": note,
            "result": f"HTTP_{e.code}",
            "http_status": e.code,
            "elapsed_s": round(time.time() - t0, 2),
            "error": str(e.reason),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "url": url,
            "note": note,
            "result": "ERROR",
            "elapsed_s": round(time.time() - t0, 2),
            "error": f"{type(e).__name__}: {e}",
        }


def parse_boc_csv(path: Path) -> dict[date, float]:
    """BoC Valet CSV: observations after header block."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    out: dict[date, float] = {}
    # Find header with date column
    start = 0
    for i, ln in enumerate(lines):
        if ln.lower().startswith("date,") or ln.startswith('"date"') or ln.startswith("d,"):
            start = i
            break
        if re.match(r"^\d{4}-\d{2}-\d{2},", ln):
            start = i
            break
    # Valet CSV often: date,AVG.INTWO then rows
    for ln in lines[start:]:
        ln = ln.strip().strip('"')
        if not ln or ln.lower().startswith("date") or ln.startswith("OBS"):
            # header-ish
            if "date" in ln.lower():
                continue
            continue
        parts = [p.strip().strip('"') for p in ln.split(",")]
        if len(parts) < 2:
            continue
        ds, vs = parts[0], parts[1]
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", ds):
            continue
        if vs in ("", "null", "NA", "."):
            continue
        try:
            out[date.fromisoformat(ds)] = float(vs)
        except ValueError:
            continue
    return out


def parse_boc_json(path: Path, series: str) -> dict[date, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[date, float] = {}
    for obs in data.get("observations", []):
        ds = obs.get("d")
        cell = obs.get(series) or {}
        vs = cell.get("v") if isinstance(cell, dict) else None
        if not ds or vs in (None, "", "null"):
            continue
        try:
            out[date.fromisoformat(ds)] = float(vs)
        except ValueError:
            continue
    return out


def parse_bis_csv(path: Path) -> dict[str, dict[date, float]]:
    """BIS SDMX CSV → {REF_AREA: {date: value}}."""
    text = path.read_text(encoding="utf-8", errors="replace")
    # Detect delimiter
    sample = text[:2000]
    delim = ";" if sample.count(";") > sample.count(",") else ","
    rows = list(csv.DictReader(text.splitlines(), delimiter=delim))
    if not rows:
        return {}
    # Normalize keys
    def pick(row: dict, *cands: str) -> str | None:
        keys = {k.lower(): k for k in row}
        for c in cands:
            if c.lower() in keys:
                return row[keys[c.lower()]]
        # fuzzy
        for lk, ok in keys.items():
            for c in cands:
                if c.lower() in lk:
                    return row[ok]
        return None

    by: dict[str, dict[date, float]] = {}
    for row in rows:
        area = pick(row, "REF_AREA", "REF_AREA:Id", "AREA")
        t = pick(row, "TIME_PERIOD", "TIME", "OBS_DATE")
        v = pick(row, "OBS_VALUE", "OBS_VALUE:Double", "value", "VALUE")
        if not area or not t or v in (None, "", "NA"):
            continue
        # daily like 2020-01-02 or 2020-01
        t = t.strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
            d = date.fromisoformat(t)
        elif re.match(r"^\d{4}-\d{2}$", t):
            # monthly — skip for daily panel
            continue
        else:
            continue
        try:
            fv = float(v)
        except ValueError:
            continue
        by.setdefault(area.upper(), {})[d] = fv
    return by


def parse_fred_csv(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            ds = (row.get("DATE") or row.get("date") or "").strip()
            vs = (row.get("VALUE") or row.get("value") or "").strip()
            if not ds or vs in ("", ".", "NA"):
                continue
            try:
                out[date.fromisoformat(ds)] = float(vs)
            except ValueError:
                continue
    return out


def ff_fill(series: dict[date, float], start: date, end: date) -> dict[date, float]:
    if not series:
        return {}
    keys = sorted(series)
    out: dict[date, float] = {}
    i = 0
    last: float | None = None
    # seed last before start
    for d0, v0 in series.items():
        if d0 < start:
            last = v0
        else:
            break
    d = start
    while d <= end:
        while i < len(keys) and keys[i] <= d:
            last = series[keys[i]]
            i += 1
        if last is not None and d.weekday() < 5:
            out[d] = last
        d = date.fromordinal(d.toordinal() + 1)
    return out


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    PANELS.mkdir(parents=True, exist_ok=True)
    MAN.mkdir(parents=True, exist_ok=True)
    CONTRACTS.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []

    # --- BoC CORRA (correct series AVG.INTWO) ---
    attempts.append(
        fetch(
            "https://www.bankofcanada.ca/valet/observations/AVG.INTWO/csv?start_date=2018-01-01",
            RAW / "boc_corra_avg_intwo.csv",
            note="BoC Valet CORRA AVG.INTWO csv",
        )
    )
    attempts.append(
        fetch(
            "https://www.bankofcanada.ca/valet/observations/AVG.INTWO/json?start_date=2018-01-01",
            RAW / "boc_corra_avg_intwo.json",
            note="BoC Valet CORRA AVG.INTWO json",
        )
    )
    attempts.append(
        fetch(
            "https://www.bankofcanada.ca/valet/observations/V39079/csv?start_date=2018-01-01",
            RAW / "boc_target_overnight_v39079.csv",
            note="BoC target overnight V39079",
        )
    )

    # --- BIS policy rates daily AU+CA+NZ+US+GB+JP+XM+CH ---
    bis_url = (
        "https://stats.bis.org/api/v2/data/BIS,WS_CBPOL,1.0/D.AU+CA+NZ+US+GB+JP+XM+CH"
        "?format=csv&startPeriod=2018-01-01"
    )
    attempts.append(fetch(bis_url, RAW / "bis_cbpol_d_g10.csv", note="BIS WS_CBPOL daily G10"))

    # alt path without version
    bis_url2 = (
        "https://stats.bis.org/api/v2/data/WS_CBPOL/D.AU+CA+NZ+US+GB+JP+XM+CH"
        "?format=csvdata&startPeriod=2018-01-01"
    )
    attempts.append(fetch(bis_url2, RAW / "bis_cbpol_d_g10_alt.csv", note="BIS WS_CBPOL alt csvdata"))

    # --- RBA F1 alternatives ---
    for url, name, note in [
        (
            "https://www.rba.gov.au/statistics/tables/xls/f01hist.xls",
            "rba_f01hist.xls",
            "RBA F1 hist xls retry",
        ),
        (
            "https://www.rba.gov.au/statistics/tables/xls-hist/f01hist.xls",
            "rba_f01hist_xls_hist.xls",
            "RBA F1 xls-hist mirror",
        ),
        (
            "https://www.rba.gov.au/statistics/tables/xls/f01dhist.xls",
            "rba_f01dhist.xls",
            "RBA F1d hist xls",
        ),
        (
            "https://data.rba.gov.au/api/v2/statistics/tables/f1/data",
            "rba_data_api_f1.json",
            "RBA data API f1",
        ),
    ]:
        attempts.append(fetch(url, RAW / name, note=note))

    # --- FRED mirrors (short timeout survivors) ---
    for series, fname in [
        ("CORRA", "fred_corra.csv"),
        ("IRSTCI01AUM156N", "fred_oecd_au_call.csv"),  # OECD call money AU monthly-ish
        ("IRSTCI01CAM156N", "fred_oecd_ca_call.csv"),
        ("RBATCTR", "fred_rba_target.csv"),
    ]:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        attempts.append(fetch(url, RAW / fname, note=f"FRED {series}"))

    # --- Yahoo proxies (cash-like; label as research proxy) ---
    # Yahoo chart API for ^IRX (US 13w) already have USD; skip. AUD/CAD short rate ETFs weak.
    # OECD SDMX MEI short rates
    oecd_url = (
        "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,"
        "4.0/AUS+CAN.M.IR3TIB.PA....?"
        "startPeriod=2018-01&dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
    )
    attempts.append(fetch(oecd_url, RAW / "oecd_mei_short_au_ca.csv", note="OECD MEI AU/CA short rates"))

    # Parse survivors into series dicts
    series_map: dict[str, dict[date, float]] = {}
    source_map: dict[str, str] = {}

    boc_csv = RAW / "boc_corra_avg_intwo.csv"
    if boc_csv.exists() and any(a.get("path", "").endswith("boc_corra_avg_intwo.csv") and a["result"] == "OK" for a in attempts):
        s = parse_boc_csv(boc_csv)
        if len(s) >= 200:
            series_map["CAD_CORRA"] = s
            source_map["CAD_CORRA"] = "BoC Valet AVG.INTWO"

    boc_json = RAW / "boc_corra_avg_intwo.json"
    if "CAD_CORRA" not in series_map and boc_json.exists():
        if any(a.get("path", "").endswith("boc_corra_avg_intwo.json") and a["result"] == "OK" for a in attempts):
            s = parse_boc_json(boc_json, "AVG.INTWO")
            if len(s) >= 200:
                series_map["CAD_CORRA"] = s
                source_map["CAD_CORRA"] = "BoC Valet AVG.INTWO json"

    boc_tgt = RAW / "boc_target_overnight_v39079.csv"
    if boc_tgt.exists() and any(a.get("path", "").endswith("boc_target_overnight_v39079.csv") and a["result"] == "OK" for a in attempts):
        s = parse_boc_csv(boc_tgt)
        if len(s) >= 50:
            series_map["CAD_TARGET"] = s
            source_map["CAD_TARGET"] = "BoC Valet V39079"

    for bis_name in ("bis_cbpol_d_g10.csv", "bis_cbpol_d_g10_alt.csv"):
        bp = RAW / bis_name
        ok = any(a.get("path", "").endswith(bis_name) and a["result"] == "OK" for a in attempts)
        if not ok or not bp.exists() or bp.stat().st_size < 200:
            continue
        by = parse_bis_csv(bp)
        mapping = {
            "AU": "AUD_BIS_POL",
            "CA": "CAD_BIS_POL",
            "NZ": "NZD_BIS_POL",
            "US": "USD_BIS_POL",
            "GB": "GBP_BIS_POL",
            "JP": "JPY_BIS_POL",
            "XM": "EUR_BIS_POL",
            "CH": "CHF_BIS_POL",
        }
        for area, col in mapping.items():
            if area in by and len(by[area]) >= 50:
                series_map[col] = by[area]
                source_map[col] = f"BIS WS_CBPOL {bis_name}"
        if any(k.endswith("_BIS_POL") for k in series_map):
            break

    fred_corra = RAW / "fred_corra.csv"
    if fred_corra.exists() and any(a.get("path", "").endswith("fred_corra.csv") and a["result"] == "OK" for a in attempts):
        s = parse_fred_csv(fred_corra)
        if len(s) >= 200 and "CAD_CORRA" not in series_map:
            series_map["CAD_CORRA"] = s
            source_map["CAD_CORRA"] = "FRED CORRA"

    fred_rba = RAW / "fred_rba_target.csv"
    if fred_rba.exists() and any(a.get("path", "").endswith("fred_rba_target.csv") and a["result"] == "OK" for a in attempts):
        s = parse_fred_csv(fred_rba)
        if len(s) >= 50:
            series_map["AUD_RBATCTR"] = s
            source_map["AUD_RBATCTR"] = "FRED RBATCTR"

    # Prefer CAD_CORRA over CAD_BIS/CAD_TARGET for overnight fidelity
    # Prefer AUD_BIS_POL or AUD_RBATCTR for AUD
    panel_cols: list[tuple[str, str]] = []
    if "USD_BIS_POL" in series_map:
        panel_cols.append(("usd", "USD_BIS_POL"))
    if "AUD_BIS_POL" in series_map:
        panel_cols.append(("aud", "AUD_BIS_POL"))
    elif "AUD_RBATCTR" in series_map:
        panel_cols.append(("aud", "AUD_RBATCTR"))
    if "CAD_CORRA" in series_map:
        panel_cols.append(("cad", "CAD_CORRA"))
    elif "CAD_BIS_POL" in series_map:
        panel_cols.append(("cad", "CAD_BIS_POL"))
    elif "CAD_TARGET" in series_map:
        panel_cols.append(("cad", "CAD_TARGET"))
    if "NZD_BIS_POL" in series_map:
        panel_cols.append(("nzd", "NZD_BIS_POL"))
    if "EUR_BIS_POL" in series_map:
        panel_cols.append(("eur", "EUR_BIS_POL"))
    if "GBP_BIS_POL" in series_map:
        panel_cols.append(("gbp", "GBP_BIS_POL"))
    if "JPY_BIS_POL" in series_map:
        panel_cols.append(("jpy", "JPY_BIS_POL"))
    if "CHF_BIS_POL" in series_map:
        panel_cols.append(("chf", "CHF_BIS_POL"))

    start, end = date(2018, 1, 1), date(2026, 7, 10)
    filled = {src: ff_fill(series_map[src], start, end) for _, src in panel_cols}

    # Panel forms if we have USD + (AUD or CAD) at minimum for new child;
    # full G10-lite needs AUD+CAD
    has_aud = any(c == "aud" for c, _ in panel_cols)
    has_cad = any(c == "cad" for c, _ in panel_cols)
    panel_status = "NO_PANEL"
    panel_path: Path | None = None
    panel_sha = None
    n_rows = 0
    if has_aud and has_cad:
        # union of business days present in both
        dates = sorted(set(filled[panel_cols[0][1]]) & set.intersection(*[set(filled[s]) for _, s in panel_cols]))
        # Prefer intersection of aud+cad+usd if usd present
        need = [s for c, s in panel_cols if c in ("aud", "cad", "usd")]
        if need:
            dates = sorted(set.intersection(*[set(filled[s]) for s in need]))
        panel_path = PANELS / "g10_policy_overnight_d1_altsource_v2.csv"
        with panel_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date"] + [c for c, _ in panel_cols])
            for d in dates:
                row = [d.isoformat()]
                ok = True
                for c, src in panel_cols:
                    if d not in filled[src]:
                        ok = False
                        break
                    row.append(f"{filled[src][d]:.6f}")
                if ok:
                    w.writerow(row)
                    n_rows += 1
        panel_sha = sha256_file(panel_path)
        panel_status = "PANEL_READY" if n_rows >= 500 else "PANEL_THIN"
    elif has_aud or has_cad:
        panel_status = "PARTIAL_SERIES_NO_JOINT_PANEL"

    contract = {
        "schema": "g10_policy_overnight_available_at_utc.v2",
        "generated_at_utc": utc_now(),
        "status": panel_status,
        "authority": (
            "BIS policy rates are target/policy (step) series, not always CORRA/AONIA MM. "
            "BoC AVG.INTWO is CORRA overnight. Use +1 business-day lag for available-at "
            "(publication lag conservative). Monthly OECD/SNB ≠ daily event book alone."
        ),
        "lags_business_days": {"usd": 1, "aud": 1, "cad": 1, "nzd": 1, "eur": 1, "gbp": 1, "jpy": 2, "chf": 1},
        "columns": [{"col": c, "source_key": s, "source": source_map.get(s)} for c, s in panel_cols],
        "panel_path": None
        if panel_path is None
        else str(panel_path.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": panel_sha,
        "panel_rows": n_rows,
        "series_counts": {k: len(v) for k, v in series_map.items()},
    }
    cpath = CONTRACTS / "20260715_G10_POLICY_OVERNIGHT_AVAILABLE_AT_UTC_V2.json"
    cpath.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "g10_overnight_altsource_acquire.v2",
        "generated_at_utc": utc_now(),
        "parent_attempt": "preflight/v8_exogenous/manifests/20260715_G10_OVERNIGHT_ACQUIRE_ATTEMPT_V1.json",
        "status": panel_status,
        "attempts": attempts,
        "contract_path": str(cpath.relative_to(ROOT)).replace("\\", "/"),
        "contract_sha256": sha256_file(cpath),
        "panel_path": contract["panel_path"],
        "panel_sha256": panel_sha,
        "panel_rows": n_rows,
        "ok_count": sum(1 for a in attempts if a["result"] == "OK"),
        "fail_count": sum(1 for a in attempts if a["result"] != "OK"),
    }
    mpath = MAN / "20260715_G10_OVERNIGHT_ALTSOURCE_ACQUIRE_V2.json"
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(mpath)
    mpath.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readout = READ / "20260715_G10_ALTSOURCE_ACQUIRE_READOUT.md"
    lines = [
        "# G10 overnight alt-source acquire readout",
        "",
        f"Generated: {utc_now()}",
        f"Status: **{panel_status}**",
        f"Manifest SHA: `{manifest['manifest_sha256']}`",
        "",
        "## Attempts",
        "",
        "| Note | Result | Bytes |",
        "|---|---|---|",
    ]
    for a in attempts:
        lines.append(
            f"| {a.get('note','')} | {a.get('result')} | {a.get('bytes','—')} |"
        )
    lines += [
        "",
        "## Series retained",
        "",
        "```json",
        json.dumps(contract["series_counts"], indent=2),
        "```",
        "",
        f"Panel rows: {n_rows}",
        f"Panel: `{contract['panel_path']}`",
        f"Panel SHA: `{panel_sha}`",
        "",
        "## Authority",
        "",
        contract["authority"],
        "",
    ]
    readout.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": panel_status,
        "ok": manifest["ok_count"],
        "fail": manifest["fail_count"],
        "rows": n_rows,
        "panel": contract["panel_path"],
        "manifest_sha": manifest["manifest_sha256"],
        "series": list(series_map.keys()),
    }, indent=2))


if __name__ == "__main__":
    main()
