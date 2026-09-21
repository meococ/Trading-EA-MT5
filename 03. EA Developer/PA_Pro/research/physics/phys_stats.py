"""phys_stats — strata tables, paired cluster bootstrap, BH, gate logic.

Implements `PHYSICS_PREREG_DRAFT.md` sections 6-7 and the pre-declared winner
rule of the frozen prereg.  Pure statistics; no prices are read here.

Paired difference (per cell):
    d_e = bounce_cond(real_e) - mean_k(bounce_cond(control_e,k))
with `bounce_cond` = 1 for BOUNCE, 0 for BREAK, undefined for NONE.  A pair is
kept only when the real event resolved AND at least one control resolved;
undefined pairs are dropped and counted.  The cell statistic is mean(d_e); the
CI is the percentile paired cluster bootstrap over real events (B=10000,
seed 20260920), each event carrying its own control set.
"""

import math

import numpy as np
from scipy.stats import binomtest

import phys_common as pc

__all__ = [
    "enrich", "cell_stats", "bootstrap_paired", "gate_verdict",
    "table_rows", "bh_across", "sign_test",
]


def enrich(events, results, bounds=None):
    """Attach outcome columns + strength tercile to event rows (in place copy)."""
    rows = []
    for e, r in zip(events, results):
        row = dict(e)
        row.update(r)
        if bounds is not None and bounds[0] == bounds[0]:
            row["tercile"] = _tercile(float(e["strength"]), bounds)
        else:
            row["tercile"] = "na"
        rows.append(row)
    return rows


def _tercile(s, bounds):
    q33, q67 = bounds
    if s <= q33:
        return "bot"
    if s <= q67:
        return "mid"
    return "top"


def _bounce_value(row):
    o = row["outcome"]
    if o == "BOUNCE":
        return 1.0
    if o == "BREAK":
        return 0.0
    return None


def _cont_value(row):
    if row["outcome"] != "BREAK":
        return None
    o = row.get("cont_outcome")
    if o == "CONT":
        return 1.0
    if o == "RETURN":
        return 0.0
    return None


def _pairs(rows_real, rows_ctrl, control_index, value_fn):
    """[(d_e, k_e)] for each real row with >=1 resolved control and resolved real."""
    out = []
    dropped_real = dropped_ctrl = 0
    for i, row in enumerate(rows_real):
        vr = value_fn(row)
        if vr is None:
            dropped_real += 1
            continue
        vals = []
        for k in control_index.get(i, ()):  # indices into rows_ctrl
            vk = value_fn(rows_ctrl[k])
            if vk is not None:
                vals.append(vk)
        if not vals:
            dropped_ctrl += 1
            continue
        out.append((vr - float(np.mean(vals)), float(np.mean(vals)), len(vals)))
    return out, {"dropped_real": dropped_real, "dropped_ctrl": dropped_ctrl}


def build_control_index(anchor_idx, n_real):
    idx = {}
    for k, a in enumerate(anchor_idx):
        idx.setdefault(int(a), []).append(k)
    return idx


def cell_stats(rows_real, rows_ctrl, value_fn, n_boot=10000, seed=pc.SEED):
    """Paired D, bootstrap CI and p for one cell."""
    idx = {}
    for k, r in enumerate(rows_ctrl):
        idx.setdefault(int(r.get("anchor_i", -1)), []).append(k)
    pairs, drop = _pairs(rows_real, rows_ctrl, idx, value_fn)
    n = len(pairs)
    if n == 0:
        return {"n": 0, "D": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "p": float("nan"), "drop": drop, "ctrl_mean": float("nan"),
                "real_mean": float("nan")}
    d = np.asarray([p[0] for p in pairs], dtype=np.float64)
    cm = float(np.mean([p[1] for p in pairs]))
    rm = cm + float(d.mean())
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        take = rng.integers(0, n, size=n)
        boots[b] = d[take].mean()
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p = (1.0 + float(np.sum(boots <= 0.0))) / (n_boot + 1.0)
    return {"n": n, "D": float(d.mean()), "lo": float(lo), "hi": float(hi),
            "p": float(p), "drop": drop, "ctrl_mean": cm, "real_mean": rm}


