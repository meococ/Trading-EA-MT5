# REVIEW_v4 — NEUTRAL REVIEW OF ROUND 2D (exit management, F2_NH_b)

Reviewer: neutral sub-agent (fresh session, own commands; report text not
trusted). Scope: `03. EA Developer/SonicR_Lab` only; read-only elsewhere;
no heavy jobs run. Date: 2026-09-23.

## VERDICT: PASS-WITH-NOTES

All 8 checks verified independently. Round-2D protocol held: freeze
precedes all exit-variant P/L, baseline regression is real, CONFIRM set
untouched, VALIDATION unread, HOLDOUT sealed, reported numbers reproduce
from the CSVs. Minor notes at the bottom; none affects any conclusion.

## Check 1 — PREREG_V4 hash & freeze ordering: PASS

- Recomputed `hashlib.sha256(PREREG_V4.md bytes)` =
  `1421a4f0ef39bac7ffe9e7e0de36f64a2a0d21426756defe427f1e779068d300`
  (10250 bytes) — matches the frozen hash verbatim.
- LAB_LOG.md line 84 records `PREREG_V4 FROZEN sha256=1421a4f0...` at
  `2026-09-23T21:26:03Z`, explicitly "BEFORE any exit-variant P/L file".
- Earliest exit-variant artifact mtime, recomputed over
  `out/trades_2d_*.csv` + `out/design_2d_*.csv` (146 files):
  `out/trades_2d_AUDUSD_X0-HOLD_e1.csv` at `2026-09-23T21:27:41.116Z`.
  Freeze 21:26:03Z < first P/L 21:27:41Z (~98 s). Ordering holds.

## Check 2 — T1 regression is real (independent rerun): PASS

Re-ran `runs/managed.py resim_trades(rule="X0", skip_suspect=True)` on
fresh `light_ctx` for two symbols, harness H1, vs the round-2C trade
files `out/trades_2c_<sym>_F2_NH_b_e1.csv`:

| symbol  | rows | exit_ctm maxdiff | exit maxdiff | reason | r_x1 maxdiff |
|---------|-----:|-----------------:|-------------:|:------:|-------------:|
| GBPUSD  | 1182 | 0 (exact)        | 2.2e-16      | identical | 1.1e-12 |
| USDJPY  | 1141 | 0 (exact)        | 1.4e-14      | identical | 1.5e-12 |

All within the 1e-9 mandate. The resim output is also identical to the
stored `out/trades_2d_<sym>_X0-HOLD_e1.csv` files, so the frozen 2D X0
artifacts and the 2C artifacts agree row-for-row.

## Check 3 — No exit-variant output for any CONFIRM symbol: PASS

- `ls out` / `find` for `*NZDUSD* *USDCAD* *EURJPY* *AUDJPY* *EURGBP*`
  containing `2d`: zero files anywhere in the lane (checked `out/`,
  `runs/`, `tests/`, `out/sigs/`).
- Existing C-symbol files are only round-2C artifacts
  (`trades_2c_<C>_*.csv`, `essence2c_trades_<C>.csv`) — permitted.
- `grep -E "NZDUSD|USDCAD|EURJPY|AUDJPY|EURGBP"` over all six
  `design_2d_{summary,slices,pess}{,_e1}.csv`: zero matches.
- `runs/design_2d.py` iterates `D_SET` (7 symbols, line 29/116); no code
  path touches C.

## Check 4 — T3 genuinely recomputes; dragon uses closed M15 only: PASS

- `tests/test_exits.py::_tfx_from_m1` (lines 34-38) calls
  `dm.resample(m1, 15)` then `ind.dragon(tf)` — the M15 resample and
  EMA34 arrays are rebuilt from the altered M1 dict at lines 147, 156,
  168, 175 (not reused). `test_t3_dragon_no_lookahead` asserts the exit
  is unchanged under post-exit edits, moves when the triggering M15
  close changes, and that `exit_i == tfx["m1_hi"][j_pb]` (first M1 of
  the next M15 bar). `pytest tests/test_exits.py`: 9/9 pass (re-run).
- `src/exits.py::_dragon_exit_i` (lines 58-85): `j0` is the first M15
  bar with close time `t[j]+900 > mt[trig_i]` — only bars CLOSED at
  decision time; condition is `close < EMA34(Low)` for longs; the exit
  index is `searchsorted(mt, t[j]+900)` = the next M15 bar's first M1
  open (then skips suspect bars under H1). `resolve_exit` exits at
  `mo[i]` with priority over that bar's SL/TP (lines 127-130), computes
  `dragon_i` only after the trigger (line 185), and bumps a retroactive
  `dragon_i <= i` to `i+1` (line 188-189) — cannot act backwards.
- `dm.resample` semantics verified: `m1_hi` = exclusive M1 end index,
  `t` = bar start, `c` = last M1 close — the "+900" close-time
  convention is consistent between engine and the independent verifier.

## Check 5 — handcheck_2d.py independence & result: PASS

- `grep`: `resolve_exit`/`src.exits` appear only in the docstring;
  `_v_exit` (lines 28-115) re-implements trigger/BE/legs/dragon/flat
  logic from raw M1 and computes its OWN `dm.resample` + `ind.dragon`
  (lines 50-51). It shares only data loading (`mg.light_ctx`), cost
  (`round_trip_cost`), roll (`_in_roll`, `_roll_px`) and session
  (`friday_flatten_ctm`) primitives — same functions the 2C baseline
  uses; acceptable for an "independent verifier".
