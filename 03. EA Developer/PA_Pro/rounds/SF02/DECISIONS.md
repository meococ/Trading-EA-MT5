# SF02 — DECISIONS (autonomous judgement calls)

One entry per call: what, why, alternatives. Newest last.

### D1 — G1 v2: inv at the deeper of (zone far edge, pullback extreme) [PRE-OUTCOME] (2026-09-21T05:38Z)

DESIGN census of v1 (g1_htf_pullback/CENSUS.json) showed the rung
assignment collapses: s_struct = zone width + 2p, and salient zones are
typically 5-20p wide, so ~97% of signals land on rung 18 and 16/20 grid
cells are empty — the mandate's rung-2 geometry (24-55p) is never
exercised. Revision (before ANY G1 outcome; census contained no outcome
fields): `inv = min(z.lo, pullback_low) - buf` for longs /
`max(z.hi, pullback_high) + buf` for shorts, where the pullback leg starts
just after the last bar lying FULLY on the approach side (long: `l[j] >
edge + touch_atr*A5`; short: `h[j] < edge - tol`), causal, capped at
`pull_max = 96` bars. Doctrine: "stop below the pullback low" —
the deeper of zone floor and pullback extreme is the real invalidation.
Spec bump v1 -> v2; new prereg; v1 (T000279) superseded, never screened.

### D2 — G3 v2: episode semantics for the Volman build-up [PRE-OUTCOME] (2026-09-21T05:55Z)

G3 v1 required compression AND break-through-zone on the SAME bar:
census ~0.05 signals/week basket (EURUSD funnel: 223,945 live bars ->
7,351 compressed trend bars -> 258 aligned breaks -> 3 zone passes ->
2 after cost guard). The joint event is near-nonexistent; Volman's
build-up is an episode — compression presses against the level and the
break may come bars later. v2: contiguous compressed bars (<=CMAX=24)
form a cluster whose extent is the box; a qualifying armed salient zone
(prox_atr=1.0 to either edge, approach_side matching the break side)
arms an episode expiring E=6 bars after the last compressed bar; trigger
= close beyond the cluster edge with s_tr_h4 alignment at trigger time.
v1 (T000280) superseded pre-outcome; new ledger hash for v2.

### D3 — Paired-random baseline for LIMIT-order families [PRE-OUTCOME] (2026-09-21T06:43Z)

The referee's matched-random path (pa_eval) builds bare entries {sig, side,
tag}; pa_fill's limit branch then raises "limit orders need an explicit
'order_px'" — the first G1 screen wrote 20 error rows (infrastructure
failure, NOT a family verdict; no outcome was seen). lib/ is read-only, so
the fix lives in the lane: sf_screen detects mod.PAIRED_RANDOM and runs a
SECOND governed pa_eval call per cell (family "<fam>_rand",
random_enabled=False) whose entries_fn is the module's
paired_random_entries. That builder replicates the referee construction
verbatim — match_random on the strategy signals (out-of-session signals
skipped internally, K=20, seed=20260921), tag = source signal's kept index,
utc_start warmup drop — and adds the one field the referee cannot express:
a geometry-fair limit price, order_px = signal-bar extreme ∓ buf
(long: l[sig]-buf; short: h[sig]+buf) = "enter on a 1-pip dip through the
random bar's extreme", the symmetric null for a limit-at-edge entry.
Lift is then the same Newcombe diff pa_eval computes internally
(strategy_matched == strategy here because the detector session-gates all
signals). Every number still comes from pa_eval and is ledgered; the
baseline run carries its own family name in the ledger for traceability.

### D4 — G2 closed pre-outcome on autopsy evidence (2026-09-21T06:49Z)

G2 (salient-zone rejection/trap) is F1/F3 restricted to the most salient
zone. A2 showed all probe/rejection entries carry ADVERSE exit-free edge
(edge-ratio delta -0.26..-0.68, BH-sig at every horizon) — the direction
is wrong, not the exits — and A3 showed salience terciles do not rescue
F1/F3 lift. No slice turns a probe entry positive. G2 is closed without
spending any screen budget; ROUND_REPORT.md written. Reopens only on a
Lead instruction.

### D5 — G4 design: exit-axis sweep on the G1 entry (2026-09-21T07:05Z)

Mandate: G4 changes ONLY the S and tp_mult grid of the best G1-G3
family, never the entry logic. Chosen base = g1_htf_pullback v2
(T000282): the only family that produced governed screen data. Grid:
gen{line1_cluster, sd_base} x tr_src{h1, h4} x S{18, 55} x
tp_mult{1.0, 2.0, 3.0} = 24 cells. Rationale: S18 is the only rung
with N>=300 (measures the tp axis with power); S55 is where A1 showed
intraday flats bind hardest and sd_base showed positive lift; the
tp_mult sweep (1/2/3) directly measures TP-reach vs flat-out tradeoff.
Detector identical to G1 -> census is the G1 census restricted to these
cells (tp_mult does not affect signals). PAIRED_RANDOM baseline as D3.

### D6 — Q4 plan (reports only) (2026-09-21T07:15Z)

Queue nearly exhausted (G1/G3 dead, G2 closed, G4 screening). Remaining
wall-clock goes to the two mandated report-only items:
1. RUNG-5 PREP: document data availability + cost evidence for USDCAD,
   USDCHF, NZDUSD from the read-only cache (already probed: all three
   have full M5 (~444k bars) + M1 (~2.24M bars) DESIGN coverage
   2015-12-02..2021-12-31 and c_rt P90 1.4/1.1/1.4; zone caches would
   need building via sf_ctx.build_cache — causal, DESIGN-only).
2. MULTI-DAY REFEREE PROPOSAL: A1 showed intraday flats are the binding
   constraint (TP reach <1-7% at S>=55/tp>=2; ~92% of random exits are
   DAILY/FRIDAY flats at S=75). Proposal only — no lib/ code — covering
   swap costs, weekend gaps, and ECON-1 tests.
Both land in rounds/SF02/Q4_*.md. No new outcomes are computed; the
proposal references only existing ledgered/autopsy numbers.
