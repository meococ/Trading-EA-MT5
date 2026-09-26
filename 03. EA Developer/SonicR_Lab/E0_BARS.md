# E0_BARS — impossible-print inventory (A3F, pre-rerun STOP report)

Status: **STOPPED per backup plan** before any rerun. Two stop
conditions triggered (see §4). This file is the flagged-bar list the
brief asked for; nothing downstream was run.

LEAD_NOTE_5 sha256 (logged in LAB_LOG before any E0 output):
`234a49ec90c51e53ddacc680bc0affc8ca86742ebfe1dd3378bb32b6fcdac8ae`

Rule applied (frozen): bar i impossible iff
(a) `max(|h_i/ref_i - 1|, |l_i/ref_i - 1|) > 3%`, ref_i = close of last
non-impossible bar before i; (b) close of first bar ≥ t_i+15min within
0.5% of ref_i. Both harnesses; bars 2010 → VALIDATION_END only;
holdout never read. Implementation: `src/e0.py`, voiding via
`run_trades(void_extra=...)` — identical skip semantics to E1.
Tests T8/T9 in `tests/test_e0.py`: 5/5 pass (real EURUSD bar flagged,
SNB slice not flagged, synthetic ±, zero-flag = identical sim).

## 1. Counts

| symbol | total | DESIGN | VALIDATION | >20 stop? |
|---|---|---|---|---|
| EURUSD | 8 | 4 | 4 | |
| XAUUSD | **69** | **50** | 19 | YES |
| GBPUSD | 12 | 7 | 5 | |
| USDJPY | 19 | 15 | 4 | |
| AUDUSD | 15 | 8 | 7 | |
| NZDUSD | 13 | 9 | 4 | |
| USDCAD | 7 | 5 | 2 | |
| USDCHF | 8 | 7 | 1 | |
| EURJPY | 18 | 16 | 2 | |
| GBPJPY | **23** | 19 | 4 | YES (total) |
| EURGBP | 5 | 1 | 4 | |
| AUDJPY | **41** | **33** | 8 | YES |
| **total** | **238** | 175 | 63 | |

Full row-level list: `out/e0_bars.csv` (238 flagged + every (a)-pass
candidate incl. (b)-failures). Per-bar flags: `out/e0_flags_<sym>.npz`.

**All 238 flagged bars are already suspect=True** — E0 would change
nothing on H1; its entire bite is on H0.

## 2. Two populations

**A. Second-stamped corrupt-ladder prints — 14 bars** (`t % 60 != 0`),
all at the same recycled price levels (0.26272/0.42656/0.68080/1.01696/
1.67232/2.65536) across EURUSD, GBPUSD, USDCAD. Includes the two prints
that decided V1: EURUSD 2020-05-07 12:33:04 (2.65536, dev 146%) and
2022-10-19 13:47:44 (0.68080, dev 56%). Unambiguous data corruption.

**B. Minute-aligned session-reopen wick bars — ~216 bars**, all inside
roll windows, stamped 00:00 (FX) or 01:05 (XAUUSD daily reopen). Dev
3–10%, revert within 0.5% in 15 min. XAUUSD: 69 flags, almost all at
01:05 — the first bar after the daily break carries a fat wick that is
gone 15 min later. This population **mixes feed artifacts with real
market events** (see §3).

## 3. Named events — E0 flags REAL market events

| event | bar flagged | detail | verdict |
|---|---|---|---|
| SNB USDCHF 2015-01-15 | 00:00:00 | dev 19.6%, l 0.81889, c 0.89031, rev15 1.01862 | FLAGGED — SNB-day boundary bar; low is in the real SNB print range |
| GBP flash 2016-10-07 | 00:00:00 | dev 9.0%, l 1.14754 (~real flash low) | FLAGGED — real flash crash |
| JPY crosses 2019-01-03 | USDJPY 00:00:00 dev 3.8% l 104.72; AUDJPY 00:40 dev 4.7% | FLAGGED — real flash crash (real low ~104.8/70.3) |
| XAUUSD 2013-04-15 | 01:05:00 | dev 9.9%, l 1337, rev15 1481 | FLAGGED — bad-tick wick (gold did NOT revert to 1481 in 15 min that day) |
| Gold March 2020 | 2020-03-16 | — | NOT flagged |
| XAUUSD flash 2021-08-09 | 01:05:00 | dev 4.5%, l 1683 (~real low 1677-85) | FLAGGED — real flash crash that did revert fast |
| Brexit EURUSD 2016-06-24 | 00:00:00 | dev 4.2% | FLAGGED — Brexit-night range compressed into midnight bar |
| ECB EURUSD 2015-12-03 | 00:00:00 | dev 3.4% | FLAGGED — ECB day (EURUSD +3%) |
| FOMC EURUSD 2015-03-18 | 00:00:00 | dev 4.2% | FLAGGED — dovish-FOMC day (EURUSD +4%) |
| NZDUSD 2015-08-24 | 16:12:00 | dev 5.6% | FLAGGED — China "Black Monday" flash |

The rule cannot distinguish "corrupt print" from "real flash that
reverted within 15 min". Several flagged bars sit on the exact
event dates the brief listed as checks.

## 4. Stop conditions triggered