- Re-ran `python runs/handcheck_2d.py`: **16/16 OK** on H0 and H1,
  covering `be`, an X2 leg-A partial (sampled row has
  `part_ctm=1267540800`, part fields checked at EPS), `dragon`, `flat`,
  `sl` — all on AUDUSD (first symbol having each reason).

## Check 6 — VALIDATION unread; HOLDOUT sealed: PASS

- `awk` over the LAB_LOG round-2D section (post-21:26:03Z): the only
  validation/holdout mentions are statements that neither was read
  ("no VALIDATION read; HOLDOUT sealed"); no unlock/read entry exists.
- Live guard test: `dm.load_m1('EURUSD', HOLDOUT_START, +86400)` and a
  window starting at `VALIDATION_END` both raise
  `PermissionError: HOLDOUT sealed ...` (HOLDOUT_START = VALIDATION_END
  = 1684333392, data.py:47/80-84).
- `grep -rn allow_holdout runs/ src/ tests/ conftest.py`: only the
  parameter definitions (`= False` defaults) and the docstring; no call
  site passes `allow_holdout=True` anywhere — including all round-2D
  scripts (`design_2d.py`, `verify_2d.py`, `managed.py`,
  `handcheck_2d.py`).
- Context note: `load_m1` legitimately serves data up to
  VALIDATION_END (design+validation span) — that is the seal boundary
  this lab defined; the 2D trade lists are the frozen 2C DESIGN-window
  fills (`order_cache.load_orders(sym,"F2_NH_b", dm.DESIGN)`,
  design_2d.py:147), so no candidate was evaluated on validation
  signals.

## Check 7 — sim.py baseline path unchanged: PASS

- `src/sim.py` lines 158-230: `exit_rule is not None` branches into the
  new layer; the `else` branch is the original 2C exit loop (SL-first,
  TP gap rules, `prev_suspect` post-suspect no-gap-bonus, E1b roll
  stress, Friday/daily flatten) structurally untouched. New kwargs
  (`exit_rule=None`, `tfx=None`, `pessimistic=False`) are inert
  defaults for all pre-2D callers.
- Empirical proof already stands via Check 2 (X0 through the new layer
  reproduces the 2C files byte-level on exits).

## Check 8 — RESULTS_v4 numbers vs CSVs: PASS

Recomputed pooled PF_R (`sum(r>0) / -sum(r<0)`, metrics.py:8-20) over
the 7 D-symbol `trades_2d_*` files:

| cfg     | harness | n    | recomputed PF_R x1 | reported |
|---------|---------|-----:|-------------------:|---------:|
| X0-HOLD | H0      | 9280 | 1.069708           | 1.0697   |
| X0-HOLD | H1      | 8444 | 1.085607           | 1.0856   |
| X0-DF   | H0      | 9280 | 1.204498           | 1.2045   |
| X0-DF   | H1      | 8444 | 1.093361           | 1.0934   |

Also spot-verified against `design_2d_summary{,_e1}.csv` POOLED rows and
the report: PF_R x1.5 H1 = 1.039807/1.023871 (reported 1.0398/1.0239);
X0-DF mean dR +0.03996 [+.0150,+.0654] H0 / -0.01613 [-.0417,+.0090] H1
(reported +0.040/-0.016 with the same CIs); r_gained/r_lost 2944.4/3080.6
(reported "2944R/3081R"); H1 reason mixes — X0-HOLD sl 4927/flat
1975/tp 1541, X0-DF flat 5298/sl 2457/tp 688, X1=X2 identical
(sl 3551/be 2237/flat 1425/tp 1230), X3 sl 3551/dragon 1958/be 992/
flat 981/tp 961, X4 sl 3552/dragon 2674/flat 1118/be 1100 — all match
exactly. The eligibility rule quoted in RESULTS_v4 §4 is verbatim the
frozen PREREG_V4 design rule (PREREG_V4.md lines 152-163).

## Notes (non-blocking)

1. RESULTS_v4 line 10 says the first `trades_2d_*` was written
   21:27:39Z; the earliest surviving mtime is 21:27:41.116Z (~2 s
   later; likely run-log vs file-mtime granularity). Freeze ordering is
   unaffected (21:26:03Z < either).
2. `handcheck_2d.py` imports `managed as mg`, which itself imports
   `src.exits` at module level — dead weight only; the verifier's
   decision logic is fully re-implemented. Confirmed no call.
3. Dragon timing nuance: an M15 bar closing exactly at the trigger
   bar's open (`t[j]+900 == t0`) is NOT evaluated (searchsorted
   `side="right"`, matching the prereg wording "CLOSES after the
   trigger bar's time" and mirrored identically in the independent
   verifier). Conservative direction only — no look-ahead possible.
4. H1 mixes contain a single `sl_same` row omitted from the prose
   counts (sums still 8444); reported numbers are unaffected.
5. Split snippet (PREREG_V4 lines 22-36) re-executed: reproduces
   D=[AUDUSD,USDCHF,GBPJPY,USDJPY,GBPUSD] and
   C=[NZDUSD,USDCAD,EURJPY,AUDJPY,EURGBP] exactly with seed 20260924.

No transcription errors with material effect found.
