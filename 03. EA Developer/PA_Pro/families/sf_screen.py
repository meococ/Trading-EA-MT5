"""sf_screen.py — governed screen for one SF01 family.

Runs every config of the family's GRID through ``pa_eval.evaluate`` (the only
economic path; each call self-logs to the ledger), then applies the charter
section-8 SCREEN gates and writes:

  rounds/SF01/<family>/SCREEN.json   — full per-config metrics + gates
  rounds/SF01/<family>/SCREEN.md     — human-readable table + verdict draft

Usage: python sf_screen.py <family_module> [--only i,j,...] [--tag NAME]
"""

import importlib
import itertools
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
PA_PRO = os.path.dirname(HERE)
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_slots      # noqa: E402
import pa_eval       # noqa: E402
import pa_stats      # noqa: E402
import sf_spec       # noqa: E402
import sf_provider   # noqa: E402

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
TIERS = ["x1", "x1.5", "x2"]
YEARS = [2016, 2017, 2018, 2019, 2020, 2021]


def grid_configs(grid):
    keys = sorted(grid.keys())
    out = []
    for vals in itertools.product(*(grid[k] for k in keys)):
        out.append(dict(zip(keys, vals)))
    return out


def _p_from_t(t):
    """Two-sided normal-approx p-value of a t-stat (df large)."""
    if t is None or not np.isfinite(t):
        return 1.0
    return math.erfc(abs(float(t)) / math.sqrt(2.0))


def _neighbors(cfg, grid):
    """All Hamming-1 neighbours of cfg inside the grid."""
    out = []
    for k, vals in grid.items():
        for v in vals:
            if v != cfg[k]:
                nb = dict(cfg)
                nb[k] = v
                out.append(nb)
    return out


def extract(res, cfg):
    """Flatten one evaluate() result into gate fields."""
    t1 = res["tiers"]["x1"]
    ms = t1["strategy"]
    mr = t1.get("random") or {}
    x2 = res["tiers"]["x2"]["strategy"]
    py = ms.get("per_year") or {}
    ps = ms.get("per_symbol") or {}
    n_years_pos = sum(1 for y in YEARS
                      if (py.get(y) or py.get(str(y)) or {}).get("PF")
                      and (py.get(y) or py.get(str(y)))["PF"] > 1.0)
    year_r = {int(y): (py.get(y) or py.get(str(y)) or {}).get("R_total", 0.0)
              for y in YEARS}
    r_tot = ms.get("R_total") or 0.0
    max_year_share = ms.get("largest_year_share")
    sym_pos = sum(1 for s in SYMBOLS
                  if (ps.get(s) or {}).get("exp_r")
                  and ps[s]["exp_r"] > 0)
    em = ms.get("exit_mix") or {}
    n_fill = ms.get("N") or 0
    return {
        "params": cfg,
        "n_signals": res.get("signals"),
        "N": n_fill,
        "exp_r_x1": ms.get("exp_r"),
        "t_x1": ms.get("t"),
        "PF_x1": ms.get("PF"),
        "PF_x15": res["tiers"]["x1.5"]["strategy"].get("PF"),
        "PF_x2": x2.get("PF"),
        "exp_r_x2": x2.get("exp_r"),
        "WR_x1": ms.get("WR"),
        "b_x1": ms.get("b"),
        "R_total_x1": r_tot,
        "max_dd_pct": ms.get("max_dd_pct"),
        "rand_N": mr.get("N"),
        "rand_exp_r": mr.get("exp_r"),
        "rand_PF": mr.get("PF"),
        "lift_pp": t1.get("lift_pp"),
        "lift_ci_pp": t1.get("lift_ci_pp"),
        "years_pf_pos": n_years_pos,
        "year_R": year_r,
        "max_year_share": max_year_share,
        "symbols_pos": sym_pos,
        "per_symbol_expr": {s: (ps.get(s) or {}).get("exp_r") for s in SYMBOLS},
        "top5_share_net": ms.get("top5_share_of_net"),
        "top5_share_gross": ms.get("top5_share_of_gross"),
        "time_exit_share": ms.get("time_exit_share"),
        "trades_per_week": ms.get("trades_per_week"),
        "exit_mix": em,
        "status_counts": ms.get("status_counts"),
        "p_norm": _p_from_t(ms.get("t")),
        "ledger_trials": res.get("ledger_trials"),
        "data_sha256": res.get("data_sha256"),
        "elapsed_s": res.get("elapsed_s"),
    }


def gates(row, all_rows, grid):
    """Charter section-8 SCREEN gates. Returns {gate: pass, ...} + reason."""
    g = {}
    g["n300"] = bool(row["N"] and row["N"] >= 300)
    g["exp_t"] = bool(row["exp_r_x1"] is not None and row["exp_r_x1"] > 0
                      and row["t_x1"] is not None and row["t_x1"] >= 2.5)
    g["bh_q"] = bool(row.get("q") is not None and row["q"] <= 0.10)
    g["pf"] = bool(row["PF_x1"] is not None and row["PF_x1"] >= 1.15
                   and row["PF_x2"] is not None and row["PF_x2"] >= 1.00)
    g["lift"] = bool(row["lift_ci_pp"] and row["lift_ci_pp"][0] > 0)
    g["years"] = row["years_pf_pos"] >= 4
    g["symbols"] = row["symbols_pos"] >= 3
    # plateau: EVERY +-1-step neighbour in the grid must have PF x1 >= 1.05
    idx = {json.dumps(r["params"], sort_keys=True): r for r in all_rows}
    nbs = []
    for nb in _neighbors(row["params"], grid):
        r = idx.get(json.dumps(nb, sort_keys=True))
        if r is not None:
            nbs.append(r["PF_x1"])
    g["plateau"] = bool(nbs) and all(
        v is not None and v >= 1.05 for v in nbs)
    g["plateau_nb_n"] = len(nbs)
    g["concentration"] = bool(
        (row["top5_share_net"] is None or row["top5_share_net"] <= 0.30)
        and (row["max_year_share"] is None or row["max_year_share"] <= 0.50)
        and (row["time_exit_share"] is None or row["time_exit_share"] <= 0.20))
    g["ALL"] = all(g[k] for k in
                   ("n300", "exp_t", "bh_q", "pf", "lift", "years",
                    "symbols", "plateau", "concentration"))
    return g