1. **>20 flagged in symbol-window**: XAUUSD DESIGN = 50, AUDJPY
   DESIGN = 33 (GBPJPY total 23, D=19/V=4).
2. **E0 flags real market events**: SNB, GBP-2016, JPY-2019,
   XAU-2021-08-09 flash crashes; Brexit/ECB/FOMC boundary bars;
   NZDUSD Black-Monday minute.

Per A3F backup plans: stopped, no rerun run, thresholds not touched.

## 5. Near-misses (rule (b) failed — kept)

1 bar: **EURUSD 2019-12-01 18:01:36** (dev 141%, second-stamped bogus
print at Sunday reopen) — (b) failed only because the first bar ≥+15min
landed 6 h later across a gap (revert_close within 0.58%, just over the
0.5% tol). Exactly the "bogus print right before a data gap/weekend"
case the brief warned about. Not flagged under the frozen rule; listed
here for the record.

## 5b. A4F — E0' second-stamped bar list (the rule that was kept)

LEAD_NOTE_6 withdrew the 3%/15-min price rule and froze **E0' = void
every M1 bar whose timestamp has non-zero seconds** (malformed record).
Format-based: no price, no future data, cannot touch a real market
event recorded as a normal M1 bar. LEAD_NOTE_6 sha256:
`c17bff6ab15d3b25347ef89d203a7599cfea31f9bdcad4516dc4518806dc7efc`
(logged in LAB_LOG 00:34:32Z, before the first E0' output).

Scan of all 12 symbols, 2010 → VALIDATION_END: **15 second-stamped
bars** — EURUSD 6, GBPUSD 5, USDCAD 4, all other symbols 0. Every one
sits on the corrupt price ladder (0.26272/0.42656/0.68080/1.01696/
1.67232/2.65536), dev 36-146% vs previous normal close; none within 1%
of neighbouring prices. All already suspect=True (H1 unchanged; the
rule bites H0 only). Per-bar detail: `out/e0s_bars.csv`; flags:
`out/e0s_flags_<sym>.npz`.

| sym | timestamp | o | h | l | c | ref | dev% |
|---|---|---|---|---|---|---|---|
| EURUSD | 2011-04-30 12:26:40 | 0.42656 | 0.42656 | 0.26272 | 0.42656 | 1.48048 | 82.3 |
| EURUSD | 2019-12-01 18:01:36 | 2.65536 | 2.65536 | 1.67232 | 1.67232 | 1.10145 | 141.1 |
| EURUSD | 2020-05-07 12:33:04 | 2.65536 | 2.65536 | 1.67232 | 2.65536 | 1.07906 | 146.1 |
| EURUSD | 2020-12-02 20:58:40 | 0.42656 | 0.42656 | 0.26272 | 0.26272 | 1.20943 | 78.3 |
| EURUSD | 2022-06-05 00:59:44 | 0.68080 | 0.68080 | 0.42656 | 0.42656 | 1.07183 | 60.2 |
| EURUSD | 2022-10-19 13:47:44 | 0.68080 | 0.68080 | 0.42656 | 0.42656 | 0.97939 | 56.4 |
| GBPUSD | 2012-03-20 03:56:48 | 1.67232 | 1.67232 | 1.01696 | 1.01696 | 1.58765 | 35.9 |
| GBPUSD | 2013-10-05 12:03:12 | 2.65536 | 2.65536 | 1.67232 | 1.67232 | 1.60097 | 65.9 |
| GBPUSD | 2014-05-21 01:23:12 | 2.65536 | 2.65536 | 1.67232 | 2.65536 | 1.68367 | 57.7 |
| GBPUSD | 2016-12-28 18:10:08 | 2.65536 | 2.65536 | 1.67232 | 1.67232 | 1.22374 | 117.0 |
| GBPUSD | 2017-12-06 14:34:40 | 1.01696 | 1.01696 | 0.68080 | 1.01696 | 1.33688 | 49.1 |
| USDCAD | 2012-08-09 18:22:56 | 1.67232 | 1.67232 | 1.01696 | 1.01696 | 0.99220 | 68.5 |
| USDCAD | 2015-04-01 14:26:08 | 0.42656 | 0.42656 | 0.26272 | 0.42656 | 1.26752 | 79.3 |
| USDCAD | 2018-02-14 09:23:12 | 2.65536 | 2.65536 | 1.67232 | 1.67232 | 1.25727 | 111.2 |
| USDCAD | 2020-04-10 05:11:28 | 0.68080 | 0.68080 | 0.42656 | 0.68080 | 1.39889 | 69.5 |

T10 (tests/test_e0.py): both V1-deciding bars and the 2019-12-01
gap-side print flagged; no minute-aligned bar flagged; no-flag window
reproduces existing files. 8/8 pass.

## 6. If the Lead still wants the rerun (decision pending)

The clean mechanical interpretation: flags stand, H1 is unaffected
(all 238 already suspect), H0 loses the 14 corrupt prints plus ~216
reopen-wick bars. Alternative the Lead may prefer: restrict E0 to the
second-stamped corrupt-ladder population (the `second_stamp` helper in
`src/e0.py` already computes that mask — 14 bars, zero real events).
That is a threshold/scope decision for the Lead, not for me.
