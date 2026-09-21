"""arrival_freeze — frozen-spec blind measurement per LEAD RULING R02-B.

Spec: w_scale = 0.75, anchor = day open, margins {0.5, 1.0, 2.0} x w_p.
Per (symbol, generator): exact n_events, counters, arm counts, covariate
summaries, common support under the PRIMARY stratum key AND under the
CO-PRIMARY fine key (since_touch tercile added).

    python -B arrival_freeze.py EURUSD GBPUSD AUDUSD USDJPY

OUTCOME-BLIND: computes no outcome column.
"""

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import arrival_common as ac  # noqa: E402

W_SCALE = 0.75


def run_symbol(symbol, gens):
    from data_helpers import load_ctx
    import registry
    from phys_source import GenSource

    ctx = load_ctx(symbol, max_bars=None)
    bars = ctx.bars
    o = np.asarray(bars["o"], dtype=np.float64)
    segs = ac.day_segments(bars)
    for g in gens:
        src = GenSource(g, registry.get(g), ctx).run()
        u_atr, n_smp = ac.armed_width_atr(src, step=288)
        grids = []
        for di, (d0, d1) in enumerate(segs):
            A = ctx.a(d0)
            anch = float(o[d0])
            bands, w_p = ac.build_day_grid(anch, A, u_atr, W_SCALE)
            grids.append((bands, w_p, di, anch, A) if bands else None)
        ev, cnt = ac.arrival_events(bars, ctx, grids)
        arms, diag = ac.tag_arms(ev, src, ac.MARGINS, bars=bars)
        row = {"symbol": symbol, "generator": g, "w_scale": W_SCALE,
               "anchor": "open", "u_atr": u_atr, "u_samples": n_smp,
               "n_events": len(ev), "counters": cnt, "diag": diag,
               "margins": {}}
        for m, tag in arms.items():
            tr, ct = tag["treated"], tag["control"]
            sup = ac.common_support(ev, tr, ct)
            sup_f = ac.common_support(ev, tr, ct, fine=True)
            zf = [ev[i]["zone_fresh"] for i in tr]
            zf_fail = (float(np.mean([z is False for z in zf]))
                       if zf else float("nan"))
            row["margins"][str(m)] = {
                "treated": len(tr), "control": len(ct),
                "excluded": len(tag["excluded"]),
                "zone_stale_share": zf_fail,
                "sum_T": ac.dist_summary(ev, tr),
                "sum_C": ac.dist_summary(ev, ct),
                "support": sup, "support_fine": sup_f}
        print("JSON " + json.dumps(row, default=float), flush=True)


if __name__ == "__main__":
    gens = (sys.argv[sys.argv.index("--gens") + 1].split(",")
            if "--gens" in sys.argv
            else ["line1_cluster", "fractal_h1", "kde_swing",
                  "profile_va", "sd_base", "ref_levels"])
    gi = sys.argv.index("--gens") if "--gens" in sys.argv else len(sys.argv)
    for sym in sys.argv[1:gi]:
        run_symbol(sym, gens)
