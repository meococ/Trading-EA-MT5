# Lab falsification map + the two cost planes — 2026-09-19

Status: campaign-level evidence document. Written after ~76k+ measured
cells across two cost models and every major mechanism class. This is
the honest record of where the exploitable edge surface ends on the
MetaQuotes-Demo M1 plane — and what changed when we measured the
DEPLOY venue's spreads instead of the feed's recorded spreads.

## The two cost planes (critical reframe)

| Plane | What it is | Spread at Mon-01h | Use |
|---|---|---|---|
| `cost_recorded` (v4) | Feed's own recorded `sp` + 0.7p comm | ~1.5p CHF / 0.8p EUR | stress bound — what the research feed itself charges |
| `cost_deploy` (v3 flat 1.0p) | Funded-broker measured spread (~0.1–0.2p all hours) + 0.7p comm + slip | ~0.2p CHF | deployment economics — the account actually trades here |

Measured 2026-09-19 on FivePercentOnline-Real ticks: EURUSD 0.0–0.1p
median all day (0.8p at 00h roll); USDCHF 0.1–0.2p all day (1.2p at
00h). The demo feed's recorded spreads run ~7–15x wider than the
deploy venue. Flat 1.0p was accidentally a good deploy-cost proxy.

**Rule now in hot.md:** a cell must be reported on BOTH planes. A cell
passing only at deploy cost is a broker-transfer hypothesis — legal
because the funded account IS the deploy target, but it must be
declared.

## What was falsified (all at M1 path, 2010–2026, real conventions)

| Class | Volume | Best result | Verdict |
|---|---|---|---|
| impulse/breakout/pullback continuation | ~30k cells | max \|gross\| ~1.27p < cost | DEAD both directions — measured ceiling |
| unconditional drift hour×dow, holds 30m–14h | ~20k v4 cells | zero PF≥1.3 at recorded cost | DEAD at demo-feed cost; Monday cluster only at deploy cost |
| daily-open gap fade/follow | ~4.6k cells | zero PF>1.15 | DEAD |
| weekend-gap conditional fade | ~200 | +2.82 gross → PF 0.97 @realcost | DEAD (gap-conditioned variant too) |
| prior-day sweep fade | ~700 | EURUSD sweepLo PF 1.40, erratic years (−18.6/−27.9), n collapse post-2021 | MARGINAL — fails stability, sub-cadence |
| trend-pullback multi-hour | ~200 | zero PF>1.2 | DEAD |
| daily-context follow/fade (prev-day dir) | ~700 | 2 cells PF 1.22–1.23 | MARGINAL |
| multi-day holds (1–3d) day-context | ~700 | zero PF>1.15 | DEAD |
| model fade/follow OOS h60 | ~200 | PF 1.22 max | MARGINAL |
| model follow OOS h240 dense | ~64 cells | EURUSD th0.08 S PF 1.31 ~3/wk; USDJPY both-sides ~PF1.22 ~8/wk | MARGINAL — best ML result, still sub-gate |
| turn-of-month USD flows (last2/first2 td) | 7 syms | ±1–3p, incoherent | DEAD |
| post-news spike fade/follow (range≥6x, :00/:30 slots) | ~30 cells | PF 1.30–1.37 at ZERO cost → PF ~1.0–1.12 at real cost | DEAD — another cost-free illusion |
| model_v2 (rich features, per-side train-fold calibration) | 4 syms × 4–5 folds | AUC 0.511–0.530, fold PFs scatter 0.4–1.8 no consistency | DEAD at honest feature hygiene |

## Feature-leak incident (model_v2, caught pre-commit)

First model_v2 run showed AUC 0.80 / PF 8–23 — impossible. Root cause:
the **00:00 daily-summary record** (h/l = full-day range, correctly
flagged `suspect`) was excluded from entry/path selection but NOT from
`groupby(day).cummax()/cummin()` and rolling-range features → `day_pos`
encoded distance to the day's eventual extremes (univariate AUC 0.70).
Fix: all features touching h/l now computed on suspect-stripped
`h_eff`/`l_eff`; day-context uses first non-suspect open; `gap` zeroed
on days with suspect first bar. Post-fix: `day_pos` AUC 0.49 (dead),
hour-0 median day-range 95.8p → 3.1p (sane). Rule added to hot.md:
suspect bars must be stripped from FEATURE inputs, not only entries.

