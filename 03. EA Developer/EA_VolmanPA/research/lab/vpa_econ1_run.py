"""VPA-ECON-1 — the ONE verdict run (prereg SHA 644DBCBA…).

DR3-accepted signals (one detector run, frozen code) + matched-random entries
(K=20, cell-matched) through the frozen fill/exit engine across the cost
scenarios; outputs PLAN/econ1/*. No VAL/OOS/HOLDOUT anywhere (G5).
"""

import csv
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PKG = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(PKG, "PLAN", "econ1")

from vpa_data import load_m5_bars  # noqa: E402
from vpa_random_baseline import load_m5, eu_server_offset_hours  # noqa: E402
from vpa_dr1 import run_dr1, DR3_CFG  # noqa: E402
from vpa_econ1_random import match_random, session_of  # noqa: E402
from vpa_econ1_sim import build_ctx, simulate_entries, metrics, newcombe_diff  # noqa: E402
from vpa_econ1_costs import COST_SCENARIOS  # noqa: E402

PREREG_SHA = "644DBCBA91B9859AF598906C8BB9C7D8CAB034CBCE99675554B48938C5BE9663"
DR3_CODE_SHA = "73497484E2C26EDF44DAE5F1D574C56BBF40BBBFE8192A05AD38B4D782A781E0"
K_RANDOM = 20
SEED = 20260920
GATES = {
    "PF_x1": (">", 1.30), "PF_x15": (">=", 1.25), "PF_x2": (">=", 1.00),
    "gross_PF": (">=", 1.10), "N": (">=", 500), "max_dd": ("<=", 6.0), "b": (">=", 1.70),
    "lift_x1": (">=", 14.1), "lift_x2": (">=", 18.2),
}


def iso_utc(epoch):
    naive = pd.to_datetime([int(epoch) + 300], unit="s", utc=False)
    off = eu_server_offset_hours(naive)[0]
    return (naive[0] - pd.Timedelta(hours=int(off))).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_next_end(starts, mask, n_m1):
    """M1 index where the session containing each M5 bar ends (repo convention)."""
    n = len(mask)
    next_end = np.full(n, n_m1, dtype=np.int64)
    cur = n_m1
    for j in range(n - 1, -1, -1):
        if mask[j]:
            next_end[j] = cur
        else:
            cur = starts[j]
    return next_end