def _pairs_empty(rows_real, value_fn):
    out = []
    dropped = 0
    for row in rows_real:
        v = value_fn(row)
        if v is None:
            dropped += 1
    return out, {"dropped_real": dropped, "dropped_ctrl": 0}


def bootstrap_paired(d, n_boot=10000, seed=pc.SEED):
    d = np.asarray(d, dtype=np.float64)
    n = d.shape[0]
    if n == 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        take = rng.integers(0, n, size=n)
        boots[b] = d[take].mean()
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p = (1.0 + float(np.sum(boots <= 0.0))) / (n_boot + 1.0)
    return float(d.mean()), float(lo), float(hi), float(p)


def sign_test(d):
    d = np.asarray(d, dtype=np.float64)
    nz = d[d != 0]
    if nz.size == 0:
        return {"n_pos": 0, "n_nonzero": 0, "p": float("nan")}
    n_pos = int(np.sum(nz > 0))
    res = binomtest(n_pos, int(nz.size), 0.5, alternative="two-sided")
    return {"n_pos": n_pos, "n_nonzero": int(nz.size), "p": float(res.pvalue)}


def bh_across(pvals, q=0.05):
    p = np.asarray([x if np.isfinite(x) else 1.0 for x in pvals], dtype=np.float64)
    n = p.shape[0]
    if n == 0:
        return {"qvalues": [], "rejected": []}
    order = np.argsort(p, kind="stable")
    ranked = p[order]
    qv = ranked * n / (np.arange(n) + 1)
    qv = np.minimum.accumulate(qv[::-1])[::-1]
    qv = np.clip(qv, 0.0, 1.0)
    out = np.empty(n, dtype=np.float64)
    out[order] = qv
    return {"qvalues": out.tolist(), "rejected": (out <= q).tolist(), "q": q}


def gate_verdict(cell_top, monotone, sym_signs, year_signs):
    """LINES MATTER gate (respect or continuation analogue), draft section 7."""
    n_sym_pos = int(sum(1 for v in sym_signs.values() if v > 0))
    n_sym = len(sym_signs)
    n_yr_pos = int(sum(1 for v in year_signs.values() if v > 0))
    n_yr = len(year_signs)
    checks = {
        "D_top_ge_5pp": bool(np.isfinite(cell_top["D"]) and cell_top["D"] >= 0.05),
        "ci_lo_gt_0": bool(np.isfinite(cell_top["lo"]) and cell_top["lo"] > 0.0),
        "monotone": bool(monotone),
        # R02-A F4: no lenient "all-of-3" fallbacks; the charter rules are
        # >= 3/4 symbols and >= 4/6 years and nothing weaker.
        "symbols_3of4": bool(n_sym >= 4 and n_sym_pos >= 3),
        "years_4of6": bool(n_yr >= 6 and n_yr_pos >= 4),
    }
    return {"pass": bool(all(checks.values())), "checks": checks,
            "n_sym_pos": n_sym_pos, "n_sym": n_sym,
            "n_yr_pos": n_yr_pos, "n_yr": n_yr}


def table_rows(rows, by, value_fn):
    """[(cell, n, wins, rate, wilson_lo, wilson_hi)] for a stratum key."""
    groups = {}
    for r in rows:
        v = value_fn(r)
        if v is None:
            continue
        groups.setdefault(r.get(by, "?"), []).append(v)
    out = []
    for key in sorted(groups, key=lambda x: str(x)):
        vals = groups[key]
        n = len(vals)
        k = int(sum(vals))
        lo, hi = pc.wilson_ci(k, n)
        out.append((key, n, k, k / n if n else float("nan"), lo, hi))
    return out
