# VPA-DR3_ECON1_PREREG — first economic baseline (FROZEN)

Task: T-VPA-ECON-1. Authority: `research/LEAD_DECISIONS_ECON1.md` (G1–G6) →
`research/HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md` → this prereg → code.
Frozen BEFORE any fill or outcome is computed (G1). No outcomes existed in the
lane before this file. `G4`: exactly ONE verdict run, no parameter changes.

## 0. Frozen code (SHA256, no edits after this point)

| Artifact | SHA256 |
|---|---|
| `research/lab/vpa_dr1.py` (DR3 detector) | `73497484E2C26EDF44DAE5F1D574C56BBF40BBBFE8192A05AD38B4D782A781E0` |
| `research/VPA-DR3_FROZEN_PREREG.md` | `A61F06BA776BD0D74A94FBFD243ECFFC9C880988832BAEC789F50DAA675E05A2` |
| `research/lab/vpa_econ1_sim.py` (fill/exit engine) | `9A5113CC3A93ED40A7B8BC62B4CD288B7992A1FBAFDB57AD996BA3101715596B` |
| `research/lab/vpa_econ1_costs.py` | `4B9F0EC330A2003935276876BEF952D1CBCE045F6E54E0EF5F4C01B72532F274` |
| `research/lab/vpa_econ1_random.py` | `07719AF87CB35298B2D990B8339E6883488537E258AC6FB879C08EC19A210A99` |
| `research/lab/vpa_data.py` (loader, incl. the F4 time fix) | `E0DEC3808AF7D2BD730C1A6185D6E850B306459DDFC00DDD8AA776A909D7212F` |

## 1. Signals

DR3-accepted records only, from ONE detector run with `DR3_CFG` + `round_grid_price
= 50 pips` + `collect_gates=True` on DESIGN. Nothing else. The detector's own
gate path is frozen (DR3 prereg §2–3). Each signal carries: signal bar index
`sig` (= `rec["bar_idx"]`), the trigger bar (= `rec["trigger_idx"]`), side,
`entry_level` (= signal-bar extreme ± 1.0 pip), `invalidation` (= buildup extreme
± 0.10×ATR), ATR, setup (PB/Combi), and the logged features (room_r, ema_dist_atr,
squeeze, lunch, pressure, chop_window, buildup variants, rho).

## 2. Order model (frozen)

1. After the close of `sig`, place a stop order at `entry_level`.
2. Valid for `V = 3` M5 bars: fill search over the M1 path of `[sig+1, sig+4)`;
   no fill afterwards → EXPIRED (no trade).
3. Cancelled before fill if the invalidation is touched (long: `low ≤ inv`,
   short: `high ≥ inv`). Inside one M1 bar the cancel is checked BEFORE the fill
   (adverse-first; conservative).
4. Fill = `max(open, stop)` (long) / `min(open, stop)` (short) at the first M1
   bar trading through the stop → gap-aware. The gap size
   `d*(fill−stop)/ATR` is logged; the HYP §3.3 `>0.3×ATR` recheck is NOT a
   trade filter in ECON-1 (reported as a sensitivity in the exploratory section).
5. No new order at/after Friday 20:00 server (VETO_FRIDAY).
6. No BE / trailing / partials / manual exits.

## 3. Cost (frozen)

`c_rt` p90 EURUSD = **1.0 pip** (`PLAN/COST_FEASIBILITY.md:75`; spread p90 0.1 +
slip p90 RT 0.2 + comm 0.7), applied ONCE as an adverse shift of the fill
(`PLAN/COST_FEASIBILITY.md:118`, `vpa_random_baseline.py:130,194`). Scenarios:
`x1 = 1.0` (primary), `x1.5 = 1.5`, `x2 = 2.0`, plus `gross = 0.0` (sanity only,
not a gate).

## 4. Bracket and exit (frozen)

- `S = 8.0` pips; `SL = fill − S`; `TP = fill + 2S` (b = 2.0 nominal).
- Resolution on the M1 path, **SL checked before TP inside every M1 bar**
  (same-bar TP+SL → SL).
- Safety flats: daily close at the first M1 close with server hour ≥ 22:00;
  Friday close at the first M1 close with Friday server hour ≥ 20:00; server
  midnight fallback (previous M1 close).
- Exit reasons: SL, TP, DAILY, FRIDAY, MIDNIGHT, DATA_END.
- `r = d*(exit − fill)/S`; SL = −1.0; TP = +2.0.

## 5. News (G2)