## The surviving pockets (deploy-cost plane)

Everything real that remains:

1. **Monday-open cluster** — USDCHF Mon-01h long +1.46/PF1.62 (t=5.01),
   USDJPY Mon-01h long +1.49/1.38, XAUUSD Mon-8/9h short +5.29/1.43.
   All ~1/wk. USDCHF further decomposed to a weekend-gap-fade
   conditional (gap-down weeks only) + post-2020 era concentration —
   killed at GATE B; the JPY/XAU siblings carry the same open-adjacency
   caution.
2. **ML follow EURUSD** — OOS purged-CV, th0.08 short h240: PF 1.31,
   ~3/wk, 9/12 pos-years but 2024–26 decayed flat/negative.
3. **EURUSD prior-day sweep-low fade** — PF 1.40, +7.44p, ~0.5/wk,
   fat-tail year distribution, single-side single-symbol.

## The structural conclusion

**Cadence–edge inverse law, measured everywhere:** raising event
frequency lowers per-event edge; every family peaks at PF~1.2–1.45 on
pockets of ~100–900 events/17y. There is no mechanism on this feed —
mechanical or learned — that delivers GOAL's joint contract
(PF>1.30 × 10–40/wk/symbol × survive 2x cost). The deployable anomaly
density is ~0.3–3 events/week/symbol at PF~1.2–1.6.

This is not an execution failure — it is the measured shape of the
edge surface: gross edges ~1–8p sit right at the cost floor, and the
cells showing edge concentrate exactly where recorded spread is widest
(edge–cost anti-correlation).

## Union-of-signals check (the last systematic idea)

Pooling marginal cells within one symbol cannot beat the per-cell PF
ceiling — pooled PF sits between constituent min and max. EURUSD v3 has
only 3 cells ≥PF1.15 (max 1.27); no symbol has ≥1.30 cells dense enough
to union into 10/wk. Mathematically dead.

## Lawful paths that remain open

1. **Owner cadence amendment** — a low-frequency sleeve (1–5/wk/symbol)
   contract would let the Monday cluster / ML-follow cells through
   governed validation. Gatekeeper-verified as the cleanest legal door.
2. **Portfolio across the full universe** — per-symbol cadence still
   fails; pooling is banned for cadence. No help.
3. **Different data plane** — H4/D1 structurally different signals
   (weekly context, month-end flows), or a different feed/asset class.
4. **Exotic families untested** — news-calendar conditioning,
   cross-asset lead-lag (sub-minute, likely unresolvable on M1).

## Process integrity notes

- GATE B killed WOPEN before any code was minted — the advisory loop
  worked exactly as designed (three catches this campaign: SL/TP field
  swap, phantom tails, cost understatement).
- v4 `spread_cost_arr` now standard: per-event recorded spread +
  commission, insane `sp` → symbol sane-median. SIM_VERSION=4.
- results_log.csv carries v2/v3/v4 provenance; report.py loader handles
  the schema drift; survivors()/apply_fdr() read current-version only.

## Cross-asset lead-lag (AUDUSD -> XAUUSD) — TESTED, KILLED_AT_PROBE

Last untested exotic family, probed 2026-09-19 on synchronized M1 parquet
(5.7M common bars, suspect bars excluded from trigger AND forward window,
60-bar dedup cooldown, honest cost = recorded sane-spread + 0.7p slip).

Raw undeduped screen looked strong (|AUDUSD ret15|>20p -> XAUUSD +60m,
PF 1.55, +9.6p). Decomposition confirmed the lead-lag is genuine —
the XAU-flat-at-trigger subset earns +10.3p PF 2.15 (target has not moved
when the leader fires; true spillover, not shared momentum). But:

- Deduped: 6762 events, 7.8 trades/wk (below 10/wk floor).
- After honest cost: net PF 1.20, edge +3.56p (gross 7.29p).
- Per-year net PF: 1.45-4.74 in the 2011-2014 gold-vol era, ~0.8-1.2
  across 2015-2026 — the edge is a dead regime artifact.

