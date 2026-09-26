"""prefreeze_2g.py - 2G STEP 1c/1d/1e (NO holdout bar may be loaded).

1c  relative-cap arm table: per calendar year of DESIGN and VALIDATION
    for XAUUSD - signals rejected by the fixed cap vs the relative cap
    (trailing 250-trading-day median daily range), AM counts under each.
1d  power: block-bootstrap (4-week) HOLDOUT-size (174 wk) samples from
    VALIDATION E0' trades; P(every gate passes). (i) as-is, (ii) R
    shifted to pooled PF_R 1.15. STOP RULE if (i) < 0.60.
1e  freeze: sha256 of every src/ file + the run scripts + swap/census
    code; written to out/freeze_2g_hashes.csv and LAB_LOG.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd

from src import data as dm
from src import runner
from src import swap_adj
from src.components import stops_targets as st
from src.variants.registry import CONFIGS
from validation_2f import pf, mc_dd
from holdout_2g import mdr250_xau

CFG = [c for c in CONFIGS if c["id"] == "F2_NH_b"][0]
SYMS = ["EURUSD", "XAUUSD"]
BLK = 28 * 86400
NRES, SEED = 2000, 20260924
HOLDOUT_WEEKS = (dm.COMMON_END - dm.VALIDATION_END) / (7 * 86400)
NBLOCKS = int(np.ceil(HOLDOUT_WEEKS / 4))


def cap_table():
    """1c: XAUUSD cap binding per year, DESIGN + VALIDATION."""
    ctx = runner.get_ctx("XAUUSD", 15)
    eur_ctx = runner.get_ctx("EURUSD", 15)
    mdr_eur = st.median_daily_range_pips(
        eur_ctx.tf, dm.DESIGN[0], dm.DESIGN[1], "EURUSD")
    mult = 120.0 / mdr_eur
    cap = runner.sl_cap(ctx, "XAUUSD")
    mdr250 = mdr250_xau(ctx)
    rows = []
    for wlo, whi, wname in ((dm.DESIGN[0], dm.DESIGN[1], "DESIGN"),
                            (dm.VALIDATION[0], dm.VALIDATION[1],
                             "VALIDATION")):
        oo = runner.orders_for(ctx, CFG, wlo, whi, None)
        sigs = np.array([int(ctx.tf["t"][o["t"]]) for o in oo])
        hh = dm.london_parts(sigs)[0]
        yr = pd.to_datetime(pd.Series(sigs), unit="s").dt.year
        for o, sc, h_, y_ in zip(oo, sigs, hh, yr):
            rows.append({"window": wname, "year": int(y_),
                         "sig_ctm": sc,
                         "risk": abs(o["entry"] - o["sl"]),
                         "day": int(sc // 86400), "am": 7 <= h_ < 12})
    df = pd.DataFrame(rows)
    out = []
    for (wname, y), g in df.groupby(["window", "year"]):
        rc = g["day"].map(lambda d: mult * mdr250.get(d, np.nan))
        out.append({"sym": "XAUUSD", "window": wname, "year": int(y),
                    "n_sig": len(g),
                    "rej_fixed": int((g.risk > cap).sum()),
                    "rej_rel": int((g.risk > rc).sum()),
                    "am_fixed": int((g.am & (g.risk <= cap)).sum()),
                    "am_rel": int((g.am & (g.risk <= rc)).sum()),
                    "relcap_med_px": float(
                        (mult * mdr250.reindex(g.day).median()))})
    r = pd.DataFrame(out)
    r.to_csv("out/cap_table_2g.csv", index=False)
    print(f"[1c] fixed_cap={cap:.2f}px mult={mult:.3f}")
    print(r.to_string(index=False), flush=True)
    return r


def _blocks(ctm, lo):
    return ((ctm - lo) // BLK).astype(np.int64)


def power():
    """1d: P(every gate passes) over 174-week resamples of VALIDATION
    E0' trades. G4 uses the FL pool (AM vs PM); PF gates use FR H1 AM.
    Approximation notes printed with the table."""
    rng = np.random.default_rng(SEED)
    lo, hi = dm.VALIDATION
    fr = pd.concat([pd.read_csv(
        f"out/trades_2fval_{s}_AMONLY_e0s_e1.csv") for s in SYMS],
        ignore_index=True)
    fl = pd.concat([pd.read_csv(
        f"out/trades_2fval_{s}_X0-HOLD_e0s_e1.csv") for s in SYMS],
        ignore_index=True)
    b_fr = _blocks(fr.fill_ctm.to_numpy(), lo)
    b_fl = _blocks(fl.fill_ctm.to_numpy(), lo)
    ub_fr = np.unique(b_fr); ub_fl = np.unique(b_fl)
    rows_fr = [np.nonzero(b_fr == u)[0] for u in ub_fr]
    rows_fl = [np.nonzero(b_fl == u)[0] for u in ub_fl]
    # part-year week bounds inside a 174-week holdout (server dates):
    bounds_wk = {"2023": (0, 32), "2024": (32, 84),
                 "2025": (84, 136), "2026": (136, 174)}
    base_pos = fr.r_x1[fr.r_x1 > 0].sum()
    base_neg = -fr.r_x1[fr.r_x1 < 0].sum()
    delta = (1.15 * base_neg - base_pos) / \
        (int((fr.r_x1 > 0).sum()) + 1.15 * int((fr.r_x1 < 0).sum()))
    print(f"[1d] n_fr={len(fr)} base PF_R={base_pos/base_neg:.4f} "
          f"shift={delta:.4f}", flush=True)
    cnt = np.zeros(6); gate_pass = np.zeros((2, 8))
    for i in range(NRES):
        draw = rng.integers(0, len(ub_fr), NBLOCKS)
        sel = np.concatenate([rows_fr[j] for j in draw])
        draw_f = rng.integers(0, len(ub_fl), NBLOCKS)
        self_ = np.concatenate([rows_fl[j] for j in draw_f])
        for k, shift in enumerate((0.0, delta)):
            r = fr.iloc[sel].copy()
            r["r_x1"] = r["r_x1"] + shift
            r["r_x15"] = r["r_x15"] + shift
            g1 = pf(r.r_x1) >= 1.10 and r.r_x1.mean() > 0
            # A1G: G1b replaces G1r (one-time, LEAD_NOTE_7). Remove the
            # single largest winner of EACH symbol (2 trades), then
            # pooled PF_R >= 1.05. G1r kept as reporting-only.
            keep = np.ones(len(r), dtype=bool)
            rr = r.r_x1.to_numpy()
            for s in SYMS:
                pos = np.nonzero((r.sym == s).to_numpy())[0]
                keep[pos[np.argmax(rr[pos])]] = False
            g1b = pf(r.r_x1[keep]) >= 1.05
            g1r = pf(r.loc[np.abs(r.r_x1) <= 5, "r_x1"]) >= 1.05
            g2 = pf(swap_adj.swap_adj_r(r, 2.0, "r_x15")) >= 1.00
            g3 = all(pf(r.loc[r.sym == s, "r_x1"]) > 1.00
                     for s in SYMS)
            rf = fl.iloc[self_].copy()
            rf["r_x1"] = rf["r_x1"] + shift
            a_ = rf.am_pm == "AM"
            g4 = (rf.loc[a_, "r_x1"].mean()
                  - rf.loc[~a_, "r_x1"].mean()) > 0
            g5a = mc_dd(r.r_x1.to_numpy()) <= 50
            # part-years: lay the resampled R series on the 174-wk
            # calendar in order, split at part-year week boundaries
            # (2023~32wk, 2024~52, 2025~52, 2026~38 of 174)
            vals = r.r_x1.to_numpy()
            seg_bounds = [0]
            for a, b in bounds_wk.values():
                seg_bounds.append(seg_bounds[-1] + (b - a))
            seg_bounds = np.round(
                np.array(seg_bounds) / seg_bounds[-1]
                * len(vals)).astype(int)
            py = sum(vals[seg_bounds[i]:seg_bounds[i + 1]].sum() > 0
                     for i in range(4))
            g5b = py >= 3
            gs = [g1, g1b, g2, g3, g4, g5a, g5b]
            for j, gg in enumerate(gs + [g1r]):
                gate_pass[k, j] += bool(gg)
            cnt[k] += all(gs)
    for k, tag in ((0, "as-is"), (1, "shift->PF1.15")):
        print(f"[1d {tag}] P(all gates)={cnt[k]/NRES:.3f} | per-gate: "
              + " ".join(f"{n}={gate_pass[k,j]/NRES:.2f}" for j, n in
                         enumerate("G1 G1b G2 G3 G4 G5a G5b".split()))
              + f" | reporting G1r={gate_pass[k,7]/NRES:.2f}",
              flush=True)
    if cnt[0] / NRES < 0.60:
        print("[1d] STOP RULE: P(i) < 0.60 - stop before STEP 2",
              flush=True)
    return cnt[0] / NRES, gate_pass / NRES


def concentration(fr, tag):
    """A1G reporting: share of net R from the top 1% / top 5% of
    trades (payoff concentration) + old-G1r PF on the base data."""
    r = fr.r_x1.to_numpy()
    net = r.sum()
    for q in (0.01, 0.05):
        k = max(1, int(np.ceil(len(r) * q)))
        top = np.sort(r)[-k:].sum()
        print(f"[conc {tag}] top{q:.0%} of {len(r)} trades = {top:.1f}R "
              f"/ net {net:.1f}R = {top/net:.3f}", flush=True)
    print(f"[conc {tag}] old-G1r PF (|R|>5 removed) = "
          f"{pf(r[np.abs(r) <= 5]):.3f}", flush=True)


def freeze_a1g():
    """A1G re-freeze: hash every changed/new file; write
    out/freeze_2g_hashes_a1g.csv; report diff vs the original freeze
    (out/freeze_2g_hashes.csv stays untouched)."""
    import hashlib
    old = pd.read_csv("out/freeze_2g_hashes.csv")
    oldmap = {p.replace("/", os.sep): h
              for p, h in zip(old.file, old.sha256)}
    files = set(oldmap)
    for root, _, fns in os.walk("src"):
        for fn in fns:
            if fn.endswith(".py"):
                files.add(os.path.join(root, fn).replace("/", os.sep))
    files.update(p.replace("/", os.sep) for p in [
        "runs/holdout_2g.py", "runs/census_2g.py",
        "runs/prefreeze_2g.py", "src/swap_adj.py",
        "src/spike.py", "src/e0.py", "LEAD_NOTE_7.md",
        "tests/test_spike_2g.py"])
    rows, changed, added = [], [], []
    for p in sorted(files):
        pn = p.replace("/", os.sep)
        if not os.path.exists(pn):
            continue
        h = hashlib.sha256(open(pn, "rb").read()).hexdigest()
        rows.append({"file": pn, "sha256": h})
        if pn not in oldmap:
            added.append(pn)
        elif oldmap[pn] != h:
            changed.append(pn)
    df = pd.DataFrame(rows)
    df.to_csv("out/freeze_2g_hashes_a1g.csv", index=False)
    print(f"[a1g-freeze] {len(df)} files | changed={changed} "
          f"| added={added}", flush=True)
    return df, changed, added


def main_a1g():
    t00 = time.time()
    fr = pd.concat([pd.read_csv(
        f"out/trades_2fval_{s}_AMONLY_e0s_e1.csv") for s in SYMS],
        ignore_index=True)
    concentration(fr, "VALIDATION")
    print("[a1g] step B: power with G1b", flush=True)
    power()
    print("[a1g] step C: re-freeze hashes", flush=True)
    freeze_a1g()
    print(f"[a1g] done {time.time()-t00:.0f}s", flush=True)


def freeze_hashes():
    import hashlib
    rows = []
    for root, _, files in os.walk("src"):
        for fn in sorted(files):
            if fn.endswith((".py",)):
                p = os.path.join(root, fn)
                rows.append({"file": p,
                             "sha256": hashlib.sha256(
                                 open(p, "rb").read()).hexdigest()})
    for p in ["runs/holdout_2g.py", "runs/census_2g.py",
              "runs/prefreeze_2g.py", "src/swap_adj.py",
              "src/e0.py"]:
        if os.path.exists(p):
            rows.append({"file": p,
                         "sha256": hashlib.sha256(
                             open(p, "rb").read()).hexdigest()})
    df = pd.DataFrame(rows).drop_duplicates("file")
    df.to_csv("out/freeze_2g_hashes.csv", index=False)
    print(f"[1e] froze {len(df)} file hashes", flush=True)
    return df


def main():
    t00 = time.time()
    print("[prefreeze] step 1c: XAU cap table (D+V)", flush=True)
    cap_table()
    print("[prefreeze] step 1d: power", flush=True)
    p, per = power()
    print("[prefreeze] step 1e: freeze hashes", flush=True)
    freeze_hashes()
    print(f"[prefreeze] done {time.time()-t00:.0f}s", flush=True)


if __name__ == "__main__":
    main()
