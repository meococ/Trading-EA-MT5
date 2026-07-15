#!/usr/bin/env python3
"""Structural rebuild offline probes V2 — stop-run accept + LNY event redefine.

A priori (frozen before ranking; GPT waived; no densify / no Phase-0 compose):
  A  HYP-H1-PDLIQ-STOPRUN-ACCEPT-001
     Prior-day H/L stop-run wick → 2 H1 closes beyond sweep extreme (continuation).
     NOT ASR/EQHL reclaim, NOT PDH immediate-break, NOT ORB-accept, NOT PDH-retest.
  B  HYP-LNY-RANGE-ACCEPT-M15-001
     London range-expansion quality event → 2 M15 accepts beyond London H/L.
     Event-definition change vs LondonNY PB / DualWin window densify; NO Mon/day mine.

Probe-only. Model 0 only if PROBE_SURVIVOR under thick+cadence+cost-stress screen.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"

OUT_JSON = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.json"
OUT_MD = READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V2.md"
DEDUP_MD = READ / "20260714_STOPRUN_ACCEPT_LNY_EVENT_DEDUP_CLEARANCE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
DEPOSIT = 100_000.0
RISK_PCT = 0.50
BASE_COST = 12.0

# --- A priori contracts (do not mine from readout) ---
# Probe A
A_RR = 2.5
A_SWEEP_ATR = 0.15          # min wick beyond PDH/PDL
A_SL_BUF_ATR = 0.10
A_ACCEPT_BARS = 2
A_ENTRY_HOURS = range(8, 16)  # London→early NY
A_MAX_HOLD = 24
A_FLAT_HOUR = 22
A_MAX_DAY = 1

# Probe B — LNY event redefine
B_RR = 2.0
B_LDN_START = 9
B_LDN_END = 12              # measure at end of London measure window
B_RANGE_ATR = 1.00          # London range >= 1.0 * ATR_D1 (expansion event)
B_CLOSE_FRAC = 0.33         # close in directional outer third of London range
B_ACCEPT_BARS = 2
B_ENTRY_START = 13
B_ENTRY_END = 18
B_SL_BUF_ATR = 0.15
B_MAX_HOLD = 32             # M15 bars
B_FLAT_HOUR = 20
B_MAX_DAY = 1


@dataclass
class Bar:
    t: datetime
    o: float
    h: float
    l: float
    c: float


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / WEEKS, 4) if WEEKS else None,
    }


def haircuts(pnls: list[float]) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def atr(bars: list[Bar], i: int, period: int = 14) -> float:
    if i < period:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        prev = bars[j - 1].c
        trs.append(max(bars[j].h - bars[j].l, abs(bars[j].h - prev), abs(bars[j].l - prev)))
    return sum(trs) / period


def simulate(
    bars: list[Bar],
    i_entry: int,
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    max_hold: int,
    flat_hour: int,
) -> float:
    risk = abs(entry - sl)
    if risk <= 0:
        return 0.0
    exit_px = entry
    for k in range(i_entry + 1, min(len(bars), i_entry + 1 + max_hold)):
        bk = bars[k]
        if bk.t.hour >= flat_hour or bk.t.weekday() >= 4:
            exit_px = bk.o
            break
        if direction > 0:
            if bk.l <= sl:
                exit_px = sl
                break
            if bk.h >= tp:
                exit_px = tp
                break
        else:
            if bk.h >= sl:
                exit_px = sl
                break
            if bk.l <= tp:
                exit_px = tp
                break
        exit_px = bk.c
    risk_cash = DEPOSIT * (RISK_PCT / 100.0)
    signed = (exit_px - entry) / risk * direction
    return risk_cash * signed


def screen(pnls: list[float]) -> dict:
    m = metrics(pnls)
    hc = haircuts(pnls)
    # A priori thick+cadence+cost-stress screen for Model 0 authorization
    pass_n = m["n"] >= 80
    pass_cadence = m["tpw"] is not None and 1.5 <= m["tpw"] <= 6.0
    pass_pf = (m["pf"] or 0) > 1.20
    pass_stress = (hc["x1_5"]["pf"] or 0) >= 1.20 or (hc["x1"]["exp"] or 0) >= 25.0
    pass_all = pass_n and pass_cadence and pass_pf and pass_stress
    kill_notes = [
        x
        for x, ok in (
            ("n_fail", pass_n),
            ("cadence_fail", pass_cadence),
            ("pf_fail", pass_pf),
            ("stress_fail", pass_stress),
        )
        if not ok
    ]
    verdict = "PROBE_SURVIVOR" if pass_all else "KILLED_AT_OFFLINE_PROBE"
    return {
        "metrics": m,
        "cost_stress": hc,
        "pass_n": pass_n,
        "pass_cadence": pass_cadence,
        "pass_pf": pass_pf,
        "pass_stress": pass_stress,
        "kill_notes": kill_notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if pass_all else "WITHHELD_KILL_FAST",
    }


def load_bars(symbol_candidates: tuple[str, ...], tf) -> tuple[str, list[Bar]]:
    for s in symbol_candidates:
        if not mt5.symbol_select(s, True):
            continue
        rates = mt5.copy_rates_range(s, tf, FROM, TO)
        if rates is not None and len(rates) > 500:
            bars = [
                Bar(
                    t=datetime.fromtimestamp(int(r["time"])),
                    o=float(r["open"]),
                    h=float(r["high"]),
                    l=float(r["low"]),
                    c=float(r["close"]),
                )
                for r in rates
            ]
            return s, bars
    raise RuntimeError(f"no rates for {symbol_candidates}: {mt5.last_error()}")


def prior_day_hl(d1: list[Bar], day) -> tuple[float, float] | None:
    """PDH/PDL from the last completed D1 strictly before `day`."""
    for i in range(len(d1) - 1, -1, -1):
        if d1[i].t.date() < day:
            return d1[i].h, d1[i].l
    return None


def probe_a_stoprun_accept(h1: list[Bar], d1: list[Bar]) -> dict:
    """H1 prior-day liquidity stop-run → multi-bar continuation acceptance."""
    pnls: list[float] = []
    day_count: dict[str, int] = defaultdict(int)
    n_sweep = 0
    n_accept = 0

    for i in range(30, len(h1) - (A_ACCEPT_BARS + 2)):
        b = h1[i]
        if b.t.weekday() >= 4:
            continue
        if b.t.hour not in A_ENTRY_HOURS:
            continue
        pd = prior_day_hl(d1, b.t.date())
        if pd is None:
            continue
        pdh, pdl = pd
        a = atr(h1, i)
        if a <= 0:
            continue

        # Stop-run bar: wick pierces PDH/PDL by >= A_SWEEP_ATR * ATR
        # Continuation (not reclaim): close must also be on breakout side of level
        direction = 0
        sweep_extreme = 0.0
        if b.h >= pdh + A_SWEEP_ATR * a and b.c > pdh:
            direction = 1
            sweep_extreme = b.h
        elif b.l <= pdl - A_SWEEP_ATR * a and b.c < pdl:
            direction = -1
            sweep_extreme = b.l
        else:
            continue
        n_sweep += 1

        # Multi-bar acceptance: next A_ACCEPT_BARS closes beyond sweep extreme
        ok = True
        for k in range(1, A_ACCEPT_BARS + 1):
            bk = h1[i + k]
            if bk.t.weekday() >= 4:
                ok = False
                break
            if direction > 0 and not (bk.c > sweep_extreme):
                ok = False
                break
            if direction < 0 and not (bk.c < sweep_extreme):
                ok = False
                break
        if not ok:
            continue
        n_accept += 1

        entry_i = i + A_ACCEPT_BARS
        entry_bar = h1[entry_i]
        if entry_bar.t.hour not in A_ENTRY_HOURS:
            continue
        day = entry_bar.t.strftime("%Y-%m-%d")
        if day_count[day] >= A_MAX_DAY:
            continue

        entry = entry_bar.c
        a_e = atr(h1, entry_i)
        if direction > 0:
            sl = sweep_extreme - A_SL_BUF_ATR * a_e
        else:
            sl = sweep_extreme + A_SL_BUF_ATR * a_e
        risk = abs(entry - sl)
        if risk <= 0 or risk > 3.0 * a_e:
            continue
        tp = entry + direction * A_RR * risk
        pnl = simulate(h1, entry_i, direction, entry, sl, tp, A_MAX_HOLD, A_FLAT_HOUR)
        pnls.append(pnl)
        day_count[day] += 1

    scr = screen(pnls)
    return {
        "hypothesis_id": "HYP-H1-PDLIQ-STOPRUN-ACCEPT-001",
        "thesis": "prior_day_liq_stoprun_multibar_continuation_accept",
        "de_dup": (
            "NOT AsianSweep/EQHL reclaim (opposite: continuation beyond extreme); "
            "NOT PDH-break immediate first-close; NOT PDH-retest reject; "
            "NOT LondonORB-accept (no ORB box); NOT ASR kill family"
        ),
        "tf": "H1",
        "params": {
            "rr": A_RR,
            "sweep_atr": A_SWEEP_ATR,
            "accept_bars": A_ACCEPT_BARS,
            "entry_hours": "08-15",
            "max_day": A_MAX_DAY,
        },
        "funnel": {"n_stoprun": n_sweep, "n_accept_geom": n_accept, "n_trades": scr["metrics"]["n"]},
        **scr,
    }


def probe_b_lny_range_accept(m15: list[Bar], d1: list[Bar]) -> dict:
    """LondonNY-class: redefine quality event as London range expansion + accept break."""
    # Index D1 ATR by date (prior completed day)
    d1_atr: dict = {}
    for i, b in enumerate(d1):
        if i < 14:
            continue
        # ATR on D1 ending at i
        trs = []
        for j in range(i - 13, i + 1):
            prev = d1[j - 1].c
            trs.append(max(d1[j].h - d1[j].l, abs(d1[j].h - prev), abs(d1[j].l - prev)))
        d1_atr[b.t.date()] = sum(trs) / 14.0

    # Group M15 by calendar day
    by_day: dict[str, list[int]] = defaultdict(list)
    for i, b in enumerate(m15):
        by_day[b.t.strftime("%Y-%m-%d")].append(i)

    pnls: list[float] = []
    day_count: dict[str, int] = defaultdict(int)
    n_expansion = 0
    n_armed = 0

    for day_str, idxs in by_day.items():
        if not idxs:
            continue
        day_dt = datetime.strptime(day_str, "%Y-%m-%d")
        if day_dt.weekday() >= 4:  # Mon-Thu only a priori shelf standard (not mined)
            continue
        # Prior D1 ATR
        prior = day_dt.date() - timedelta(days=1)
        # walk back to last available D1 atr
        a_d1 = None
        for back in range(1, 6):
            key = (day_dt - timedelta(days=back)).date()
            if key in d1_atr and d1_atr[key] > 0:
                a_d1 = d1_atr[key]
                break
        if a_d1 is None:
            continue

        # London window bars [9,12)
        ldn = [i for i in idxs if B_LDN_START <= m15[i].t.hour < B_LDN_END]
        if len(ldn) < 4:
            continue
        ldn_h = max(m15[i].h for i in ldn)
        ldn_l = min(m15[i].l for i in ldn)
        ldn_range = ldn_h - ldn_l
        if ldn_range < B_RANGE_ATR * a_d1:
            continue
        n_expansion += 1

        # Measure close = last London bar close; directional outer third
        last_ldn = m15[ldn[-1]]
        if ldn_range <= 0:
            continue
        close_pos = (last_ldn.c - ldn_l) / ldn_range
        if close_pos >= (1.0 - B_CLOSE_FRAC):
            direction = 1
            level = ldn_h
        elif close_pos <= B_CLOSE_FRAC:
            direction = -1
            level = ldn_l
        else:
            continue
        n_armed += 1

        # Entry search: 2 consecutive M15 closes beyond London extreme in [13,18)
        entry_idxs = [
            i
            for i in idxs
            if B_ENTRY_START <= m15[i].t.hour < B_ENTRY_END and i > ldn[-1]
        ]
        for j in range(len(entry_idxs) - (B_ACCEPT_BARS - 1)):
            window = entry_idxs[j : j + B_ACCEPT_BARS]
            ok = True
            for wi in window:
                bk = m15[wi]
                if direction > 0 and not (bk.c > level):
                    ok = False
                    break
                if direction < 0 and not (bk.c < level):
                    ok = False
                    break
            if not ok:
                continue
            entry_i = window[-1]
            if day_count[day_str] >= B_MAX_DAY:
                break
            entry = m15[entry_i].c
            if direction > 0:
                sl = ldn_l - B_SL_BUF_ATR * a_d1
            else:
                sl = ldn_h + B_SL_BUF_ATR * a_d1
            risk = abs(entry - sl)
            if risk <= 0 or risk > 2.5 * a_d1:
                continue
            tp = entry + direction * B_RR * risk
            pnl = simulate(m15, entry_i, direction, entry, sl, tp, B_MAX_HOLD, B_FLAT_HOUR)
            pnls.append(pnl)
            day_count[day_str] += 1
            break  # one trade per day

    scr = screen(pnls)
    return {
        "hypothesis_id": "HYP-LNY-RANGE-ACCEPT-M15-001",
        "thesis": "london_range_expansion_event_then_multibar_accept_break",
        "de_dup": (
            "NOT LondonNY PB entry (event=expansion+accept-break, not bias+pullback); "
            "NOT LNY DualWin window densify (single entry window [13,18)); "
            "NOT S530 Mon/day mine; NOT LondonORB ORB-box; NOT IB-overlap densify"
        ),
        "tf": "M15",
        "params": {
            "rr": B_RR,
            "london": f"{B_LDN_START}-{B_LDN_END}",
            "range_atr_d1": B_RANGE_ATR,
            "close_frac": B_CLOSE_FRAC,
            "accept_bars": B_ACCEPT_BARS,
            "entry_window": f"{B_ENTRY_START}-{B_ENTRY_END}",
            "days": "Mon-Thu_a_priori_shelf",
            "max_day": B_MAX_DAY,
        },
        "funnel": {
            "n_expansion_days": n_expansion,
            "n_armed_bias": n_armed,
            "n_trades": scr["metrics"]["n"],
        },
        **scr,
    }


def write_dedup() -> None:
    DEDUP_MD.write_text(
        """# De-dup clearance — Stop-run accept + LNY range-accept (V2)

