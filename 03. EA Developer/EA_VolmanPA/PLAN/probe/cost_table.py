"""Produces the markdown table for COST_FEASIBILITY.md (read-only)."""

def reqw(T, b, k):
    return T * (1 + k) / ((b - k) + T * (1 + k))


# symbol: (spread p50, spread p90, slippage p90 RT, commission price pips, atr14_m5_all, atr14_london_1012srv)
SYM = {
    "EURUSD": (0.0, 0.1, 0.2, 0.7, 3.43, 4.39),
    "GBPUSD": (0.0, 0.1, 0.3, 0.7, 4.71, 6.12),
    "USDJPY": (0.2, 0.3, 0.4, 0.7, 4.24, 4.81),
    "USDCHF": (0.1, 0.2, 0.2, 0.7, 3.01, 3.70),
    "USDCAD": (None, None, None, 0.7, 3.73, 3.94),
    "AUDUSD": (None, None, None, 0.7, 3.11, 3.63),
    "NZDUSD": (None, None, None, 0.7, 2.96, 3.36),
    "XAUUSD": (3.0, 4.5, 2.83, 0.7, 10.62, 11.40),
}

GEOMS = [8, 10, 12, 16, 20, 30, 40]

print("## Cost in pips (research plane, MQ-Demo sidecars; p50 / p90-conservative)")
print()
print("| Symbol | spread p50 | spread p90 | slip p90 RT | comm | c_rt p50 | c_rt p90 | ATR14 M5 all | ATR14 London |")
print("|---|---|---|---|---|---|---|---|---|")
for s, (sp50, sp90, sl, cm, atr, atrl) in SYM.items():
    if sp90 is None:
        print(f"| {s} | NOT MEASURED | NOT MEASURED | NOT MEASURED | {cm} | n/a | n/a | {atr} | {atrl} |")
    else:
        c50 = round(sp50 + cm + sl * 0.5, 2)
        c90 = round(sp90 + cm + sl, 2)
        print(f"| {s} | {sp50} | {sp90} | {sl} | {cm} | {c50} | {c90} | {atr} | {atrl} |")

print()
print("## Required win rate for PF>1.30 at x1 and PF>=1.00 at x2, b=2.0 (conservative c_rt p90)")
print()
hdr = "| Symbol | c_rt p90 | " + " | ".join(f"S={g}" for g in GEOMS) + " |"
print(hdr)
print("|---" * (len(GEOMS) + 2) + "|")
for s, (sp50, sp90, sl, cm, atr, atrl) in SYM.items():
    if sp90 is None:
        print(f"| {s} | n/a | " + " | ".join("n/a" for _ in GEOMS) + " |")
        continue
    c = round(sp90 + cm + sl, 2)
    cells = []
    for g in GEOMS:
        k = c / g
        w1 = reqw(1.30, 2.0, k) * 100
        cells.append(f"{w1:.1f}%")
    print(f"| {s} | {c} | " + " | ".join(cells) + " |")

print()
print("## Verdict per symbol (c_rt p90, b=2.0): PASS if reqW(x1,PF1.3) <= 44.0% and reqW(x2,PF1.0) <= 42.0%")
print()
for s, (sp50, sp90, sl, cm, atr, atrl) in SYM.items():
    if sp90 is None:
        print(f"- **{s}**: BLOCKED — no measured spread; measurement required before any economic run.")
        continue
    c = round(sp90 + cm + sl, 2)
    ok = []
    for g in GEOMS:
        k = c / g
        w1 = reqw(1.30, 2.0, k) * 100
        w2 = reqw(1.00, 2.0, k) * 100
        if w1 <= 44.0 and w2 <= 42.0:
            ok.append(g)
    if ok:
        print(f"- **{s}**: viable stop range {ok[0]}-{ok[-1]} pips (b=2.0). min viable / ATR_all = {ok[0]/atr:.2f}")
    else:
        print(f"- **{s}**: NOT viable at any S in {GEOMS} at conservative cost.")

print()
print("## Stress check: b=1.7 (bracket shortfall) at conservative cost")
print()
for s, (sp50, sp90, sl, cm, atr, atrl) in SYM.items():
    if sp90 is None:
        continue
    c = round(sp90 + cm + sl, 2)
    ok = []
    for g in GEOMS:
        k = c / g
        w1 = reqw(1.30, 1.7, k) * 100
        if w1 <= 44.0:
            ok.append(g)
    tag = f"stop>={ok[0]}p" if ok else "NOT viable even at S=40"
    print(f"- {s} (c={c}): {tag}")
