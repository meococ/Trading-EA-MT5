#!/usr/bin/env python3
"""COT lev-money SIZE BUDGET probe on RR2 (not a skip-gate).

Hypothesis: HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001
Semantics: keep ALL RR2 trades; scale risk/PnL by a priori crowding size mult.
A priori thresholds frozen here — do NOT mine from readout.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
PANEL = PRE / "v8_exogenous" / "panels" / "cftc_jpy_finfut_net_lev_spec_d1_v1.csv"
RR2_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_194548"

OUT_JSON = PRE / "20260714_COT_SIZEBUDGET_RR2_PROBE.json"
OUT_MD = READ / "20260714_COT_SIZEBUDGET_RR2_PROBE.md"

EXPECTED_PANEL_SHA = "93D69F957A503B38C729F41D2E6B6D714A25EB330147383867C65A5EFC19AE54"
MARKET_EXACT = "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
PRIOR_WEEKS = 52
MIN_PRIORS = 40

HYP_ID = "HYP-RR2-CFTC-JPY-LEVMONEY-SIZEBUDGET-001"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts_sized(pnls: list[float], size_mults: list[float], base: float = BASE_COST) -> dict:
    """Cost haircut scales with size_mult: haircut = BASE_COST * mult * size_mult."""
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult * sm for p, sm in zip(pnls, size_mults)]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def haircuts_flat(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / WEEKS if WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict, baseline_x15: float | None) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.0 <= tpw <= 6.5):
        notes.append("cadence_fail")
    if pf < 1.05:
        notes.append("pf_fail")
    if x15 < 1.10:
        notes.append("stress_fail")
    if baseline_x15 is not None and not (x15 > baseline_x15 + 0.01):
        notes.append("no_stress_lift_vs_baseline")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and baseline_x15 is not None
        and x15 > baseline_x15 + 0.01
    ):
        return "PROBE_SURVIVOR", notes
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "KILLED_AT_OFFLINE_PROBE", ["joint_screen_miss"]


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def load_closed_trades(path: Path) -> list[dict]:
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in ("1", "true", "True"):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                ot = parse_dt(op.get("event_time") or "")
                ct = parse_dt(row.get("event_time") or "")
                closed.append(
                    {
                        "position_id": pid,
                        "open_time": ot,
                        "close_time": ct,
                        "pnl": pnl,
                    }
                )
    return closed


def size_mult_from_crowd_pct(crowd_pct: float | None) -> float:
    if crowd_pct is None:
        return 1.00  # fail-open on size, not skip
    if crowd_pct < 0.50:
        return 1.00
    if crowd_pct < 0.80:
        return 0.67
    return 0.50


def percentile_rank(value: float, priors: list[float]) -> float:
    """Fraction of priors strictly less than value + 0.5*ties / n (midrank)."""
    n = len(priors)
    if n == 0:
        return 0.5
    less = sum(1 for x in priors if x < value)
    equal = sum(1 for x in priors if x == value)
    return (less + 0.5 * equal) / n


def load_cot_panel() -> list[dict]:
    panel_sha = sha256_file(PANEL)
    if panel_sha != EXPECTED_PANEL_SHA:
        raise SystemExit(
            f"FAIL CLOSED: panel SHA mismatch got={panel_sha} expected={EXPECTED_PANEL_SHA}"
        )
    rows: list[dict] = []
    with PANEL.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            market = (row.get("market") or "").strip()
            if "JAPANESE YEN - CHICAGO" not in market:
                continue
            if "EURO FX" in market:
                continue
            if market != MARKET_EXACT:
                continue
            avail = datetime.strptime(row["available_at_utc"][:10], "%Y-%m-%d")
            obs = datetime.strptime(row["observation_date"], "%Y-%m-%d")
            net = float(row["net_lev_money"])
            rows.append(
                {
                    "observation_date": obs,
                    "available_at": avail,
                    "net_lev_money": net,
                    "abs_net": abs(net),
                }
            )
    rows.sort(key=lambda x: x["observation_date"])
    return rows, panel_sha


def attach_crowd_pct(rows: list[dict]) -> list[dict]:
    """For each row, percentile of |net| among prior 52 weekly obs ending before current."""
    out = []
    for i, r in enumerate(rows):
        # priors: rows with observation_date < current, take last PRIOR_WEEKS
        priors = [rows[j]["abs_net"] for j in range(i) if rows[j]["observation_date"] < r["observation_date"]]
        priors = priors[-PRIOR_WEEKS:]
        if len(priors) < MIN_PRIORS:
            crowd = None
        else:
            crowd = percentile_rank(r["abs_net"], priors)
        nr = dict(r)
        nr["crowd_pct"] = crowd
        nr["n_priors"] = len(priors)
        out.append(nr)
    return out


def lookup_latest(cot: list[dict], open_date: datetime) -> dict | None:
    """Latest COT row with available_at <= open_time date."""
    od = open_date.replace(hour=0, minute=0, second=0, microsecond=0)
    hit = None
    for r in cot:
        if r["available_at"] <= od:
            hit = r
        else:
            break
    return hit


def main() -> None:
    cot_raw, panel_sha = load_cot_panel()
    cot = attach_crowd_pct(cot_raw)

    trades_path = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_path)
    windowed = [
        t
        for t in trades
        if t["open_time"] is not None and FROM <= t["open_time"] <= TO
    ]

    raw_pnls: list[float] = []
    scaled_pnls: list[float] = []
    size_mults: list[float] = []
    crowd_vals: list[float | None] = []
    funnel = Counter()

    for t in windowed:
        row = lookup_latest(cot, t["open_time"])
        crowd = row["crowd_pct"] if row else None
        sm = size_mult_from_crowd_pct(crowd)
        raw = float(t["pnl"])
        scaled = raw * sm
        raw_pnls.append(raw)
        scaled_pnls.append(scaled)
        size_mults.append(sm)
        crowd_vals.append(crowd)
        key = f"{sm:.2f}"
        funnel[key] += 1

    base_m = metrics(raw_pnls)
    base_hc = haircuts_flat(raw_pnls)
    scaled_m = metrics(scaled_pnls)
    # For scaled stress: apply haircut to scaled pnls with size-scaled cost
    scaled_hc = haircuts_sized(scaled_pnls, size_mults)

    baseline_x15 = (base_hc.get("x1_5") or {}).get("pf")
    verdict, notes = joint_verdict(scaled_m, scaled_hc, baseline_x15)

    missing_crowd = sum(1 for c in crowd_vals if c is None)
    body = {
        "hypothesis_id": HYP_ID,
        "semantics": "SIZE_BUDGET_NOT_GATE",
        "panel_path": str(PANEL.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": panel_sha,
        "market_exact": MARKET_EXACT,
        "trades_path": str(trades_path.relative_to(ROOT)).replace("\\", "/"),
        "trades_sha256": sha256_file(trades_path),
        "window": {"from": "2021-01-01", "to": "2025-12-31", "weeks": round(WEEKS, 6)},
        "a_priori": {
            "crowd_score": "percentile_rank_|net_lev_money|_prior_52_weekly_min40",
            "size_mult": {"lt_0.50": 1.00, "0.50_to_0.80": 0.67, "ge_0.80": 0.50, "missing": 1.00},
            "base_cost": BASE_COST,
            "cost_scales_with_size": True,
            "joint_kill": "N<80 OR tpw not in [1,6.5] OR PF<1.05 OR x1.5 PF<1.10 OR no stress lift >0.01 vs baseline x1.5",
            "survivor": "PF>1.20 AND tpw in [1.5,6] AND x1.5 PF>=1.15 AND stress lift vs baseline",
        },
        "baseline_unscaled": {"metrics": base_m, "haircuts": base_hc},
        "sized": {
            "metrics": scaled_m,
            "haircuts": scaled_hc,
            "size_mult_histogram": dict(sorted(funnel.items())),
            "missing_crowd_n": missing_crowd,
            "n_cot_rows_jpy": len(cot),
        },
        "stress_lift_x15": None
        if baseline_x15 is None
        else round(((scaled_hc.get("x1_5") or {}).get("pf") or 0.0) - baseline_x15, 4),
        "verdict": verdict,
        "kill_notes": notes,
        "updated_at": "2026-07-14",
    }

    # receipt over canonical body without receipt field
    receipt = sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    body["receipt_sha256"] = receipt

    OUT_JSON.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# COT Size-Budget RR2 Probe Readout")
    md.append("")
    md.append(f"**Hypothesis:** `{HYP_ID}`")
    md.append(f"**Verdict:** `{verdict}`")
    md.append(f"**Notes:** {notes}")
    md.append("")
    md.append("## Semantics")
    md.append("SIZE BUDGET (scale risk/PnL). Keep all RR2 trades. No skip-by-z.")
    md.append("")
    md.append("## Metrics")
    md.append("")
    md.append("| Set | N | PF | TPW | Net | x1 PF | x1.5 PF | x2 PF |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    md.append(
        f"| Baseline | {base_m['n']} | {base_m['pf']} | {base_m['tpw']} | {base_m['net']} | "
        f"{base_hc['x1']['pf']} | {base_hc['x1_5']['pf']} | {base_hc['x2']['pf']} |"
    )
    md.append(
        f"| Sized | {scaled_m['n']} | {scaled_m['pf']} | {scaled_m['tpw']} | {scaled_m['net']} | "
        f"{scaled_hc['x1']['pf']} | {scaled_hc['x1_5']['pf']} | {scaled_hc['x2']['pf']} |"
    )
    md.append("")
    md.append(f"Stress lift (sized x1.5 − baseline x1.5): `{body['stress_lift_x15']}`")
    md.append(f"Size mult histogram: `{dict(sorted(funnel.items()))}`")
    md.append(f"Missing crowd (fail-open size=1.0): `{missing_crowd}`")
    md.append(f"Panel SHA: `{panel_sha}`")
    md.append(f"Receipt SHA: `{receipt}`")
    md.append("")
    md.append("A priori thresholds frozen in probe script; not mined from this readout.")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    # Registry: preregistered then result
    def append_reg(state: str, reason: str) -> None:
        rec = {
            "record_type": "candidate",
            "schema_version": 1,
            "hypothesis_id": HYP_ID,
            "state": state,
            "verdict": verdict if state != "preregistered" else "PENDING_OFFLINE_PROBE",
            "reason": reason,
            "updated_at": "2026-07-14",
            "lane": "dichotomy_break_cot_sizebudget_20260714",
            "feature_family": "cftc_jpy_levmoney_abs_pct_size_budget_on_rr2",
            "parent_candidate": "HYP-RR2-CFTC-JPY-LEVMONEY-ZGATE-001",
            "symbol": "USDJPY",
            "timeframe": "M15",
            "window": "2021.01.01-2025.12.31",
            "model": "offline_closed_bar_probe",
            "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            "probe_json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "run_ids": ["20260714_194548"],
            "metrics": scaled_m if state != "preregistered" else None,
            "validation": {
                "offline_probe": "SURVIVOR" if verdict == "PROBE_SURVIVOR" else "KILL",
                "model0": "WITHHELD",
                "kill_notes": notes,
            }
            if state != "preregistered"
            else {"offline_probe": "PENDING", "model0": "WITHHELD"},
            "panel_sha256": panel_sha,
            "receipt_sha256": receipt if state != "preregistered" else None,
        }
        with REG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    append_reg(
        "preregistered",
        "a priori COT |net_lev_money| percentile size-budget on RR2; keep all trades; scale PnL",
    )
    final_state = "survivor" if verdict == "PROBE_SURVIVOR" else "killed"
    append_reg(
        final_state,
        f"COT lev-money size-budget on RR2: N={scaled_m['n']} PF={scaled_m['pf']} "
        f"tpw={scaled_m['tpw']} x1.5={scaled_hc['x1_5']['pf']}; notes={notes}; no Model0",
    )

    print("=== COT SIZEBUDGET RR2 PROBE ===")
    print(f"hypothesis_id: {HYP_ID}")
    print(f"verdict: {verdict}")
    print(f"notes: {notes}")
    print(f"baseline: n={base_m['n']} pf={base_m['pf']} tpw={base_m['tpw']} x15={base_hc['x1_5']['pf']}")
    print(
        f"sized:    n={scaled_m['n']} pf={scaled_m['pf']} tpw={scaled_m['tpw']} "
        f"x15={scaled_hc['x1_5']['pf']} lift={body['stress_lift_x15']}"
    )
    print(f"histogram: {dict(sorted(funnel.items()))}")
    print(f"panel_sha: {panel_sha}")
    print(f"receipt_sha256: {receipt}")
    print(f"wrote_json: {OUT_JSON} exists={OUT_JSON.exists()}")
    print(f"wrote_md: {OUT_MD} exists={OUT_MD.exists()}")


if __name__ == "__main__":
    main()