`NEWS: NOT AVAILABLE` — the ForexFactory EURUSD high-impact CSV/JSON for
2019–2022 are absent from the repo (gitignored, never committed; see
`PLAN/econ1/NEWS_CALENDAR_RESEARCH.md`); the surviving MQL5 datetime array is
2019–2022, unlabeled, `C_DIAGNOSTIC_ONLY`, and covers zero 2016–2018 events.
The verdict run applies NO news filter. A SENSITIVITY check (no effect on the
verdict) excludes signals whose bar closes in the fixed windows
`utc_min ∈ [745, 765)` (12:25–12:45 UTC) or `[805, 825)` (13:25–13:45 UTC);
FOMC days are not derivable for 2016–2020 → not filtered.

## 6. Split (G5)

DESIGN 2016.01.01 → 2021.12.31 ONLY (`vpa_data.load_m5_bars` defaults y0=2016,
y1=2021; the loaded frame's min/max dates are reported). VAL / OOS / HOLDOUT are
NOT loaded by any script in this task.

## 7. Matched-random baseline (G3)

- For each DR3 signal, K = **20** random entries from the DESIGN M5 bars with the
  same cell `(session, hour-of-day, weekday, month)`, drawn uniformly with
  replacement; direction drawn with P(long) = the DR3 signals' long share.
- The random entries go through the SAME engine with the SAME bracket and flats,
  but **no invalidation cancel** (random entries have no buildup; the frozen
  baseline semantics also have none) — documented asymmetry.
- Random entries also get the Friday veto.
- Seed `20260920`; the generator is `vpa_econ1_random.match_random`.

## 8. Metrics and gates (G3/G6)

Per cost scenario: `N` (fills), `WR = P(r > 0)`, `PF = Σr⁺/|Σr⁻|`, `gross PF`
(scenario gross), `b = mean(r⁺)/|mean(r⁻)|`, expectancy, total R, exit-reason
mix, and max DD of the 0.5%-risk fixed-fractional equity curve (risk 0.5% of the
initial equity per trade, trades ordered by exit time; DD relative to the running
peak).

| Gate | Threshold |
|---|---|
| PF x1 | > 1.30 |
| PF x1.5 | ≥ 1.25 |
| PF x2 | ≥ 1.00 |
| gross PF | ≥ 1.10 |
| N fills | ≥ 500 |
| max DD @0.5% | ≤ 6.0% |
| realised b | ≥ 1.70 |
| LIFT x1 | WR_DR3 − WR_random ≥ +14.1pp AND 95% CI lower bound > 0 |
| LIFT x2 | WR_DR3 − WR_random ≥ +18.2pp AND 95% CI lower bound > 0 |

Verdict: all pass → PASS; any fail → FAIL with the per-gate table (G6). The
required-lift numbers come from `HYP-VPA-EURUSD-M5-001_FROZEN_PREREG.md:83-85`.

## 9. One run (G4) and the exploratory section

The verdict run is executed once (DR3 signals + matched random + the three cost
scenarios) and is not re-run with different parameters. The EXPLORATORY section
reports WR/PF by feature tercile (room_r, ema_dist_atr, squeeze, lunch, session,
PB vs Combi, long vs short, per year) and the gap-recheck and news-window
sensitivities — all from the SAME trades, clearly labelled, with no effect on the
verdict.

## 10. No-look-ahead (contract)

A trade reads only M1 bars after its own signal bar; the fill scan is bounded by
`[sig+1, sig+4)`; the exit scan starts at the fill bar; the equity/DD use the
exit times. The detector itself is causal (DR3 prereg; significant-pivot fix
`j = t − S`).

## ADDENDUM A1 — post-freeze code alignment (recorded before any outcome)

The initial freeze (17:50:11) hashed `vpa_econ1_sim.py` at
`9A5113CC…`; that revision already contained the V=3 window but not the
**session-end cancel required by §2.3 of this same prereg**. The engine was
aligned to §2.3 immediately after (adding `next_end` truncation of the fill
window; unit test `session_end_cancel`), and the unit suite re-run
(`TESTS PASS 19/19`). Corrected hash:

| Artifact | SHA256 (corrected) |
|---|---|
| `research/lab/vpa_econ1_sim.py` | `87D3C73507666B58AAA0553D1A3F6FE0EF03EDFB645D012C59080A2E23E33930` |

Timeline: prereg mtime 17:50:11 → engine alignment 17:51:02 → this addendum →
the verdict run (the first outcome file). `PLAN/econ1/TRADES_DESIGN.csv` did not
exist at the time of this addendum (verified). No other frozen artifact changed.
The final prereg SHA256 is recorded in `PLAN/econ1/ECON1_RESULTS.md` §0 and in
the report; it must be earlier than every `PLAN/econ1/*` outcome file.
