"""phys_parity — harness arming must equal `gen.views_at(t, arm=True)`.

Lead ruling R01-C1 section 5: on >= 200 random bars per generator on EURUSD and
>= 100 bars per remaining core symbol for `line1_cluster`, the harness armed set
must be identical to the generator's own `views_at(t, arm=True)`.  Zero
mismatches is the target; tolerance <= 0.5% of sampled bars, every mismatch
listed with its cause.  Writes `rounds/R01/PARITY.md`.

Usage:
    python phys_parity.py --symbols EURUSD,GBPUSD,USDJPY,AUDUSD
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import phys_common as pc  # noqa: E402

ROUNDS = os.path.join(pc.PA_PRO, "rounds", "R01")


def sample_bars(n, k, seed):
    rng = np.random.default_rng(seed)
    lo = 3200
    hi = n - 100
    if hi <= lo:
        return np.arange(max(0, lo), max(1, hi))
    return np.sort(rng.choice(np.arange(lo, hi), size=min(k, hi - lo),
                              replace=False))


def check(src, bars_idx):
    import registry  # noqa: F401

    out = []
    gen = src.gen
    for t in bars_idx:
        t = int(t)
        ref = {v.zid for v in gen.views_at(t, arm=True)}
        fast = src.armed_ids_from(src.active_at_fast(t), t)
        if ref != fast:
            missing = sorted(ref - fast)
            extra = sorted(fast - ref)
            out.append({"bar": t, "missing": missing, "extra": extra})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="EURUSD,GBPUSD,USDJPY,AUDUSD")
    ap.add_argument("--bars-main", type=int, default=200)
    ap.add_argument("--bars-other", type=int, default=100)
    ap.add_argument("--out", default=os.path.join(ROUNDS, "PARITY.md"))
    args = ap.parse_args()

    import pa_slots
    from data_helpers import load_ctx
    from phys_source import GenSource
    import registry

    lines = ["# R01 PARITY — harness arming vs `gen.views_at(t, arm=True)`", "",
             f"UTC {pc.utc_now()} · seed {pc.SEED} · main symbol bars "
             f"{args.bars_main}/generator, others {args.bars_other} for line1_cluster.",
             "Tolerance: 0 mismatched bars (acceptance <= 0.5%).", ""]
    any_bad = False
    with pa_slots.slot("phys_parity", timeout=1800):
        for symbol in args.symbols.split(","):
            ctx = load_ctx(symbol, max_bars=None)
            n = ctx.n
            names = registry.names() if symbol == "EURUSD" else ["line1_cluster"]
            k = args.bars_main if symbol == "EURUSD" else args.bars_other
            idx = sample_bars(n, k, pc.SEED + 101 * pc.SYMBOL_ORD.get(symbol, 0))
            for name in names:
                src = GenSource(name, registry.get(name), ctx).run()
                bad = check(src, idx)
                rate = len(bad) / max(1, len(idx))
                status = "PASS" if not bad else ("TOLERATED" if rate <= 0.005 else "FAIL")
                if status == "FAIL":
                    any_bad = True
                lines.append(f"- `{symbol}` `{name}`: {len(idx)} bars, "
                             f"{len(bad)} mismatches ({rate:.4%}) — {status}")
                for b in bad[:5]:
                    lines.append(f"    - bar {b['bar']}: missing {b['missing']} "
                                 f"extra {b['extra']}")
                print(f"{symbol} {name}: {len(idx)} bars, {len(bad)} mismatches "
                      f"({rate:.4%}) {status}", flush=True)
    lines.append("")
    lines.append("OVERALL: " + ("FAIL" if any_bad else "PASS"))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", args.out, "->", "FAIL" if any_bad else "PASS")


if __name__ == "__main__":
    main()