Date: 2026-07-14  
Authority: Structural rebuild offline-first; GPT waived  
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## A — `HYP-H1-PDLIQ-STOPRUN-ACCEPT-001`

| Prior | Mechanism | Relation |
|---|---|---|
| AsianSweep reclaim **KILL** N=0 | Asia H/L pierce → close-inside → reclaim fade | **Opposite** trade: continuation beyond sweep extreme, not reclaim |
| EQHL sweep-reclaim **KILL intake** | EQH/EQL pierce → reclaim | Same reclaim archetype; A is continuation accept |
| H1SwingFailure / SFP **KILL** | Pivot pierce → close back inside | Fade/SFP; A requires closes **beyond** extreme |
| PDH-break **PARK** | Immediate M15 close beyond PDH/PDL | A requires stop-run wick + **2 H1** closes beyond **sweep extreme** |
| PDH-retest **KILL** | Break → retest+reject | A has no retest leg |
| LondonORB-accept **PARK** | ORB box accept | No ORB construction |

Independence: multi-bar **continuation acceptance after PDH/PDL stop-run** on H1 —
new object vs reclaim family and vs immediate PDH-break.

## B — `HYP-LNY-RANGE-ACCEPT-M15-001`

| Prior | Mechanism | Relation |
|---|---|---|
| EA_LondonNY S529/S544 | London ATR bias → NY **pullback** | Event redefined: London **range expansion** + outer-third close → **accept-break** of London H/L |
| LNY DualWin **KILL** | Same PB entry; two windows | B keeps **one** window [13,18); changes entry object |
| LondonORB / IB-overlap | ORB/IB box break | London full-measure-window range, not ORB/IB |
| S530 day-skip | Mon/Wed mine | **Banned**; Mon–Thu shelf standard only |