Same edge x cadence inverse law as every prior family. Registry row
HYP-XLEAD-AUDXAU-M1-001, state=killed, KILLED_AT_PROBE. No EA minted.

## Final falsification state

All families tested on this data plane are dead at GOAL economics:
M1 events, clock/session/fix drifts, gaps (daily+weekly), multi-day,
day-context, turn-of-month, spike-fade, ML v1/v2, union-of-signals,
cross-asset lead-lag. Two lawful doors remain unchanged:
(1) Owner cadence amendment; (2) different data plane (feed/asset class).

## 2026-09-19 — Data-plane expansion wave 1: same-feed universe +12 symbols

Synced via harness backtests (HYP-DATAACQ-*, model 2, no trades — history
download side effect only): AUDJPY, AUDNZD, AUDCAD, AUDCHF, USDSEK, USDNOK,
USDPLN, USDTRY, USDZAR, USDMXN, USDCNH, USDSGD. All ETL'd to parquet
(~6M bars each, suspect ~1.1%). MetaQuotes-Demo feed has ~37 FX symbols —
no indices/crypto on this feed.

### WGAP replication (new evidence FOR the mechanism)

Weekend gap-down -> Monday fade replicates cross-symbol on CLEAN 01:00
paths (suspect-filtered): AUDJPY PF 2.07, AUDCAD 2.18, AUDNZD 2.35,
USDCHF 2.52, USDJPY 2.30 gross. 2020+ regime strengthens (PF 3.3-7.3).
Gap-up->short/follow does NOT replicate (all ~1.0 or below).
Asymmetry is coherent: weekend down-gap = overshoot->revert; up-gap =
genuine repricing.

### Unconditional Monday-01:00 long drift — killed by recorded spread

Unconditional (no gap filter) Monday 01:00 long is real on clean paths
(PF 1.2-2.9 gross, all 10 symbols, 2020+ stronger) but dies to recorded
spread (net PF ~0.5 except USDJPY ~0.96). Same edge-density wall.

### Cadence ceiling quantified

Gap-fade is structurally ~1 event/symbol/week. Strong-symbol basket
(USDJPY, AUDJPY, USDCHF, AUDCAD) ~3-6 events/wk net-viable. The GOAL
10/wk floor remains unreachable on bar data regardless of universe width.

### Early-session artifact trap (new lesson)

Monday 00:00-00:10 roll = suspect burst region; 840/840 of Monday 00:05
forward paths are suspect-contaminated. Lab probes cannot evaluate the
week-open window — only governed tester (real ticks) can. All suspect-
path "edges" are void by construction.


## 2026-09-20 — Tick-plane (Dukascopy) early findings

**HYP-WGAP-JPY-M1-002** (slot variant 00:05, governed run 20260920_000259):
0 trades. Signals fire with real gap reads (-21.1p, -7.9p, -5.0p) but 100%
rejected by FILTER/SESSION — Monday 00:05 sits inside the substrate rollover/
weekend guard. The lab's PF~3.8 estimate for this window was void (suspect
bars); the guard exists precisely because that zone is untradeable. Verdict:
KILLED_AT_MODEL_0 (untradeable window, not economics).

**Week-open real-tick cost measurement** (AUDUSD Sunday 2026-06-07, n=1):
first-10min median spread 15.6p (p90 17.3p) vs normal ~1.0p; spread stays
>14p for ~30min, normalizes ~120min. Any week-open edge <15p is dead on
spread alone. Drift in first 2h was +9.9p — below cost. Structural, not
statistical: the rollover guard is justified by real spread data.

**AUDUSD->XAUUSD tick lead-lag** (2-day overlap Jun 1-2, pipeline check only):
W=300s/H=900s/th=3p showed PF 1.68 but n=11 — no economic claim. Most
5s-60s cells negative after real spread. Cadence potential is real
(35-70 events/wk at small thresholds) — pending full pilot data.


## 2026-09-20 — WGAP cross-symbol replication, NET-of-spread truth

Committed probe (probe_weekgap.run, cost_arr applied) over 20 newly-synced
crosses. Corrects earlier GROSS screen which over-stated replication:

