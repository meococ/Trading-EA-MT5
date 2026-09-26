"""Render COSTS.md (sub-agent B, Round 00) from the per-symbol JSONs written
by _data_inventory_scan.py plus the frozen cost table with file:line
provenance. Every ATR/share number comes from the JSONs; every cost number
from the cited sources."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_data_inventory")
OUT = os.path.join(HERE, "COSTS.md")

SYMS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
YEARS = [str(y) for y in range(2010, 2027)]

# value, tier ("measured" | "proxy"), provenance
C_RT = {
    "EURUSD": (1.0, "measured", "`EA_VolmanPA/PLAN/COST_FEASIBILITY.md:75`; `vpa_random_baseline.py:41`"),
    "GBPUSD": (1.1, "measured", "`EA_VolmanPA/PLAN/COST_FEASIBILITY.md:76`; `vpa_random_baseline.py:41`"),
    "USDJPY": (1.4, "measured", "`EA_VolmanPA/PLAN/COST_FEASIBILITY.md:77`; `vpa_random_baseline.py:41`"),
    "USDCHF": (1.1, "measured", "`EA_VolmanPA/PLAN/COST_FEASIBILITY.md:78`; `vpa_random_baseline.py:41`"),
    "AUDUSD": (1.4, "proxy", "no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; supporting: `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:376` (Dukascopy AUDUSD RT spread ~1 p)"),
    "USDCAD": (1.4, "proxy", "no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; `COST_FEASIBILITY.md:79` (NOT MEASURED)"),
    "NZDUSD": (1.4, "proxy", "no measured c_rt in repo — `proxy` per `PA_PRO_CHARTER.md:96-98`; `COST_FEASIBILITY.md:81` (NOT MEASURED)"),
}

HEADER = """# PA-PRO — COSTS (sub-agent B, Round 00)

Status: `DONE`. Charter: `PA_PRO_CHARTER.md` §3/§6/§8 (SHA256
`3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`, verified 2026-09-20).
ATR/share numbers come from `PA_Pro/docs/_data_inventory/<SYM>.json` (see
`DATA_INVENTORY.md` for the method); this file adds the cost model and the
cost-geometry feasibility tables. Renderer: `PA_Pro/docs/_costs_render.py`.

**`c_rt` is `RESEARCH_PROXY` (conservative)** — see §7. Every number carries a
file:line provenance; nothing here is a live-broker measurement.

---

## 1. c_rt p90 per symbol (all-in round-turn, pips)

`c_rt = spread_p90 + slippage_p90_rt + commission_bound` (`COST_FEASIBILITY.md:58-63`).
Commission bound = 0.7 pip = $7.00/lot round-turn, an **assumed conservative bound**
(`COST_FEASIBILITY.md:21`, `EA_LiquiditySweep/research/evidence/COST_SOURCE_MANIFEST.json:39-49`;
broker-observed commission is 0.00 on the governed run — `04. Memory/research/20260916_COST_PLANE_AUDIT.md:27-31`).

| Symbol | c_rt p90 (pips) | status | provenance |
|---|---|---|---|
"""

TIERS = """
---

## 2. Cost tiers and semantics (charter §6)

Tiers multiply **`c_rt`**; the implementation shifts the fill **against the trader** by
`tier x c_rt` at entry (the round-turn cost is charged once per trade, as an adverse price
shift; `EA_VolmanPA/research/lab/vpa_random_baseline.py:10-11`). The referee reports every
metric per tier (charter §6, `PA_PRO_CHARTER.md:156-160`).

| tier | multiplier | semantics |
|---|---|---|
| gross | 0.0 | sanity only, no cost; never a promotion basis |
| x1 | 1.0 | baseline `c_rt` p90 (research proxy) |
| x1.5 | 1.5 | stress |
| x2 | 2.0 | stress ceiling; SCREEN gate requires PF x2 >= 1.00 (`PA_PRO_CHARTER.md:195`) |

Minimum stop = `10 x c_rt x tier` (charter §3 geometry guard, `PA_PRO_CHARTER.md:100`;
x1 is the hard guard, `PA_PRO_CHARTER.md:202`):

| Symbol | x1 min stop | x1.5 min stop | x2 min stop |
|---|---|---|---|
"""

BODY_FORMULA = """
---

## 3. Feasibility arithmetic (stated formula)

For symbol `s`, year `y`:

- `min_stop_x1(s) = 10 x c_rt(s)` (pips), the charter §3 geometry guard at x1.
- `ratio_H1(s,y) = min_stop_x1(s) / median(ATR14_H1(s,y))` — how many times the typical
  H1 bar's ATR the guard costs. `ratio < 1` means a 1xATR14(H1) stop is wide enough at x1;
  `ratio > 1` means a structural H1 stop has to exceed the typical H1 ATR.