def run(fam, only=None, tag=None, slot_timeout=7200):
    mod = importlib.import_module(fam)
    grid = mod.GRID
    cfgs = grid_configs(grid)
    if only:
        cfgs = [cfgs[i] for i in only]
    rows = []
    rnd = mod.ROUND if hasattr(mod, "ROUND") else "SF01"
    prereg_sha = sf_spec.spec_sha(mod.spec_dict())
    paired = bool(getattr(mod, "PAIRED_RANDOM", False))
    with pa_slots.slot(f"sf01-screen-{fam}", timeout=slot_timeout):
        for i, cfg in enumerate(cfgs):
            spec = mod.make_spec(cfg)
            t0 = time.time()
            try:
                res = pa_eval.evaluate(
                    spec, "DESIGN", SYMBOLS, "M5", TIERS,
                    round_name=rnd, family=fam,
                    data_provider=sf_provider.provider,
                    K_random=20, seed=20260921,
                    random_enabled=not paired,
                    notes=(f"{fam} cfg{i} tag={tag or 'v1'} "
                           f"prereg_sha={prereg_sha[:16]}"))
                row = extract(res, cfg)
                if paired:
                    # Referee cannot build LIMIT-order randoms (no order_px
                    # field on its generated entries).  Ledger the strategy
                    # run above, then a second governed run whose entries are
                    # the module's geometry-fair matched randoms; lift is the
                    # same Newcombe diff pa_eval computes internally.
                    rspec = dict(spec)
                    rspec["entries_fn"] = mod.paired_random_entries
                    res_r = pa_eval.evaluate(
                        rspec, "DESIGN", SYMBOLS, "M5", TIERS,
                        round_name=rnd, family=f"{fam}_rand",
                        data_provider=sf_provider.provider,
                        K_random=0, seed=20260921,
                        random_enabled=False,
                        notes=(f"{fam} cfg{i} PAIRED-RANDOM baseline "
                               f"prereg_sha={prereg_sha[:16]}"))
                    # strategy_matched is empty when random_enabled=False
                    # (kept_by_symbol never populated).  The family detector
                    # gates on session, so every signal is in-session and the
                    # matched subset equals the full set -> use "strategy".
                    ms_m = res["tiers"]["x1"]["strategy"]
                    mr = res_r["tiers"]["x1"]["strategy"]
                    if ms_m.get("N") and mr.get("N"):
                        k1, n1 = round(ms_m["WR"] * ms_m["N"]), ms_m["N"]
                        k2, n2 = round(mr["WR"] * mr["N"]), mr["N"]
                        import pa_metrics
                        d, lo, hi = pa_metrics.newcombe_diff(k1, n1, k2, n2)
                        row["lift_pp"] = round(d * 100, 2)
                        row["lift_ci_pp"] = [round(lo * 100, 2),
                                             round(hi * 100, 2)]
                    row["rand_N"] = mr.get("N")
                    row["rand_exp_r"] = mr.get("exp_r")
                    row["rand_PF"] = mr.get("PF")
            except Exception as ex:
                row = {"params": cfg, "error": f"{type(ex).__name__}: {ex}"}
            row["i"] = i
            row["elapsed"] = round(time.time() - t0, 1)
            rows.append(row)
            print(f"[{i+1}/{len(cfgs)}] {cfg} -> "
                  f"N={row.get('N')} PF_x1={row.get('PF_x1')} "
                  f"t={row.get('t_x1')} ({row['elapsed']}s)", flush=True)
    # BH within the family's config set
    pvals = [r.get("p_norm", 1.0) for r in rows]
    bh = pa_stats.bh_fdr(pvals, q=0.10)
    for r, q in zip(rows, bh["qvalues"]):
        r["q"] = float(q)
    for r in rows:
        if "error" not in r:
            r["gates"] = gates(r, rows, grid)
    outdir = os.path.join(PA_PRO, "rounds", rnd, fam)
    os.makedirs(outdir, exist_ok=True)
    payload = {"family": fam, "round": rnd, "split": "DESIGN",
               "symbols": SYMBOLS, "tiers": TIERS, "grid": grid,
               "spec_sha256": prereg_sha, "rows": rows,
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    jpath = os.path.join(outdir, "SCREEN.json")
    with open(jpath, "w") as f:
        json.dump(payload, f, indent=1, default=str)
    print("wrote", jpath)
    return rows


if __name__ == "__main__":
    fam = sys.argv[1] if len(sys.argv) > 1 else "f1_zone_rejection"
    only = None
    for a in sys.argv[2:]:
        if a.startswith("--only="):
            only = [int(x) for x in a.split("=", 1)[1].split(",")]
    run(fam, only=only)
