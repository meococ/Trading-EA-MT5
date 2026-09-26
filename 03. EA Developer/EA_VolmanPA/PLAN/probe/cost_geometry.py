"""Cost-geometry feasibility math (read-only, no repo writes).

reqW(T,b,k) = T*(1+k) / ((b-k) + T*(1+k))   [REDTEAM 20260726 line 218]
T = target profit factor, b = realized payoff (R), k = all-in cost in R.
"""

def reqw(T, b, k):
    return T * (1 + k) / ((b - k) + T * (1 + k))


rows = []

# --- A. Repo prior geometry (killed): 8-pip stop, realized b=1.0586R ---
b_prior = 1.0586
for T in (1.30, 1.25, 1.00):
    for c, tag in ((1.5, "x1"), (2.25, "x1.5"), (3.0, "x2")):
        k = c / 8.0
        rows.append(("PRIOR 8p stop b=1.0586", f"PF>{T} {tag}", c, 8, k, reqw(T, b_prior, k)))

# --- B. Volman UPA bracket: 10-pip stop, 20-pip target => b=2.0 nominal ---
for b, name in ((2.0, "b=2.0 nominal"), (1.80, "b=1.8 (10% shortfall)")):
    for T in (1.30, 1.25, 1.00):
        for c1 in (1.0,):
            for mult, tag in ((1.0, "x1"), (1.5, "x1.5"), (2.0, "x2")):
                k = (c1 * mult) / 10.0
                rows.append((f"VOLMAN 10/20 {name}", f"PF>{T} {tag}", round(c1 * mult, 1), 10, k, reqw(T, b, k)))

# --- C. Volman geometry on XAUUSD (ATR ~10.6p): 1.5xATR stop ~ 16p, b=2 ---
for stop in (16, 20):
    for mult, tag in ((1.0, "x1"), (2.0, "x2")):
        k = (1.0 * mult) / stop
        rows.append((f"XAU stop {stop}p b=2.0", f"PF>1.30 {tag}", round(1.0 * mult, 1), stop, k, reqw(1.30, 2.0, k)))

# --- D. Wider FX geometry: 20-pip stop, b=2 ---
for mult, tag in ((1.0, "x1"), (1.5, "x1.5"), (2.0, "x2")):
    k = (1.0 * mult) / 20.0
    rows.append(("FX wide 20p stop b=2.0", f"PF>1.30 {tag}", round(1.0 * mult, 1), 20, k, reqw(1.30, 2.0, k)))

print(f"{'geometry':38s} {'gate':16s} {'c(p)':>5s} {'stop':>5s} {'k':>6s} {'reqWR%':>8s}")
for name, gate, c, stop, k, w in rows:
    print(f"{name:38s} {gate:16s} {c:5.1f} {stop:5d} {k:6.3f} {w*100:8.2f}")

print()
print("Measured repo WR ceiling: 47.151% (N=3,703, STRATEGY_LOG.md:5441-5444)")
print()
# sensitivity: what b is needed to hit reqW=47% at k=0.1 (10p stop, c=1p)?
print("Required realized payoff b for reqW=0.47 at 10p stop:")
for T in (1.30, 1.25, 1.00):
    for mult in (1.0, 1.5, 2.0):
        k = mult / 10.0
        w = 0.47
        # solve reqw = w  =>  T(1+k) = w((b-k)+T(1+k)) => b = T(1+k)/w - T(1+k) + k
        b = T * (1 + k) / w - T * (1 + k) + k
        print(f"  PF>{T} x{mult}: b >= {b:.3f}R")