- `share_H1(s,y) = mean(ATR14_H1(s,y) >= min_stop_x1(s))` — the fraction of complete H1
  bars in the year whose ATR14 alone already covers the guard. Equivalently: the share of
  H1 bars on which a 1xATR14(H1) stop is admissible at x1.
- M15 columns use the same min stop against `median(ATR14_M15)`.

Caveat: `share_H1` is the share of **bars**, not of signals; setups can (and should)
select wide-ATR bars, so this is a floor on feasibility, not a forecast.

---

## 4. Feasibility per symbol — overall (2010-2026, complete bars only)

| Symbol | c_rt x1 | min stop x1 | ATR14 H1 med | ratio H1 | share H1 >= guard | ATR14 M15 med | ratio M15 |
|---|---|---|---|---|---|---|---|
"""


def f2(v):
    return "n/a" if v is None else f"{v:.2f}"


def pct(v, dec=1):
    return "n/a" if v is None else f"{100.0*v:.{dec}f} %"


def main():
    r = {}
    for s in SYMS:
        with open(os.path.join(SRC, f"{s}.json"), encoding="utf-8") as f:
            r[s] = json.load(f)

    L = [HEADER]
    for s in SYMS:
        v, status, prov = C_RT[s]
        L.append(f"| {s} | **{v:.1f}** | {status} | {prov} |\n")

    L.append(TIERS)
    for s in SYMS:
        v = C_RT[s][0]
        L.append(f"| {s} | {10*v:.1f} p | {15*v:.1f} p | {20*v:.1f} p |\n")

    L.append(BODY_FORMULA)
    for s in SYMS:
        d = r[s]
        h1, m15 = d["timeframes"]["H1"], d["timeframes"]["M15"]
        c = C_RT[s][0]
        ms = 10.0 * c
        L.append(f"| {s} | {c:.1f} | {ms:.1f} p | {h1['overall_median_pips']:.2f} p "
                 f"| {ms/h1['overall_median_pips']:.2f} | {pct(h1['overall_share_atr_ge_10c'])} "
                 f"| {m15['overall_median_pips']:.2f} p | {ms/m15['overall_median_pips']:.2f} |\n")

    L.append("\n---\n\n## 5. Feasibility per symbol and per year\n\n")
    L.append("Share column = fraction of complete H1 bars in that year with "
             "`ATR14(H1) >= 10 x c_rt(x1)`; `c_rt` is the symbol's x1 value (constant across "
             "years in this research plane). 2026 is partial (cache ends 2026-09-18).\n")
    for s in SYMS:
        d = r[s]
        h1, m15 = d["timeframes"]["H1"], d["timeframes"]["M15"]
        c = C_RT[s][0]
        ms = 10.0 * c
        L.append(f"\n### {s} (c_rt x1 = {c:.1f} p, min stop = {ms:.1f} p)\n\n")
        L.append("| Year | H1 med | ratio H1 | share H1 >= guard | H1 n | M15 med | ratio M15 |\n")
        L.append("|---|---|---|---|---|---|---|\n")
        for y in YEARS:
            py = d["per_year_m1"][y]
            if py["m1_bars"] == 0:
                continue
            hy, my = h1["per_year"][y], m15["per_year"][y]
            sh = h1["share_atr_ge_10c_per_year"][y]
            ytag = f"{y} (partial)" if y == "2026" else y
            if hy is None:
                L.append(f"| {ytag} | n/a | n/a | n/a | 0 | n/a | n/a |\n")
                continue
            L.append(f"| {ytag} | {hy['median']:.2f} p | {ms/hy['median']:.2f} | {pct(sh)} "
                     f"| {hy['n']:,} | {my['median']:.2f} p | {ms/my['median']:.2f} |\n")

    L.append(SEARCH_REPORT)
    with open(OUT, "w", encoding="utf-8") as f:
        f.writelines(L)
    print(f"[render] {OUT}")


SEARCH_REPORT = """
---

## 6. Cost-evidence search for AUDUSD / USDCAD / NZDUSD (what was searched, what was found)

Searched (all READ-ONLY, 2026-09-20):

1. `03. EA Developer/*/research/evidence/*spread*evidence*.json` — found only EURUSD
   (`EA_LiquiditySweep`), GBPUSD + USDJPY (`EA_SessionDrive`), USDCHF (`EA_BoundaryEdge`,
   `EA_RollReversion`), USDJPY (`EA_WeekGap`, `EA_SessionMomentum`), XAUUSD
   (`EA_LiquiditySweep`). **No AUDUSD / USDCAD / NZDUSD spread evidence file exists.**
2. `03. EA Developer/*/research/evidence/*slippage*evidence*.json` — same symbol set as
   above (EURUSD, GBPUSD, USDJPY, USDCHF, XAUUSD). **No AUDUSD / USDCAD / NZDUSD slippage
   evidence file exists.**