def main():
    os.makedirs(OUT, exist_ok=True)
    bars = load_m5_bars("EURUSD")                      # DESIGN 2016-2021 (loader defaults)
    m1, m5b, m5_t, starts, sess_mask = load_m5("EURUSD")
    assert len(m5_t) == len(bars["t"]) and np.array_equal(m5_t, bars["t"]), "M5 frames misaligned"
    pip = bars["pip"]
    t0, t1 = bars["t"][0], bars["t"][-1]
    span = {"first_bar_utc": iso_utc(t0), "last_bar_utc": iso_utc(t1),
            "n_m5": int(len(bars["t"])), "n_m1": int(len(m1["t"]))}
    print("[frame]", span, flush=True)

    cfg = dict(DR3_CFG, round_grid_price=50.0 * pip, collect_gates=True)
    recs, cnt = run_dr1(bars, cfg=cfg)
    acc = [r for r in recs if r.get("executable")]
    print(f"[signals] records {len(recs)} accepted {len(acc)}", flush=True)

    sig_entries = []
    for i, r in enumerate(acc):
        g = r.get("gates") or {}
        anti = (g.get("anti_chase", {}).get("value") or {})
        feat = {"room_r": (None if r.get("room_r") in (None, float("inf")) else r.get("room_r")),
                "ema_dist_atr": anti.get("ema_dist_atr"), "squeeze": int(bool(r.get("squeeze"))),
                "lunch": int(bool(r.get("lunch"))), "session": r.get("session"),
                "setup": r.get("setup"), "side": int(r["side"]),
                "pressure": int(bool(r.get("pressure"))),
                "chop_window": ((g.get("chop", {}).get("value") or {}).get("chop_window")),
                "year": datetime.datetime.utcfromtimestamp(int(bars["t"][r["bar_idx"]])).year}
        sig_entries.append({"sig": int(r["bar_idx"]), "side": int(r["side"]),
                            "inv": r.get("invalidation"), "atr": r.get("atr"),
                            "tag": i, "feat": feat})

    signals = [{"bar_idx": e["sig"], "side": e["side"]} for e in sig_entries]
    picks = match_random(signals, bars, K=K_RANDOM, seed=SEED)
    # signals whose SIGNAL bar is out of session contribute no random rows
    # (the DR3 session gate is measured at the trigger bar, so a few signal
    # bars sit outside the windows); lift is computed on the matched subset.
    kept = [i for i, e in enumerate(sig_entries) if session_of(bars["utc_min"][e["sig"]]) is not None]
    assert len(picks) == len(kept) * K_RANDOM, "matched-random rows misaligned"
    kept_set = set(kept)
    rnd_entries = [{"sig": int(p[0]), "side": int(p[1]), "tag": kept[i // K_RANDOM]} for i, p in enumerate(picks)]
    print(f"[random] entries {len(rnd_entries)} (K={K_RANDOM}); matched signals {len(kept)}/{len(sig_entries)}", flush=True)

    mask_any = sess_mask["london"] | sess_mask["ny"]
    next_end = compute_next_end(starts, mask_any, len(m1["t"]))
    ctx = build_ctx(m1, m5b, m5_t, starts, pip, next_end=next_end)

    results = {"scenarios": {}, "signals": len(acc), "random_entries": len(rnd_entries)}
    trades_rows = []
    random_rows = []
    status = {}
    for name, mult in COST_SCENARIOS.items():
        tr_s = simulate_entries(sig_entries, ctx, mult=mult)
        tr_r = simulate_entries(rnd_entries, ctx, mult=mult)
        ms = metrics(tr_s)
        ms_m = metrics([t for t in tr_s if t.get("tag") in kept_set])
        mr = metrics(tr_r)
        sc = {}
        for t in tr_s:
            sc[t["status"]] = sc.get(t["status"], 0) + 1
        status[name] = sc
        k1, n1 = round(ms_m["WR"] * ms_m["N"]), ms_m["N"]
        k2, n2 = round(mr["WR"] * mr["N"]), mr["N"]
        d, lo, hi = newcombe_diff(k1, n1, k2, n2)
        results["scenarios"][name] = {"signals": ms, "signals_matched": ms_m, "random": mr,
                                      "lift_pp": round(d * 100, 2),
                                      "lift_ci_pp": [round(lo * 100, 2), round(hi * 100, 2)]}
        print(f"[{name}] N={ms['N']} WR={ms['WR']:.4f} PF={ms['PF']:.3f} b={ms['b']:.3f} "
              f"dd={ms['max_dd_pct']:.2f}% | rand N={mr['N']} WR={mr['WR']:.4f} "
              f"lift={d*100:+.2f}pp CI[{lo*100:+.2f},{hi*100:+.2f}]", flush=True)
        if name == "x1":
            for t in tr_s:
                if t.get("status") != "FILLED":
                    continue
                e = sig_entries[t["tag"]]
                f = e["feat"]
                trades_rows.append({
                    "signal_bar_idx": t["sig"], "side": "long" if t["side"] > 0 else "short",
                    "session": f["session"], "setup": f["setup"], "year": f["year"],
                    "entry": round(t["stop"], 6), "invalidation": round(e["inv"], 6) if e["inv"] else None,
                    "fill_server_t": t["fill_t"], "fill_utc": iso_utc(t["fill_t"]),
                    "fill": round(t["fill"], 6), "sl": round(t["sl"], 6), "tp": round(t["tp"], 6),
                    "exit_server_t": t["exit_t"], "exit_utc": iso_utc(t["exit_t"]),
                    "exit": round(t["exit_px"], 6), "reason": t["reason"], "r": round(t["r"], 6),
                    "cost_mult": mult, "cost_pips": t["cost_pips"],
                    "gap_atr": (round(t["gap_atr"], 3) if t["gap_atr"] is not None else None),
                    "room_r": (round(f["room_r"], 3) if f["room_r"] is not None else None),
                    "ema_dist_atr": f["ema_dist_atr"], "squeeze": f["squeeze"],
                    "lunch": f["lunch"], "pressure": f["pressure"], "chop_window": f["chop_window"],
                })
            for t in tr_r:
                if t.get("status") != "FILLED":
                    continue
                random_rows.append({
                    "entry_bar_idx": t["sig"], "side": "long" if t["side"] > 0 else "short",
                    "src_signal_bar_idx": sig_entries[t["tag"]]["sig"],
                    "fill": round(t["fill"], 6), "exit": round(t["exit_px"], 6),
                    "reason": t["reason"], "r": round(t["r"], 6),
                    "cost_mult": mult, "cost_pips": t["cost_pips"],
                })
    results["status_counts"] = status
    results["frame"] = span
    results["prereg_sha"] = PREREG_SHA
    results["dr3_code_sha"] = DR3_CODE_SHA

    with open(os.path.join(OUT, "TRADES_DESIGN.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(trades_rows[0].keys()))
        w.writeheader(); w.writerows(trades_rows)
    with open(os.path.join(OUT, "RANDOM_MATCHED.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(random_rows[0].keys()))
        w.writeheader(); w.writerows(random_rows)
    with open(os.path.join(OUT, "ECON1_METRICS.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, default=str)
    print("[write]", OUT, "trades", len(trades_rows), "random fills", len(random_rows), flush=True)
    return results


if __name__ == "__main__":
    main()
