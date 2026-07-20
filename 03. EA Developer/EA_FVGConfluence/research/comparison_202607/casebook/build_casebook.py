#!/usr/bin/env python3
"""Build the deterministic, outcome-blind EURUSD M5 comparison casebook."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from casebook_contract import (
    CASEBOOK_DIR,
    HOLDOUT,
    M1_PATH,
    PROTOCOL_PATH,
    SEED,
    SOURCE_PATH,
    STRATA,
    STUDY_ID,
    ContractError,
    casebook_code_binding,
    load_m1_pre_holdout,
    mt5_atr,
    packet_file_hashes,
    resample_ohlc,
    sha256_file,
    signal_identity,
    source_binding,
    stable_rank,
    write_json,
)

PIP = 0.0001
EMULATOR_CONTRACT = {
    "schema_version": "fvg_source_emulator.v1",
    "decision": "new M5 bar; all signal inputs are closed bars",
    "lookback": 30,
    "atr_period": 14,
    "atr_variant": "atr_mt5_parity_proven_sma_true_range",
    "minimum_gap_pips": 10.0,
    "minimum_body_atr": 0.80,
    "minimum_body_range": 0.55,
    "maximum_fill_fraction": 0.50,
    "entry_depth": [0.40, 0.60],
    "entry_mode": "rejection_or_mid_gap",
    "minimum_confluence": 3,
    "session_hard_filter": True,
    "confluence": ["H1_alignment", "nearby_order_block", "premium_discount", "liquidity_sweep", "session"],
    "ob_search_bars": 8,
    "ob_max_distance_atr": 0.75,
    "pd_lookback": 40,
    "pivot_lr": 2,
    "sweep_lookback": 12,
    "h1_lookback": 40,
}


def assert_source_contract_literals() -> None:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    include = (SOURCE_PATH.parent / "Include/FVG_Risk.mqh").read_text(encoding="utf-8")
    required_source = (
        "InpFVGLookback        = 30",
        "InpMinBodyATR         = 0.80",
        "InpMinBodyRange       = 0.55",
        "InpMaxFillPct         = 0.50",
        "InpMinConfluence      = 3",
        "InpOBSearchBars       = 8",
        "InpOBMaxDistATR       = 0.75",
        "InpPDLookback         = 40",
        "InpPivotLR            = 2",
        "InpSweepLookback      = 12",
        "InpHTFLookback        = 40",
        "InpATRPeriod          = 14",
    )
    missing = [token for token in required_source if token not in source]
    if 'out_pack.min_gap_pips = 10.0' not in include:
        missing.append("EURUSD min gap 10.0")
    if missing:
        raise ContractError(f"source/emulator literal drift: {missing}")


def _zone_at(o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
             f: int, atr: float, min_gap: float, min_body_atr: float,
             min_body_range: float) -> dict[str, Any] | None:
    if f < 2:
        return None
    impulse = f - 1
    rng = h[impulse] - l[impulse]
    if not np.isfinite(atr) or rng <= 0:
        return None
    body = abs(c[impulse] - o[impulse])
    if not (body >= atr * min_body_atr or body / rng >= min_body_range):
        return None
    if h[f - 2] < l[f] and l[f] - h[f - 2] >= min_gap:
        return {"direction": 1, "bottom": h[f - 2], "top": l[f], "formed_index": f}
    if l[f - 2] > h[f] and l[f - 2] - h[f] >= min_gap:
        return {"direction": -1, "bottom": h[f], "top": l[f - 2], "formed_index": f}
    return None


def _acceptable_mitigation(zone: dict[str, Any], h: np.ndarray, l: np.ndarray,
                           start: int, end: int, maximum: float) -> bool:
    bottom, top = zone["bottom"], zone["top"]
    gap = top - bottom
    if gap <= 0 or start > end:
        return False
    fill = 0.0
    for k in range(start, end + 1):
        if zone["direction"] == 1 and l[k] < top:
            depth = top - min(top, max(l[k], bottom))
            if h[k] < bottom:
                depth = gap
            fill = max(fill, depth)
        elif zone["direction"] == -1 and h[k] > bottom:
            depth = max(bottom, min(h[k], top)) - bottom
            if l[k] > top:
                depth = gap
            fill = max(fill, depth)
    fraction = fill / gap
    return fraction < 0.999 and fraction <= maximum


def _interacts(zone: dict[str, Any], h: np.ndarray, l: np.ndarray, j: int) -> bool:
    return not (h[j] < zone["bottom"] or l[j] > zone["top"])


def _rejection_or_mid(zone: dict[str, Any], o: np.ndarray, h: np.ndarray,
                      l: np.ndarray, c: np.ndarray, j: int) -> bool:
    rng = h[j] - l[j]
    if rng <= 0 or j < 1:
        return False
    body = abs(c[j] - o[j])
    upper = h[j] - max(o[j], c[j])
    lower = min(o[j], c[j]) - l[j]
    if zone["direction"] == 1:
        pin = lower >= rng * 0.55 and body <= rng * 0.35 and c[j] > o[j]
        engulf = c[j] > o[j] and c[j] >= max(o[j - 1], c[j - 1]) and o[j] <= min(o[j - 1], c[j - 1])
        strong = c[j] > o[j] and body / rng >= 0.60
        depth = (zone["top"] - c[j]) / (zone["top"] - zone["bottom"])
    else:
        pin = upper >= rng * 0.55 and body <= rng * 0.35 and c[j] < o[j]
        engulf = c[j] < o[j] and c[j] <= min(o[j - 1], c[j - 1]) and o[j] >= max(o[j - 1], c[j - 1])
        strong = c[j] < o[j] and body / rng >= 0.60
        depth = (c[j] - zone["bottom"]) / (zone["top"] - zone["bottom"])
    return pin or engulf or strong or 0.40 <= depth <= 0.60


def _is_pivot(h: np.ndarray, l: np.ndarray, idx: int, lr: int, high: bool) -> bool:
    if idx - lr < 0 or idx + lr >= len(h):
        return False
    if high:
        return not (np.any(h[idx - lr:idx] >= h[idx]) or np.any(h[idx + 1:idx + lr + 1] > h[idx]))
    return not (np.any(l[idx - lr:idx] <= l[idx]) or np.any(l[idx + 1:idx + lr + 1] < l[idx]))


def _last_swings(h: np.ndarray, l: np.ndarray, t: np.ndarray, last_closed: int,
                 lookback: int = 40, lr: int = 2) -> tuple[float, Any, float, Any] | None:
    got_h = got_l = None
    newest = last_closed - lr
    oldest = max(lr, last_closed + 1 - lookback)
    for idx in range(newest, oldest - 1, -1):
        if got_h is None and _is_pivot(h, l, idx, lr, True):
            got_h = (h[idx], t[idx])
        if got_l is None and _is_pivot(h, l, idx, lr, False):
            got_l = (l[idx], t[idx])
        if got_h is not None and got_l is not None:
            return got_h[0], got_h[1], got_l[0], got_l[1]
    return None


def _bias(h: np.ndarray, l: np.ndarray, c: np.ndarray, t: np.ndarray,
          last_closed: int) -> int:
    swings = _last_swings(h, l, t, last_closed)
    if swings is None:
        return 0
    sh, th, sl, tl = swings
    oldest = max(0, last_closed + 1 - 40)
    for idx in range(last_closed, oldest - 1, -1):
        if t[idx] <= th and t[idx] <= tl:
            break
        if c[idx] > sh and t[idx] > th:
            return 1
        if c[idx] < sl and t[idx] > tl:
            return -1
    mid = 0.5 * (sh + sl)
    return 1 if c[last_closed] > mid else (-1 if c[last_closed] < mid else 0)


def _session(server_time: pd.Timestamp) -> str | None:
    minute = server_time.hour * 60 + server_time.minute
    if 8 * 60 <= minute < 12 * 60:
        return "LONDON"
    if 13 * 60 <= minute < 17 * 60:
        return "NEW_YORK"
    return None


def _score(zone: dict[str, Any], i: int, m5: pd.DataFrame, h1: pd.DataFrame,
           atr: np.ndarray, arrays: tuple[np.ndarray, ...]) -> tuple[int, dict[str, bool]]:
    o, h, l, c, t = arrays
    j = i - 1
    decision = m5["time_utc"].iloc[i]
    h1_last = int(np.searchsorted(h1["bar_close_utc"].to_numpy(), np.datetime64(decision), side="right") - 1)
    hh, hl, hc = (h1[k].to_numpy(float) for k in ("high", "low", "close"))
    ht = h1["time_utc"].to_numpy()
    htf = h1_last >= 5 and _bias(hh, hl, hc, ht, h1_last) == zone["direction"]

    ob = False
    f = zone["formed_index"]
    # MQL scans start=formed_shift+2 through start+search_bars inclusive:
    # the origin candle plus eight older candles, nine candidates total.
    for idx in range(f - 2, max(-1, f - 11), -1):
        if idx < 0:
            break
        if zone["direction"] == 1 and c[idx] < o[idx] and abs(h[idx] - zone["bottom"]) <= atr[j] * 0.75:
            ob = True
            break
        if zone["direction"] == -1 and c[idx] > o[idx] and abs(l[idx] - zone["top"]) <= atr[j] * 0.75:
            ob = True
            break

    swings = _last_swings(h, l, t, j)
    pd_aligned = sweep = False
    if swings is not None:
        sh, _, sl, _ = swings
        eq = 0.5 * (sh + sl)
        pd_aligned = c[j] <= eq if zone["direction"] == 1 else c[j] >= eq
        for idx in range(j, max(-1, j - 12), -1):
            if zone["direction"] == 1 and l[idx] < sl and c[idx] > sl:
                sweep = True
                break
            if zone["direction"] == -1 and h[idx] > sh and c[idx] < sh:
                sweep = True
                break
    session_ok = _session(pd.Timestamp(m5["time_server"].iloc[i])) is not None
    flags = {"htf_aligned": htf, "order_block": ob, "premium_discount": pd_aligned,
             "liquidity_sweep": sweep, "session_ok": session_ok}
    return sum(flags.values()), flags


def extract_candidate_pools(m5: pd.DataFrame, h1: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    o, h, l, c = (m5[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    t = m5["time_utc"].to_numpy()
    atr = mt5_atr(m5)
    pools = {name: [] for name in STRATA}
    start = int(np.searchsorted(t, np.datetime64("2019-01-01")))
    end = int(np.searchsorted(t, np.datetime64(HOLDOUT), side="left"))
    for i in range(max(start, 50), end):
        decision = pd.Timestamp(t[i])
        if decision.year not in (2019, 2020, 2021, 2022):
            continue
        j = i - 1
        exact = loose = None
        for s in range(2, 31):
            f = i - s
            z = _zone_at(o, h, l, c, f, atr[j], 10 * PIP, 0.80, 0.55)
            # Exact current-source semantics: FVG_FindLatestZone calls
            # FVG_IsAcceptableMitigation(z, 1, ...), whose descending loop
            # evaluates shift=1 only.  Do not silently substitute the broader
            # comment/intended lifetime check for the hash-bound specimen.
            if z is not None and _acceptable_mitigation(z, h, l, j, j, 0.50):
                exact = z
                break
        ea_ok = False
        exact_score = 0
        exact_flags: dict[str, bool] = {}
        if exact is not None and _interacts(exact, h, l, j) and _rejection_or_mid(exact, o, h, l, c, j):
            exact_score, exact_flags = _score(exact, i, m5, h1, atr, (o, h, l, c, t))
            ea_ok = exact_flags["session_ok"] and exact_score >= 3

        if not ea_ok:
            for s in range(2, 31):
                f = i - s
                z = _zone_at(o, h, l, c, f, atr[j], 1 * PIP, 0.40, 0.30)
                if z is not None and _acceptable_mitigation(z, h, l, f + 1, j, 0.75) and _interacts(z, h, l, j):
                    loose = z
                    break

        session = _session(pd.Timestamp(m5["time_server"].iloc[i]))
        common = {
            "decision_time_utc": decision.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decision_time_server": pd.Timestamp(m5["time_server"].iloc[i]).strftime("%Y-%m-%dT%H:%M:%S"),
            "split": "calibration" if decision.year <= 2021 else "evaluation",
            "session": session or "OTHER",
        }
        if ea_ok and exact is not None:
            pools[STRATA[0]].append({**common, **exact, "ea_accept": True,
                                     "formed_time_utc": pd.Timestamp(t[exact["formed_index"]]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "source_score": exact_score, "source_flags": exact_flags})
        elif loose is not None:
            pools[STRATA[1]].append({**common, **loose, "ea_accept": False,
                                     "formed_time_utc": pd.Timestamp(t[loose["formed_index"]]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                     "source_score": exact_score, "source_flags": exact_flags,
                                     "reject_reason": "fails_exact_source_core"})
        else:
            f = i - 2
            if f >= 2:
                rng = h[f - 1] - l[f - 1]
                body = abs(c[f - 1] - o[f - 1])
                if rng > 0 and (body / rng >= 0.30 or body >= atr[j] * 0.40):
                    choices: list[tuple[int, float, float]] = []
                    bull_overlap = h[f - 2] - l[f]
                    bear_overlap = h[f] - l[f - 2]
                    if 0 <= bull_overlap <= 3 * PIP:
                        mid = 0.5 * (h[f - 2] + l[f])
                        choices.append((1, mid - 0.5 * PIP, mid + 0.5 * PIP))
                    if 0 <= bear_overlap <= 3 * PIP:
                        mid = 0.5 * (h[f] + l[f - 2])
                        choices.append((-1, mid - 0.5 * PIP, mid + 0.5 * PIP))
                    for direction, bottom, top in choices:
                        z = {"direction": direction, "bottom": bottom, "top": top, "formed_index": f}
                        if _interacts(z, h, l, j):
                            pools[STRATA[2]].append({**common, **z, "ea_accept": False,
                                                     "formed_time_utc": pd.Timestamp(t[z["formed_index"]]).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                     "source_score": 0, "source_flags": {},
                                                     "reject_reason": "wick_overlap_near_miss"})
                            break
    return pools


def _balanced_pick(rows: list[dict[str, Any]], n: int, seed: int, salt: str,
                   used_times: set[str], used_signals: set[tuple[str, int, str, str]]) -> list[dict[str, Any]]:
    eligible = [r for r in rows if r["session"] in {"LONDON", "NEW_YORK"}
                and r["decision_time_utc"] not in used_times and signal_identity(r) not in used_signals]
    # Gray-code order keeps both direction and session margins within one for
    # every partial four-cell cycle (when all cells have supply).
    cells = [(1, "LONDON"), (-1, "NEW_YORK"), (-1, "LONDON"), (1, "NEW_YORK")]
    queues = {(d, s): stable_rank([r for r in eligible if r["direction"] == d and r["session"] == s], seed, f"{salt}|{d}|{s}")
              for d, s in cells}
    picked: list[dict[str, Any]] = []
    while len(picked) < n:
        progressed = False
        for cell in cells:
            while queues[cell] and (queues[cell][0]["decision_time_utc"] in used_times
                                    or signal_identity(queues[cell][0]) in used_signals):
                queues[cell].pop(0)
            if queues[cell] and len(picked) < n:
                row = queues[cell].pop(0)
                picked.append(row)
                used_times.add(row["decision_time_utc"])
                used_signals.add(signal_identity(row))
                progressed = True
        if not progressed:
            break
    if len(picked) < n:
        remainder = stable_rank([r for r in rows if r["decision_time_utc"] not in used_times
                                 and signal_identity(r) not in used_signals], seed, salt + "|remainder")
        for row in remainder:
            if len(picked) >= n:
                break
            if signal_identity(row) in used_signals:
                continue
            picked.append(row)
            used_times.add(row["decision_time_utc"])
            used_signals.add(signal_identity(row))
    return picked


def select_casebook(pools: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    audit: dict[str, Any] = {"seed": SEED, "splits": {}}
    used_times: set[str] = set()
    used_signals: set[tuple[str, int, str, str]] = set()
    for split, total in (("calibration", 100), ("evaluation", 300)):
        split_pools = {s: [r for r in pools[s] if r["split"] == split] for s in STRATA}
        base = total // 3
        targets = {s: base for s in STRATA}
        for s in STRATA[: total - base * 3]:
            targets[s] += 1
        # Deterministic even reallocation if a stratum is supply constrained.
        deficit = 0
        for s in STRATA:
            available = len({signal_identity(r) for r in split_pools[s]})
            if available < targets[s]:
                deficit += targets[s] - available
                targets[s] = available
        while deficit:
            progressed = False
            for s in STRATA:
                available = len({signal_identity(r) for r in split_pools[s]})
                if targets[s] < available and deficit:
                    targets[s] += 1
                    deficit -= 1
                    progressed = True
            if not progressed:
                raise ContractError(f"insufficient total supply for {split}: requested={total}")
        counts = {}
        selected_rows_by_stratum: dict[str, list[dict[str, Any]]] = {}
        for s in STRATA:
            got = _balanced_pick(split_pools[s], targets[s], SEED, f"{split}|{s}", used_times, used_signals)
            if len(got) != targets[s]:
                raise ContractError(f"selection shortage split={split} stratum={s}")
            for row in got:
                raw = f"{STUDY_ID}|{split}|{row['decision_time_utc']}".encode()
                row = dict(row)
                row["case_id"] = "FVG-" + hashlib.sha256(raw).hexdigest()[:16].upper()
                row["stratum"] = s
                identity = {key: row[key] for key in ("case_id", "split", "decision_time_utc", "formed_time_utc",
                                                       "direction", "stratum", "bottom", "top")}
                row["event_sha256"] = hashlib.sha256(
                    json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest().upper()
                selected.append(row)
            counts[s] = len(got)
            selected_rows_by_stratum[s] = got
        balance = {}
        for s, rows in selected_rows_by_stratum.items():
            direction_counts = {str(d): sum(r["direction"] == d for r in rows) for d in (1, -1)}
            session_counts = {name: sum(r["session"] == name for r in rows) for name in ("LONDON", "NEW_YORK")}
            balance[s] = {"direction": direction_counts, "session": session_counts,
                          "direction_max_difference": abs(direction_counts["1"] - direction_counts["-1"]),
                          "session_max_difference": abs(session_counts["LONDON"] - session_counts["NEW_YORK"])}
        pool_counts = {s: len(split_pools[s]) for s in STRATA}
        pool_unique_signal_counts = {s: len({signal_identity(r) for r in split_pools[s]}) for s in STRATA}
        pool_balance = {}
        for s, rows in split_pools.items():
            pool_balance[s] = {
                "direction": {str(d): sum(r["direction"] == d for r in rows) for d in (1, -1)},
                "session": {name: sum(r["session"] == name for r in rows) for name in ("LONDON", "NEW_YORK", "OTHER")},
            }
        deviations = []
        if split == "evaluation" and counts[STRATA[0]] < total // 3:
            exact_n = counts[STRATA[0]]
            deficit_n = total // 3 - exact_n
            deviations.append({"code": f"EVAL_STRATUM_BALANCE_UNMET_UNIQUE_EXACT_EA_POOL_N{exact_n}",
                               "reason": f"unique exact source-derived EA signal-core supply is {exact_n}; all are retained and the {deficit_n}-case deficit is evenly reallocated",
                               "economic_gate_effect": "fail_closed_until_protocol_accepts_recorded_reallocation; never claim equal-stratum balance"})
        if split == "evaluation" and balance[STRATA[0]]["session_max_difference"] > 1:
            ea_sessions = balance[STRATA[0]]["session"]
            deviations.append({"code": f"EVAL_EA_SESSION_BALANCE_UNMET_UNIQUE_SELECTION_LONDON{ea_sessions['LONDON']}_NEW_YORK{ea_sessions['NEW_YORK']}",
                               "reason": f"after enforcing one row per FVG, exact EA-core selection is London={ea_sessions['LONDON']} and New_York={ea_sessions['NEW_YORK']}",
                               "economic_gate_effect": "partial_fail_closed; preserve imbalance in paired analysis and never claim session balance"})
        if split == "evaluation" and balance[STRATA[0]]["direction_max_difference"] > 1:
            ea_directions = balance[STRATA[0]]["direction"]
            deviations.append({"code": f"EVAL_EA_DIRECTION_BALANCE_UNMET_UNIQUE_SELECTION_LONG{ea_directions['1']}_SHORT{ea_directions['-1']}",
                               "reason": f"after enforcing one row per FVG, exact EA-core selection is long={ea_directions['1']} and short={ea_directions['-1']}",
                               "economic_gate_effect": "partial_fail_closed; preserve imbalance in paired analysis and never claim direction balance"})
        audit["splits"][split] = {"requested": total, "pool_counts": pool_counts,
                                  "pool_unique_signal_counts": pool_unique_signal_counts,
                                  "pool_direction_session_supply": pool_balance,
                                  "selected_counts": counts,
                                  "selection_weights_over_unique_signals": {s: counts[s] / pool_unique_signal_counts[s] if pool_unique_signal_counts[s] else None for s in STRATA},
                                  "reallocation": {s: counts[s] - (total // 3) for s in STRATA},
                                  "direction_session_balance": balance, "protocol_deviations": deviations,
                                  "fully_equal_strata": len(set(counts.values())) == 1}
    selected.sort(key=lambda r: r["case_id"])
    if (len(selected) != 400 or len({r["decision_time_utc"] for r in selected}) != 400
            or len({signal_identity(r) for r in selected}) != 400):
        raise ContractError("selected casebook is not exactly 400 unique decisions and FVG identities")
    return selected, audit


def _draw_panel(ax: Any, frame: pd.DataFrame, title: str) -> None:
    for x, row in enumerate(frame.itertuples(index=False)):
        color = "#1f6f5b" if row.close >= row.open else "#a33b3b"
        ax.vlines(x, row.low, row.high, color=color, linewidth=0.55)
        lo, hi = sorted((row.open, row.close))
        ax.add_patch(plt.Rectangle((x - 0.32, lo), 0.64, max(hi - lo, 1e-8), color=color, linewidth=0))
    ax.set_title(title, fontsize=8)
    ax.grid(alpha=0.12)
    ax.set_xlim(-1, len(frame))
    ticks = list(range(0, len(frame), max(1, len(frame) // 5)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([pd.Timestamp(frame["time_utc"].iloc[x]).strftime("%m-%d %H:%M") for x in ticks], fontsize=6)
    ax.tick_params(axis="y", labelsize=6)


def render_blinded_charts(selected: list[dict[str, Any]], views: dict[int, pd.DataFrame], packet: Path) -> list[dict[str, Any]]:
    chart_dir = packet / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    results = []
    windows = {5: 96, 15: 80, 60: 72}
    for row in selected:
        decision = pd.Timestamp(row["decision_time_utc"].replace("Z", ""))
        panels: list[tuple[int, pd.DataFrame]] = []
        cutoffs = {}
        for minutes in (5, 15, 60):
            view = views[minutes]
            closed = view[view["bar_close_utc"] <= decision].tail(windows[minutes]).copy()
            if len(closed) < windows[minutes] // 2 or closed["bar_close_utc"].max() > decision:
                raise ContractError(f"insufficient/future chart bars for {row['case_id']} M{minutes}")
            panels.append((minutes, closed))
            cutoffs[f"M{minutes if minutes < 60 else 'H1'}"] = pd.Timestamp(closed["bar_close_utc"].max()).strftime("%Y-%m-%dT%H:%M:%SZ")
        fig, axes = plt.subplots(3, 1, figsize=(10, 9), dpi=100)
        for ax, (minutes, frame) in zip(axes, panels):
            label = "H1" if minutes == 60 else f"M{minutes}"
            _draw_panel(ax, frame, f"{row['case_id']} | {label} | closed information only")
        fig.suptitle(f"{row['case_id']} | information cutoff {row['decision_time_utc']}", fontsize=9)
        fig.tight_layout()
        out = chart_dir / f"{row['case_id']}.png"
        fig.savefig(out, metadata={"Software": "AlphaFactory FVG blinded casebook v1"})
        plt.close(fig)
        results.append({"case_id": row["case_id"], "chart": f"charts/{out.name}", "sha256": sha256_file(out),
                        "bytes": out.stat().st_size, "decision_cutoff_utc": row["decision_time_utc"],
                        "last_closed_bar_by_timeframe": cutoffs, "future_bars_drawn": 0})
    return results


def _write_reviewer_files(selected: list[dict[str, Any]], packet: Path, internal_sha256: str) -> None:
    fields = ["schema_version", "study_id", "source_sha256", "internal_casebook_sha256", "event_sha256",
              "case_id", "chart", "setup_label", "confidence_1_to_5", "reason_codes",
              "native_order_type", "native_entry", "native_stop", "native_target", "notes"]
    for reviewer in (1, 2):
        path = packet / f"REVIEWER_{reviewer}_OVERLAY.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in selected:
                writer.writerow({"schema_version": "fvg_reviewer_overlay.v2", "study_id": STUDY_ID,
                                 "source_sha256": sha256_file(SOURCE_PATH),
                                 "internal_casebook_sha256": internal_sha256,
                                 "event_sha256": row["event_sha256"],
                                 "case_id": row["case_id"], "chart": f"charts/{row['case_id']}.png"})
        attestation = {
            "schema_version": "fvg_reviewer_attestation.v2",
            "study_id": STUDY_ID,
            "reviewer_id": f"REVIEWER_{reviewer}",
            "reviewer_name": "",
            "ict_fvg_experience_years": "",
            "verified_live_history_months": "",
            "journaled_trade_count": "",
            "qualification_evidence_reference": "",
            "attests_independent_review_without_outcomes": False,
            "attests_no_second_reviewer_labels_seen": False,
            "signed_name": "",
            "signed_date_utc": "",
        }
        write_json(packet / f"REVIEWER_{reviewer}_ATTESTATION.json", attestation)
    guide = """# Blinded review instructions\n\nReview every chart independently using only information shown through its cutoff.\nAllowed setup labels are `ACCEPT`, `REJECT`, and `UNCERTAIN`; blank is invalid.\nDo not obtain future charts, outcomes, the EA decision, or the other reviewer's labels.\nIf `ACCEPT`, optional native order fields may declare MARKET/LIMIT and entry/stop/target.\nDo not change case IDs or chart paths. Complete and sign the separate attestation.\n"""
    (packet / "REVIEW_INSTRUCTIONS.md").write_text(guide, encoding="utf-8", newline="\n")