3. `**/COST_SOURCE_MANIFEST.json` — 6 manifests exist (EA_BoundaryEdge, EA_LiquiditySweep,
   EA_RollReversion, EA_SessionDrive, EA_SessionMomentum, EA_WeekGap); all are for
   USDCHF/USDJPY/EURUSD/GBPUSD/XAUUSD. The per-symbol `_dataacq` manifests
   (`02. AlphaFactory/runs/_dataacq/<SYM>/cost_source_manifest.json`) carry
   `cost_provenance: UNVERIFIED`, `commission: unknown_not_zero`, `slippage:
   unknown_not_zero`, `note: "Data acquisition; no economics."` — not usable as cost
   evidence.
4. `02. AlphaFactory/lab/*` — `labels.py:23-38` defines the v4 per-event cost
   (`spread_cost_arr` = recorded feed spread in pips + 0.7 commission). `results_log.csv`
   has `cost_rt` for the three symbols (11,460 cells each): min 1.0 / median 1.0 / max
   ~4.0–5.2 p. This is **recorded feed spread on event masks, not an all-in p90**, and the
   recorded `sp` field is known corrupt in bursts (`data_plane.py:8-11`, and the
   2026-09-20 GATE-B correction in `04. Memory/research/20260919_...md:244-263`); it is
   cited as supporting context only.
5. `02. AlphaFactory/tools/*cost*` — `measure_cost_evidence.py`,
   `build_research_cost_proxy_evidence.py`, `build_verified_cost_artifact.py`,
   `research_cost_stress.py` and the MTS cost overlays: tooling only; their outputs for
   these symbols are the `_dataacq` UNVERIFIED manifests (3).
6. `04. Memory/research/2026091*COST*.md` — `20260916_COST_PLANE_AUDIT.md` (commission
   bound, demo vs deploy planes) and `20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md`
   (two cost planes; AUDUSD Dukascopy measurements). The 2026-09-18 day-boundary doc
   reports MQ-Demo tick spreads at 00:00-02:00 server of p50 0.1-0.2 p / p90 0.2-0.3 p
   across the seven majors (`04. Memory/research/20260918_DAY_BOUNDARY_MARKET_PHYSICS.md:77-78`),
   i.e. the same order as the four measured majors — again window-specific and
   spread-only.

Found for AUDUSD: real measured spread on the **Dukascopy** tick plane — "normal ~1.0 p",
week-open first 10 min median 15.6 p / p90 17.3 p
(`04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:189-190`) and
"Dukascopy AUDUSD RT spread ~1 pip" (`...:376`). This is spread-only, another venue, and
~110 days in 2026 — **not** an all-in research-plane `c_rt`.

Found for USDCAD / NZDUSD: nothing measured. `COST_FEASIBILITY.md:79-81` lists both as
**NOT MEASURED** and `COST_FEASIBILITY.md:271-276` names measuring them as required work
before an economic run.

**Decision (per the task rule):** no sufficient all-in measured `c_rt` exists for the
three symbols, so all three use **1.4 pips, marked `proxy`**, per
`PA_PRO_CHARTER.md:96-98`. The 1.4 p proxy is conservative in the direction of the
program: for AUDUSD it is above the measured Dukascopy spread-alone (~1.0 p) and above
the recorded-feed median; it equals the USDJPY measured value, the widest measured major.

---

## 7. Provenance, assumptions, and caveats

- **`RESEARCH_PROXY` (conservative).** Every manifest in the repo is
  `evidence_tier: RESEARCH_PROXY`, `promotion_eligible: false`
  (`EA_LiquiditySweep/research/evidence/COST_SOURCE_MANIFEST.json:3-9`);
  `COST_FEASIBILITY.md:302-310` (§8) states the p90 construction is the conservative bound
  for the research plane. Live/deploy costs can be lower (deploy plane EURUSD 0.0-0.1 p
  all-day, USDCHF 0.1-0.2 p — `04. Memory/research/20260919_LAB_FALSIFICATION_MAP_AND_COST_REFRAME.md:16-19`),
  but promotion requires the measured venue, not this proxy.
- `ASSUMPTION:` the 3-4 day MQ-Demo tick samples (2026-09-08/11) represent the 2010-2026
  distribution (`COST_FEASIBILITY.md:304-305`).
- `ASSUMPTION:` x1.5/x2 tiers apply the same `c_rt` multiplied, as an adverse shift at
  fill (charter §6); no separate measurement exists for stressed fills.
- Exact per-year shares are computed for x1 only. For x1.5/x2 thresholds, the JSON
  per-year ATR percentiles (`p10,p25,median,p75,p90` in
  `_data_inventory/<SYM>.json`) allow interpolation, but the exact share is `NOT RUN`.
- The cost-geometry guard is a necessary condition, not a promise: a stop can be wide and
  the setup still lose; and the guard says nothing about target geometry (`b`).
- `c_rt` for AUDUSD/USDCAD/NZDUSD must be re-derived from measured evidence before any
  promotion decision on those symbols (per charter §3).
"""


if __name__ == "__main__":
    main()
