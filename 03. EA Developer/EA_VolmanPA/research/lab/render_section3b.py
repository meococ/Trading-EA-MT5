"""Render COST_FEASIBILITY section 3b from RANDOM_BASELINE.csv (read-only)."""

import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
CSV = os.path.join(PKG, "PLAN", "random_baseline", "RANDOM_BASELINE.csv")
OUT = os.path.join(PKG, "PLAN", "random_baseline", "SECTION_3B.md")

df = pd.read_csv(CSV)
x1 = df[df.cost_mult == 1.0].copy()
x1["verdict"] = [
    "KILL" if (r.lift_x1_pp > 15.0 or r.unresolved_sess_pct > 30.0) else "PASS"
    for r in x1.itertuples()
]

lines = []
lines.append("### Bảng A — random-entry baseline tại cost x1 (c_rt p90), DESIGN 2016–2021, 12,000 mẫu/cell")
lines.append("")
lines.append(
    "| Symbol | Session | S | c (p) | fill% | WR% | b | exp R | reqW(b=2) | lift_nom pp | reqW(b_obs) | lift_badj pp | unres% | Fri% | mid% | p50 bar | p90 bar | Verdict |"
)
lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in x1.itertuples():
    lines.append(
        f"| {r.symbol} | {r.session} | {r.S} | {r.c_pips} | {r.fill_rate*100:.1f} | {r.wr_net*100:.1f} | "
        f"{r.b:.2f} | {r.exp_r:+.3f} | {r.reqw_x1*100:.1f} | {r.lift_x1_pp:+.1f} | {r.reqw_x1_badj*100:.1f} | "
        f"{r.lift_x1_badj_pp:+.1f} | {r.unresolved_sess_pct:.1f} | {r.friday_pct:.1f} | {r.midnight_pct:.1f} | "
        f"{r.bars_med:.0f} | {r.bars_p90:.0f} | {r.verdict} |"
    )

lines.append("")
lines.append("### Bảng B — surviving cells tại x1.5 và x2")
lines.append("")
lines.append("| Symbol | Session | S | tier | WR% | b | exp R | lift_nom pp | lift_badj pp |")
lines.append("|---|---|---|---|---|---|---|---|---|")
survivors = set()
for r in x1.itertuples():
    if r.verdict == "PASS":
        survivors.add((r.symbol, r.session, r.S))
for r in df.itertuples():
    if (r.symbol, r.session, r.S) in survivors and r.cost_mult in (1.5, 2.0):
        lines.append(
            f"| {r.symbol} | {r.session} | {r.S} | x{r.cost_mult} | {r.wr_net*100:.1f} | {r.b:.2f} | "
            f"{r.exp_r:+.3f} | {r.lift_x1_pp:+.1f} | {r.lift_x1_badj_pp:+.1f} |"
        )

lines.append("")
lines.append("### Bảng C — tổng hợp verdict theo (symbol, session, S)")
lines.append("")
lines.append("| Symbol | Session | " + " | ".join(f"S={int(s)}" for s in sorted(x1.S.unique())) + " |")
lines.append("|---" * (len(x1.S.unique()) + 2) + "|")
for (sym, sess), grp in x1.groupby(["symbol", "session"].copy() if False else ["symbol", "session"]):
    cells = {int(r.S): r.verdict for r in grp.itertuples()}
    row = " | ".join(cells.get(int(s), "-") for s in sorted(x1.S.unique()))
    lines.append(f"| {sym} | {sess} | {row} |")
lines.append("")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("wrote", OUT)
print("\n".join(lines[:10]))
