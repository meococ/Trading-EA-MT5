#!/usr/bin/env python3
"""Complete V8 G3 rates panel gaps: BoJ daily call + policy steps + lag contract.

Acquisition / contract prep ONLY. Does not authorize probe, prereg, EA, compile.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research")
RAW = ROOT / "preflight" / "v8_exogenous" / "raw"
MANIFESTS = ROOT / "preflight" / "v8_exogenous" / "manifests"
CONTRACTS = ROOT / "preflight" / "v8_exogenous" / "contracts"
FRED = ROOT / "data" / "exogenous"
READOUTS = ROOT / "readouts"
BOJ_HTML = Path(
    r"C:\Users\ADMIN\.cursor\projects\d-Trading-EA-MT5\agent-tools\77a813fb-fa3e-4226-9c4a-9e137bc3f530.txt"
)

# Official BoJ Basic Discount / Basic Loan Rate effective dates from
# https://www.boj.or.jp/en/statistics/boj/other/discount/discount.htm
# (fetched 2026-07-13). Values are percent per annum; post-2001 table uses
# single Basic Discount / Basic Loan Rate column.
# Post-2001 chronology from BoJ EN discount table (fetched 2026-07-13).
BOJ_POLICY_STEPS = [
    ("2001-01-04", 0.50),
    ("2001-02-13", 0.35),
    ("2001-03-01", 0.25),
    ("2001-09-19", 0.10),
    ("2006-07-14", 0.40),
    ("2007-02-21", 0.75),
    ("2008-10-31", 0.50),
    ("2008-12-19", 0.30),
    ("2024-08-01", 0.50),
    ("2025-01-27", 0.75),
    ("2025-12-22", 1.00),
    ("2026-06-17", 1.25),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(path: Path, text: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8")
    path.write_bytes(data)
    return {
        "name": path.name,
        "path": str(path),
        "status": "OK",
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
    }


def parse_boj_call(html_path: Path) -> dict:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    pairs = re.findall(
        r"\|\s*((?:19|20)\d{2}/\d{2}/\d{2})\s*\|\s*([-+]?\d+(?:\.\d+)?|NA)\s*\|",
        text,
    )
    lines = ["observation_date,BOJ_CALL_ON"]
    for d, v in pairs:
        lines.append(f"{d.replace('/', '-')},{v}")
    out = RAW / "jpy_boj_uncollateralized_overnight_call_daily.csv"
    meta = write_text(out, "\n".join(lines) + "\n")
    meta.update(
        {
            "source_url": "https://www.stat-search.boj.or.jp/ssi/mtshtml/fm01_d_1.html",
            "series_code": "FM01'STRDCLUCON",
            "source_html_cache": str(html_path),
            "rows_data": len(pairs),
            "coverage_note": "Daily uncollateralized overnight call average; NA retained (no silent fill).",
        }
    )
    return meta


def write_boj_policy_steps() -> dict:
    lines = [
        "effective_date,basic_discount_loan_rate_pct,source",
    ]
    for d, v in BOJ_POLICY_STEPS:
        lines.append(
            f"{d},{v:.2f},boj_en_discount_table_20260713"
        )
    out = RAW / "jpy_boj_basic_discount_loan_rate_steps.csv"
    meta = write_text(out, "\n".join(lines) + "\n")
    meta.update(
        {
            "source_url": "https://www.boj.or.jp/en/statistics/boj/other/discount/discount.htm",
            "rows_data": len(BOJ_POLICY_STEPS),
            "coverage_note": "Effective-date step series only; sparse; not a daily money-market substitute.",
        }
    )
    return meta


def verify_existing() -> list[dict]:
    expected = {
        "ecb_dfr_daily.csv": "175bdbb3f46f4cd9e42cccbc84f20e86049b320767c16833cc2fa23df8bbe63d",
        "us_treasury_bill_rates_2018.csv": "6f037e225a3f296613f620404667971df9f202743e70540d9ffbf5c7d30a3a51",
        "us_treasury_bill_rates_2019.csv": "f0396ee6dfaa3a60ce676c593a026f8cfbb9bcd72af7b6aa8450c68a5d3ac98a",
        "us_treasury_bill_rates_2020.csv": "cc29ccb650fe49ce04781e97332cecba11c20e466b053a08d6fb15b6b24dbd20",
        "us_treasury_bill_rates_2021.csv": "e45398cf008aeca21679fe1ebcc7d051add07f0819ef62723fe472a1ea00377d",
        "us_treasury_bill_rates_2022.csv": "4059b158b989b5bb4d295cc5e3356434bcceba44d89365e368a2aafbf2077859",
        "us_treasury_bill_rates_2023.csv": "ca4d73d5e9856391c06ef0b3ec252d950019b1a5db97c934d92d9569fc4ba87c",
        "us_treasury_bill_rates_2024.csv": "47cc8985d9474bbdaea37266ac5658f6b1b276d3310c54c7efd70358e80bc37b",
        "us_treasury_bill_rates_2025.csv": "aa024dfde7700a971b287d7cc8284fd8c34f4dd6c66cb009cf39f501be33b562",
        "boe_bank_rate.csv": "1adcc97719c437839b678ab295f1c176234cdb91dd63f4516f2b82ac308d7806",
    }
    rows = []
    for name, exp in expected.items():
        path = RAW / name
        if not path.exists():
            rows.append({"name": name, "status": "MISSING", "expected_sha256": exp})
            continue
        got = sha256_file(path)
        rows.append(
            {
                "name": name,
                "status": "HASH_OK" if got.lower() == exp.lower() else "HASH_MISMATCH",
                "bytes": path.stat().st_size,
                "sha256": got,
                "expected_sha256": exp,
                "path": str(path),
            }
        )
    # COT claimed OK in V1 manifest but out of V8 rates packet; integrity check only.
    for year in (2022, 2023, 2024):
        z = RAW / f"cot_tff_{year}.zip"
        rows.append(
            {
                "name": z.name,
                "status": "PRESENT" if z.exists() else "MISSING_DESPITE_PRIOR_MANIFEST_OK",
                "v8_packet_scope": "OUT_OF_SCOPE_RATES_ONLY",
                "path": str(z),
            }
        )
    return rows


def invent_fred_index() -> list[dict]:
    rows = []
    if not FRED.exists():
        return rows
    for path in sorted(FRED.glob("*.csv")):
        rows.append(
            {
                "name": path.name,
                "status": "OK",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "path": str(path),
                "tree": "research/data/exogenous",
            }
        )
    return rows


def write_lag_contract(acquired: list[dict]) -> dict:
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    contract = {
        "schema": "v8_rates_available_at_utc_contract.v1",
        "status": "DRAFT_CONTRACT / NO_JOIN / NO_PROBE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": (
            "Acquisition readiness under Owner 1A. Does not authorize Deep Research "
            "submit, offline probe, registry, prereg, EA, compile, or Model 0."
        ),
        "join_rule": "FX closed bar may use a rate observation only if bar_close_utc >= available_at_utc. No silent forward-fill across missing observations or policy gaps.",
        "series": [
            {
                "series_id": "USD_DFF_OR_SOFR",
                "local_files": [
                    "research/data/exogenous/us_fed_funds_DFF.csv",
                    "research/data/exogenous/us_sofr_SOFR.csv",
                ],
                "observation_clock": "US calendar day",
                "publication_lag_rule": "Treat as available next US business day 15:00 UTC unless ALFRED first-release proves earlier. Prefer SOFR after 2018-04-03; DFF as longer history USD proxy with explicit mapping note in any later probe.",
                "fail_closed": "Missing day => no carry update that day.",
            },
            {
                "series_id": "USD_TBILL_DAILY",
                "local_files": [
                    f"research/preflight/v8_exogenous/raw/us_treasury_bill_rates_{y}.csv"
                    for y in range(2018, 2026)
                ],
                "observation_clock": "US Treasury published daily bill rates",
                "publication_lag_rule": "available_at_utc = next calendar day 00:00 UTC after observation date (conservative). Do not use same-day T-bill for Tokyo/London bars before US publish.",
                "fail_closed": "Missing year/day => no differential that day.",
            },
            {
                "series_id": "EUR_ECB_DFR",
                "local_files": [
                    "research/preflight/v8_exogenous/raw/ecb_dfr_daily.csv",
                    "research/data/exogenous/eur_ecb_deposit_ECBDFR.csv",
                ],
                "observation_clock": "ECB deposit facility rate level series",
                "publication_lag_rule": "Use effective date / series timestamp; prefer official ECB SDMX daily level. available_at_utc = max(observation_date 16:00 UTC, next bar after known announcement).",
                "fail_closed": "Gap => hold prior known effective rate only if continuity is source-justified; else fail closed.",
            },
            {
                "series_id": "EUR_ESTR",
                "local_files": [
                    "research/data/exogenous/eur_estr_ECBESTRVOLWGTTRMDMNRT.csv"
                ],
                "observation_clock": "Euro short-term rate",
                "publication_lag_rule": "ESTR typically T+1 morning publication. available_at_utc = next ECB business day 08:00 UTC.",
                "fail_closed": "Pre-2019-10-01 ESTR absent; use ECB DFR proxy only with explicit probe mapping, never silent splice.",
            },
            {
                "series_id": "GBP_BOE_BANK_RATE",
                "local_files": [
                    "research/preflight/v8_exogenous/raw/boe_bank_rate.csv"
                ],
                "observation_clock": "BoE IUDBEDR daily export",
                "publication_lag_rule": "Policy rate is effective-date based; daily export repeats level. available_at_utc = observation DATE 12:00 UTC (London noon) conservative.",
                "fail_closed": "Missing DATE row => no GBP leg that day.",
            },
            {
                "series_id": "GBP_SONIA",
                "local_files": ["research/data/exogenous/gbp_sonia_IUDSOIA.csv"],
                "observation_clock": "SONIA daily",
                "publication_lag_rule": "Typically next London business morning. available_at_utc = next UK business day 09:00 UTC.",
                "fail_closed": "Missing => no SONIA differential that day.",
            },
            {
                "series_id": "JPY_BOJ_CALL_ON",
                "local_files": [
                    "research/preflight/v8_exogenous/raw/jpy_boj_uncollateralized_overnight_call_daily.csv"
                ],
                "observation_clock": "BoJ uncollateralized overnight call average daily",
                "publication_lag_rule": "BoJ table updates with lag; conservative available_at_utc = next Tokyo business day 06:00 UTC. NA rows are missing, not zero.",
                "fail_closed": "NA or missing => no JPY money-market leg that day.",
            },
            {
                "series_id": "JPY_BOJ_POLICY_STEPS",
                "local_files": [
                    "research/preflight/v8_exogenous/raw/jpy_boj_basic_discount_loan_rate_steps.csv"
                ],
                "observation_clock": "Effective-date policy steps only",
                "publication_lag_rule": "Rate in force only when bar_close_utc >= effective_date 00:00 Asia/Tokyo converted to UTC. Announcement may precede effective date — never backfill future effective rate.",
                "fail_closed": "Sparse steps alone cannot hit 2-5 trades/week; money-market call series is required companion.",
            },
        ],
        "negative_control_reminder": (
            "Any later probe must include a rates-zeroed or rates-shuffled control "
            "so carry differential cannot collapse to spot momentum/rank."
        ),
        "acquired_files_referenced": [a.get("name") for a in acquired],
    }
    path = CONTRACTS / "20260713_V8_RATES_AVAILABLE_AT_UTC_CONTRACT_V1.json"
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "status": contract["status"],
    }


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)

    verified = verify_existing()
    boj_call = parse_boj_call(BOJ_HTML)
    boj_policy = write_boj_policy_steps()
    fred = invent_fred_index()
    acquired_new = [boj_call, boj_policy]
    lag = write_lag_contract(acquired_new + fred)

    panel = {
        "schema": "v8_g3_rates_panel_readiness.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RATES_PANEL_MOSTLY_READY / LAG_CONTRACT_DRAFT / NO_PROBE / NO_DR_SUBMIT",
        "v8_packet": "03. EA Developer/EA_SonicR/research/20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md",
        "authority_flags": {
            "deep_research_submit": False,
            "offline_probe": False,
            "registry_append": False,
            "prereg": False,
            "ea_compile_model0": False,
        },
        "verified_raw_files": verified,
        "new_acquisitions": acquired_new,
        "fred_mirror_index": fred,
        "lag_contract": lag,
        "remaining_gaps": [
            "ALFRED vintage pulls not yet archived (revised-series risk for some FRED series).",
            "EFFR / DTB3 not pulled separately (DFF/SOFR and Treasury bills used as lawful proxies pending Deep Research mapping).",
            "COT zips claimed OK in older manifest are missing on disk; out of V8 rates packet — do not use for V8.",
            "Same-broker cost provenance still incomplete; Model 0 blocked even after a future probe pass.",
        ],
        "owner_decision_required": "CONFIRM_SUBMIT_DEEP_RESEARCH_V8 on rates-only data-contract packet with Browser UI readback GPT-5.6 Sol + Pro + Nghien cuu sau.",
    }
    manifest_path = MANIFESTS / "20260713_V8_G3_RATES_PANEL_READINESS_V1.json"
    manifest_path.write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")
    panel_hash = sha256_file(manifest_path)
    panel["manifest_sha256"] = panel_hash
    # rewrite with hash field
    manifest_path.write_text(json.dumps(panel, indent=2) + "\n", encoding="utf-8")

    print("boj_call", boj_call["status"], boj_call.get("rows_data"), boj_call["sha256"])
    print("boj_policy", boj_policy["status"], boj_policy.get("rows_data"), boj_policy["sha256"])
    print("lag", lag["path"], lag["sha256"])
    print("manifest", manifest_path, sha256_file(manifest_path))
    bad = [r for r in verified if r["status"] not in ("HASH_OK", "MISSING_DESPITE_PRIOR_MANIFEST_OK", "PRESENT")]
    print("verify_bad", bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