Independence: quality-event definition change (expansion+accept), not hour/day densify.

## Banned from these readouts

Hour/day mine · RR retune · DualWin third window · reclaim rescue · Phase-0 compose reopen.
""",
        encoding="utf-8",
    )


def write_md(result: dict) -> None:
    a = result["probe_a"]
    b = result["probe_b"]
    lines = [
        "# Structural rebuild offline probes V2",
        "",
        f"Generated: {result['generated_at']}",
        "Authority: Owner R&D continue; offline-first; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        f"De-dup: `{DEDUP_MD.name}`",
        "",
        "## Probe A — stop-run → multi-bar acceptance",
        "",
        f"- ID: `{a['hypothesis_id']}`",
        f"- Symbol/TF: `{result['symbol']}` / H1",
        f"- Funnel: {a['funnel']}",
        f"- N={a['metrics']['n']} PF={a['metrics']['pf']} tpw={a['metrics']['tpw']} exp={a['metrics']['exp']}",
        f"- Cost x1.5 PF={a['cost_stress']['x1_5']['pf']} exp={a['cost_stress']['x1_5']['exp']}",
        f"- Kill notes: {a['kill_notes']}",
        f"- **Verdict: `{a['verdict']}`** · model0={a['model0']}",
        "",
        "## Probe B — LondonNY thick event redefinition",
        "",
        f"- ID: `{b['hypothesis_id']}`",
        f"- Symbol/TF: `{result['symbol']}` / M15",
        f"- Funnel: {b['funnel']}",
        f"- N={b['metrics']['n']} PF={b['metrics']['pf']} tpw={b['metrics']['tpw']} exp={b['metrics']['exp']}",
        f"- Cost x1.5 PF={b['cost_stress']['x1_5']['pf']} exp={b['cost_stress']['x1_5']['exp']}",
        f"- Kill notes: {b['kill_notes']}",
        f"- **Verdict: `{b['verdict']}`** · model0={b['model0']}",
        "",
        "## Board",
        "",
        f"| Probe | Verdict | Model 0 |",
        f"|---|---|---|",
        f"| A stop-run accept | `{a['verdict']}` | `{a['model0']}` |",
        f"| B LNY range-accept | `{b['verdict']}` | `{b['model0']}` |",
        "",
        f"Offline survivors: `{result['offline_survivors']}`",
        f"Any Model 0 authorized: `{result['any_model0_authorized']}`",
        "",
        "## Phase-0 compose",
        "",
        "Not reopened. Still `BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW`.",
        "",
        "## Best shelf",
        "",
        "RR2 `20260714_194548` unchanged.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    write_dedup()
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        sym, h1 = load_bars(("USDJPY", "USDJPY+", "USDJPYm", "USDJPY."), mt5.TIMEFRAME_H1)
        _, d1 = load_bars((sym,), mt5.TIMEFRAME_D1)
        _, m15 = load_bars((sym,), mt5.TIMEFRAME_M15)
    finally:
        mt5.shutdown()

    probe_a = probe_a_stoprun_accept(h1, d1)
    probe_b = probe_b_lny_range_accept(m15, d1)
    survivors = [
        p["hypothesis_id"]
        for p in (probe_a, probe_b)
        if p["verdict"] == "PROBE_SURVIVOR"
    ]
    result = {
        "schema": "structural_rebuild_offline_probes.v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "Owner_structural_rebuild_offline_first",
        "gpt": "waived",
        "demo_discovery_diminishing_returns": True,
        "best_shelf": "20260714_194548",
        "symbol": sym,
        "de_dup_path": str(DEDUP_MD.relative_to(ROOT)).replace("\\", "/"),
        "probe_a": probe_a,
        "probe_b": probe_b,
        "phase0_compose": {
            "status": "BLOCKED_REQUIRES_CLEAN_FUTURE_FREEZE_REVIEW",
            "reopened": False,
        },
        "banned_densify": [
            "MaxKZ/RR/SB/Spark",
            "ATR%ile/Asia-box/NY-IB hours",
            "ASR/EQHL reclaim rescue",
            "PDH-break/retest retune",
            "LNY DualWin window densify",
            "S530 Mon/day mine",
            "Wave1-5 killed/parked",
            "Phase-0 compose without Owner clear",
        ],
        "offline_survivors": survivors,
        "any_model0_authorized": bool(survivors),
    }
    raw = json.dumps(result, indent=2, sort_keys=False)
    # attach sha after write
    OUT_JSON.write_text(raw, encoding="utf-8")
    digest = sha256_file(OUT_JSON)
    result["result_sha256"] = digest
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_md(result)
    print(
        json.dumps(
            {
                "symbol": sym,
                "probe_a": {
                    "n": probe_a["metrics"]["n"],
                    "pf": probe_a["metrics"]["pf"],
                    "tpw": probe_a["metrics"]["tpw"],
                    "x1_5": probe_a["cost_stress"]["x1_5"]["pf"],
                    "verdict": probe_a["verdict"],
                    "kills": probe_a["kill_notes"],
                },
                "probe_b": {
                    "n": probe_b["metrics"]["n"],
                    "pf": probe_b["metrics"]["pf"],
                    "tpw": probe_b["metrics"]["tpw"],
                    "x1_5": probe_b["cost_stress"]["x1_5"]["pf"],
                    "verdict": probe_b["verdict"],
                    "kills": probe_b["kill_notes"],
                },
                "survivors": survivors,
                "sha": digest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
