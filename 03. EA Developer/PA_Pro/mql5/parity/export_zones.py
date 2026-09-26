"""export_zones.py — Python twin of the EA's zone parity export (PA_Export.mqh).

For each of the six generators it runs ``families/sf_ctx.py::run_pass`` —
the unit-tested exact-replay reference (SF01 DECISIONS D4) — and writes one
CSV row per ARMED zone view per bar:

  t_idx,t_epoch,gen,zid,kind,scale,lo,hi,strength,touches,fresh,
  broken_idx,role_flip,approach_side,born_idx,end_idx

Join key against the MQL5 side is (t_epoch, gen) — bar indices differ
because the EA exports its own loaded-history window.

Usage:
    python export_zones.py EURUSD [out_dir] [from_idx to_idx]

Heavy compute: acquire a pa_slots slot BEFORE running (done internally).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQL5 = os.path.dirname(HERE)
PA_PRO = os.path.dirname(MQL5)
for _p in (os.path.join(PA_PRO, "families"),
           os.path.join(PA_PRO, "struct", "zones"),
           os.path.join(PA_PRO, "lib")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_data          # noqa: E402
import pa_slots         # noqa: E402
import registry         # noqa: E402
import sf_ctx           # noqa: E402
from common import ZoneContext  # noqa: E402

COLS = ("t_idx,t_epoch,gen,zid,kind,scale,lo,hi,strength,touches,fresh,"
        "broken_idx,role_flip,approach_side,born_idx,end_idx")

SCALE = {"micro": 0, "meso": 1, "macro": 2}
DG = {"EURUSD": 5, "GBPUSD": 5, "USDJPY": 3, "USDCHF": 5,
      "AUDUSD": 5, "USDCAD": 5, "NZDUSD": 5}


def export(symbol, out_path, gens=None, t0=0, t1=0):
    m1 = pa_data.load_m1(symbol, split="DESIGN", warmup_days=30)
    m5 = pa_data.resample(m1, "M5")
    h1 = pa_data.resample(m1, "H1")
    ctx = ZoneContext(m5, h1)
    n = ctx.n
    hi_t = (n - 1) if t1 <= 0 else min(t1, n - 1)
    dg = DG.get(symbol, 5)
    names = gens or registry.names()
    rows = 0
    with open(out_path, "w", encoding="ascii", newline="") as f:
        f.write(COLS + "\n")
        for gname in names:
            gen = registry.get(gname)(ctx)

            def cb(t, views, _g=gname, _gen=gen):
                nonlocal rows
                if t < t0 or t > hi_t:
                    return
                te = int(m5["t"][t])
                for v in views:
                    if not v.meta.get("_armed"):
                        continue
                    z = _gen._live.get(v.zid)
                    end_idx = int(z.end_idx) if z is not None else -1
                    st = v.meta.get("_stx_state") or {}
                    app = st.get("approach_side") or 0
                    f.write(
                        "%d,%d,%s,%d,%s,%d,%.*f,%.*f,%.6f,%d,%d,%d,%d,%d,%d,%d\n"
                        % (t, te, _g, int(v.zid), v.kind,
                           SCALE.get(v.scale, 0),
                           dg, v.lo, dg, v.hi,
                           float(v.strength), int(v.touches),
                           1 if v.fresh else 0,
                           int(v.broken_idx) if v.broken_idx is not None else -1,
                           int(v.role_flip), int(app),
                           int(v.born_idx), end_idx))
                    rows += 1

            sf_ctx.run_pass(ctx, gen, cb=cb)
            print("  %s done" % gname, flush=True)
    return rows


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out")
    t0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    t1 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "zones_%s_py.csv" % symbol)
    with pa_slots.slot("pa_pro export_zones %s" % symbol):
        rows = export(symbol, out_path, t0=t0, t1=t1)
    print("wrote %s (%d zone rows)" % (out_path, rows))


if __name__ == "__main__":
    main()