NET survivors (PF>1.0): USDJPY 1.54 | EURZAR 4.26 (+64.8p/ev) | EURSEK 1.72 |
EURNOK 1.41 | GBPJPY 1.23 | EURJPY 1.16 | AUDJPY 1.04
NET dead: AUDCAD 0.59 AUDNZD 0.66 AUDCHF 0.62 USDCHF 0.73 CADJPY 0.88
CHFJPY 0.72 NZDJPY 0.79 and ALL EUR/GBP crosses (0.42-0.71).

Pattern: edge exists only where weekend gap >> spread. Exotics survive
because ZAR/SEK/NOK weekend gaps are 50-200p vs 3-8p spreads. Major-pair
gaps (2-10p) cannot clear even 1-4p spreads except USDJPY.

EURZAR: 12/12 years positive (PF 1.31-9.84), no decay — strongest single
cell of the campaign. Deployability unknown: must verify The5ers offers
EURZAR/EURSEK/EURNOK; exotic margin+spread on funded account may differ.

Basket: 11 members -> 5.96 trades/wk, portfolio PF 1.71 net.
Cadence floor (10/wk) still fails. Structural: Monday events are bounded
by ~1/symbol/wk; only ~7 symbols clear net-positive.


## 2026-09-20 — WGAP full-universe map (35 symbols, NET, both directions)

Complete enumeration. Net PF>1.3 survivors (long on gap<-2p, SL20, 60bar):
EURZAR 4.26 (+64.8p) | USDMXN 2.65 (+39.0p) | USDZAR 1.77 | EURSEK 1.72 |
USDJPY 1.54 | USDNOK 1.49 | USDSEK 1.43 | EURNOK 1.41
Marginal: GBPJPY 1.23 EURJPY 1.16 USDCNH 1.09 AUDJPY 1.04 USDTRY 1.03
Short up-gap: only USDMXN +13.2p PF 1.51 survives (bidirectional!).

Pattern now precise: weekend-gap fade survives ONLY where gap size >>
spread — EM (ZAR/MXN gaps 50-200p) and Scandies. Tight majors (EURUSD,
GBPUSD, AUDUSD, crosses) all die: gap 2-10p cannot clear 1-4p spread.
USDTRY notable dead: TRY weekend gaps are repricing, not overshoot.

Basket ceiling: ~8 members x ~0.5-0.9 ev/wk = ~5-6 trades/wk.
GOAL cadence floor (10/wk) remains structurally unreachable from this
mechanism alone. If cadence is ever amended to ~5/wk, the exotic+JPY
basket (PF ~1.7-2 net, multi-currency) is the strongest known candidate.
Deployability: The5ers symbol coverage for ZAR/MXN/SEK/NOK unverified
(needs Owner GUI symbol list).


## 2026-09-20 CORRECTION — exotic WGAP/drift edges were cost-imputation phantoms

CRITICAL TRAP: spread_cost_arr's sane-bound (sp<200pts) falls back to the
sane median when >90% of a symbol's spread field is corrupt — but on
exotics the REAL spread legitimately exceeds the bound. Actual medians
from the 0<sp<=5000pts band:

EURZAR ~107p | USDZAR ~86p | EURNOK ~42p | EURSEK ~40p | USDNOK ~39p |
USDSEK ~36p | USDMXN ~34p | USDTRY ~40p | USDPLN ~22p | USDCNH ~15p |
USDSGD ~2.7p | USDJPY ~0.7p

Re-priced at realistic spread: ALL exotic cells die (PF 0.03-0.28).
This voids the earlier "EURZAR PF 4.26 / USDMXN bidirectional" rows —
edge < spread on every exotic. The 01:00-server daily drift (+28p on
EURZAR) is real in the price series but ~4x smaller than real cost.

Also voids exotic WGAP "survivors" — basket reverts to USDJPY-core only.
Lesson pinned: on symbols with >50% corrupt spread field, do NOT use
sane-median fallback — measure the plausible band first. Exotic real
spreads (20-100+p) live above the majors sanity bound.


## 2026-09-20 — tick-plane probes (Dukascopy pilot, partial Jun-2026)

**XAUUSD tick autocorrelation**: dead at all scales 5s-15min. Mean pnl
~-6p == round-trip spread exactly. Microstructure efficient; both
momentum and fade sides dead. Clean falsification, n=4.6M ticks.