def build(packet: Path, render: bool = True, reuse_charts: bool = False) -> dict[str, Any]:
    assert_source_contract_literals()
    binding = source_binding()
    m1 = load_m1_pre_holdout()
    views = {minutes: resample_ohlc(m1, minutes) for minutes in (5, 15, 60)}
    pools = extract_candidate_pools(views[5], views[60])
    selected, selection_audit = select_casebook(pools)
    packet.mkdir(parents=True, exist_ok=True)
    # Generated output is reproducible: remove only this builder's generated children.
    cleanup_names = ["REVIEWER_1_OVERLAY.csv", "REVIEWER_2_OVERLAY.csv",
                 "REVIEWER_1_ATTESTATION.json", "REVIEWER_2_ATTESTATION.json",
                 "REVIEW_INSTRUCTIONS.md", "PACKET_MANIFEST.json"]
    if not reuse_charts:
        cleanup_names.extend(["charts", "CHART_MANIFEST.json"])
    for name in cleanup_names:
        target = packet / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    internal = CASEBOOK_DIR / "CASEBOOK_INTERNAL.json"
    payload = {
        "schema_version": "fvg_casebook_internal.v2",
        "study_id": STUDY_ID,
        "outcome_columns_present": False,
        "holdout_rows_loaded": 0,
        "maximum_loaded_time_utc": pd.Timestamp(m1["time_utc"].max()).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_binding": binding,
        "casebook_code_binding": casebook_code_binding(),
        "data": {"m1_path": M1_PATH.relative_to(M1_PATH.parents[4]).as_posix(), "m1_sha256": sha256_file(M1_PATH)},
        "emulator_contract": EMULATOR_CONTRACT,
        "selection_audit": selection_audit,
        "cases": selected,
    }
    write_json(internal, payload)
    if reuse_charts:
        existing = json.loads((packet / "CHART_MANIFEST.json").read_text(encoding="utf-8"))
        chart_rows = existing.get("charts", [])
        if {r.get("case_id") for r in chart_rows} != {r["case_id"] for r in selected}:
            raise ContractError("cannot reuse charts: selected case IDs changed")
        for chart in chart_rows:
            path = packet / chart["chart"]
            if not path.is_file() or sha256_file(path) != chart["sha256"]:
                raise ContractError(f"cannot reuse missing/tampered chart: {chart.get('case_id')}")
    else:
        chart_rows = render_blinded_charts(selected, views, packet) if render else []
    if not render:
        raise ContractError("production packet requires rendered charts")
    internal_sha256 = sha256_file(internal)
    _write_reviewer_files(selected, packet, internal_sha256)
    write_json(packet / "CHART_MANIFEST.json", {"schema_version": "fvg_blinded_chart_manifest.v1", "study_id": STUDY_ID,
                                                "outcome_columns_present": False, "direction_columns_present": False,
                                                "charts": chart_rows})
    manifest = {
        "schema_version": "fvg_owner_label_packet.v2",
        "study_id": STUDY_ID,
        "deterministic_seed": SEED,
        "case_count": len(selected),
        "blinding": {"direction_present": False, "stratum_present": False, "ea_decision_present": False,
                     "outcome_present": False, "future_bars_present": False},
        "bindings": {"protocol_sha256": sha256_file(PROTOCOL_PATH), "source_sha256": sha256_file(SOURCE_PATH),
                     "m1_sha256": sha256_file(M1_PATH), "internal_casebook_sha256": sha256_file(internal)},
        "files": packet_file_hashes(packet, {"PACKET_MANIFEST.json"}),
    }
    write_json(packet / "PACKET_MANIFEST.json", manifest)
    return {"case_count": len(selected), "pool_counts": {k: len(v) for k, v in pools.items()},
            "selection_audit": selection_audit, "packet": str(packet)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--reuse-charts", action="store_true", help="reuse only exact hash-verified charts for unchanged case IDs")
    args = ap.parse_args()
    print(json.dumps(build(args.packet, reuse_charts=args.reuse_charts), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