**AUDUSD->XAUUSD tick lead-lag** (16d overlap): W300/H900/th6 PF 1.72
+23p raw BUT excluding top-2 days -> PF 0.96. Entire edge was 2 episodic
days. Reverse XAU->AUD dead. Provisionally KILLED (same episodic
signature as M1); will re-verify when full Jun->Sep range lands.

**Week-open (n=3 Sundays AUDUSD)**: entry +10-30min shows weak positive
tilt (+3-11p) but n=3 meaningless; spread ~15p first 30min remains the
structural cost wall. Undecided pending more Sundays.

**BTCUSD**: downloading Aug1->Sep19; probe ready (probe_btc_plane.py).


## 2026-09-20 — session-open + BTC tick probes (full pilot ranges)

**AUDUSD session-open follow-drift** (110 days): DEAD everywhere. All 18
cells PF<1.5, most <1.0, n=44-73/cell. The earlier +3.9p cells were
small-n noise. Clean falsification at real-spread cost.

**BTCUSD tick momentum** (49 days, Aug-Sep): DEAD. Every W/H/th cell
mean -$32..-65 == round-trip spread (Duka BTC spread ~$50-60). Both
momentum and fade sides dead. DOW-drift cells n=7 too thin to judge.

Tick-plane standing truth: microstructure is efficient at every tested
scale on every tested asset. The only non-dead tick cell remains
AUD->XAU lead-lag at 15-30min (episodic, pending full XAU range).

LAW now triple-confirmed across planes: price-series edges exist but
scalping-horizon cost eats them. GOAL-reachable candidate would need
either (a) per-trade edge >> spread on a tight-spread symbol at high
cadence, or (b) a genuinely different mechanism family.


## 2026-09-20 — week-open definitive + divergence + news families

**Week-open AUDUSD real-tick (n=15 Sundays)**: DEAD all cells both
directions (-1 to -10p). Spread ~15p first 30min + no systematic drift.
HYPOTHESIS SPACE CLOSED: lab-side suspect bars void, EA-side rollover
guard blocks, tick-side cost kills. Three independent confirmations.

**News-event drift** (calendar 2019-2022, 869 events, majors):
USDJPY/EURUSD/GBPUSD post-impulse continuation all PF 0.67-0.78 net,
n~1300/symbol. DEAD.

**Pair-divergence mean-reversion** (EURUSD-GBPUSD, AUDUSD-NZDUSD,
EURUSD-USDCHF, z>2-3, dedup): all PF<0.90 net. EURUSD->GBPUSD mean
+16-21p but PF 0.84-0.90 = fat-tail lottery profile, not a GOAL cell.
DEAD.

**Tick data integrity**: 178 afdticks files, 13.46M ticks, all valid
(magic/count/monotonic/nonneg spread verified).


## 2026-09-20 — unconditional hour-sweep (majors, full range, corrected cost)

USDJPY / EURUSD / XAUUSD: every hour-of-day x long/short, 60m hold, net
of recorded spread+commission. n=180k-260k events/hour-cell. EVERY cell
PF<0.70. No unconditional intraday drift exists on majors at retail
cost. Any surviving mechanism must be conditional (event/state), not
clock-based. The clock family's last hope is dead.

**VWAP reversion** (AUDUSD ticks, 110d): dead, PF 0.42-0.58 at all
thresholds — tick deviations continue rather than revert.

## STANDING MAP (both planes, honest cost)
- M1 conditional survivors: USDJPY WGAP only (0.5/wk, PF 1.54)
- M1 unconditional: dead everywhere (hour sweep, all symbols)
- Tick microstructure: efficient (XAU/BTC momentum, AUDUSD session,
  VWAP, week-open — all dead)
- Tick lead-lag AUD->XAU: episodic, pending full XAU range
- Untested plane: The5ers real feed (needs Owner GUI online)

GOAL-reachability: no tested mechanism delivers 10-40/wk at PF>1.3.
Only lawful paths remaining: (a) tick full-range verification,
(b) funded-feed cost measurement, (c) Owner GOAL amendment.

## 2026-09-20 — XAUUSD session-open: cross-feed verified, episodic kill

Tick probe (Dukascopy, 15d) showed london_fade +40p PF2.39 / ny_follow
+67.6p PF4.06 / asia_follow +28p PF1.79 — first cells approaching GOAL
economics (edge >> XAU spread, cadence ~15/wk). Cross-feed replication
on MetaQuotes M1 same days (Jun1-19, n=14-15): NY follow +83p PF5.11,
LDN fade +37p PF2.15 — CONFIRMED real on independent feed (not a tick
artifact). BUT full-window M1 Jun1-Sep18 (n=70-78): diluted to +6.3p
PF1.07 — the June window was a hot regime, not a persistent mechanism.

16-year decomposition (M1, suspect-clean, per-year):
- NY follow @15:00 Apr-Oct: 13/16y positive but mean only +1-12p gross,
  PF 1.05-1.71 — weak persistent drift, dies under XAU RT cost ~5p.
- NY follow @16:00 Nov-Mar: symmetric noise.
- LDN fade: symmetric noise, no persistent effect.
- ASIA follow: ex-top2 = -156p on 13d — pure episodic.

VERDICT: session-open family DEAD for GOAL. June-2026 regime was real
but episodic; persistent component too weak vs cost. Same edge x cadence
inverse law: big-edge cells are regime-concentrated.

XAUUSD contract conflict FIXED: 19 receipts rebound to canonical pilot
contract sha (binary hashes verified on-disk first; no data rewritten).
Downloader resumed Jun20->Sep18.

## 2026-09-20 — AUDUSD tick momentum/reversion + M1 compression-breakout

**AUDUSD tick microstructure** (110d, ~5.5M ticks): DEAD all 72 cells.
W=30/60/300s x H=60/300/900s x th=0.5-4p, mom+rev. mean -1.0..-1.3p ==
Dukascopy AUDUSD RT spread ~1pip. PF 0.05-0.66. Third confirmation of
the law: tick autocorrelation is zero modulo spread on every asset
tested (XAU -6p, BTC -$56, AUD -1p). Sub-15min directional prediction
does not exist at retail spread.

**M1 H1 compression->breakout** (6-bar range < P20 of 480-bar dist,
break->follow, exit next H1): USDJPY n=632 +0.08p PF1.02; EURUSD n=446
+0.91p PF1.25; AUDUSD n=448 +1.57p PF1.45; GBPUSD +1.13p PF1.24;
XAUUSD +2.47p PF1.17. All GROSS — spread+commission kills every cell
(net ~1.0-1.15 at best). Cadence ~0.5/wk. DEAD for GOAL.

**Pipeline**: EURUSD+USDJPY tick contract launched (Jun1->Sep19, same
window); BTC backfill 76d; XAUUSD resumed Jun20->Jul18 and grinding.

## 2026-09-20 — AUD->XAU lead-lag KILLED (53d tick overlap) + 2 more families

**Lead-lag** (W300 H900 th6, 53d, 97 events): headline PF1.43 +17p BUT
ex-top1=1.22, ex-top2=1.07, ex-top3=0.98, ex-top5=0.84. The whole edge
is 3 fat events (Jun5 +525, Jun11 +695, Jun17 +400). Jun PF1.39 vs Jul
PF1.62 — not decaying, just lottery-clustered. Same profile as
EUR->GBP divergence: mean positive, PF<1 without tails. DEAD as GOAL
mechanism — a 3-events-in-2-months edge is tail luck, not alpha.

**Asia-range -> London breakout** (M1, all majors, tight-range 3-40p):
EURUSD n=3091 net -0.45p PF0.92; USDJPY -0.02p PF0.99; GBPUSD -1.11p;
AUDUSD -1.41p. DEAD.

**Overnight roll drift** (23:55->01:55 by dow): noise, no systematic
edge > spread. DEAD (clock family already closed).

**Law, now quadruple-confirmed**: every positive-mean cell found is
either (a) regime-concentrated (XLEAD 2011-14, session-open Jun-2026),
or (b) fat-tail lottery (lead-lag, EUR->GBP div). No cell with
PF>1.3 sustained after removing its 2-3 best events exists anywhere
tested. GOAL needs a mechanism where the MEDIAN event profits, not
the mean.
