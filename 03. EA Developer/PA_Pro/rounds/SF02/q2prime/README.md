# Q2' — Volman setups on the Snapshot API (drafts only)

Per LEAD_RULINGS Review 1: Q2 (G1-G4 census/screens) is PAUSED until
P-v1 freeze. This folder holds the replacement deliverable — five
setup SPEC drafts written against a minimal Snapshot contract, plus
detector code exercised on synthetic fixtures. NO prereg, census, or
screen — all of that waits for P-FREEZE.

## Files

- `SNAPSHOT_CONTRACT.md` — the stand-in API the detectors consume
  (mirrors perception spec §2/§4 fields; only fixture construction
  changes when the real API freezes).
- `SPEC_PB.md`   — Pattern Break: with-pressure close beyond/ON a
  frozen box edge (>=2 touches on the breakout edge), proper buildup,
  signal bar may close ON the line under squeeze; 14-pip room.
- `SPEC_PBP.md`  — Pattern Break Pullback: poke through the broken
  edge's extension and close back; deep re-entry (past box mid) reads
  as failure, not PBP.
- `SPEC_PBC.md`  — Combi: strong bar + inside bar AT a boundary as an
  entry-timer only; colour/half-position rules; variants listed.
- `SPEC_PR.md`   — Pullback Reversal: counter-wave that touched/pierced
  EMA25 turns with pressure; trigger via pullback line, M/W middle,
  or second break; wave anchor = impulsive-leg start.
- `SPEC_TFF.md`  — Trade-for-Failure: counter-pressure break fails;
  barrier-reclaim rule (signal extreme back across the barrier) is the
  hard veto; first-retest preference.

## Code + tests

- `families/volman_setups.py` — shared helpers (tol, pressure, room,
  long-bar veto) + `detect_{pb,pbp,pbc,pr,tff}(snap, params)`.
- `families/test_volman_setups.py` — 20 tests on synthetic snapshots:
  positive fire, veto paths (room, pressure, stand-aside, abnormal
  bars), corrected rules (close-ON-line via squeeze, single-touch
  breakout edge rejected, barrier-reclaim veto, held-break veto),
  mirror side for TFF.

## Corrections applied from notes (vs RULEBOOK)

- signal bar may close ON the line (not strictly beyond);
- room rule = 14 pips to first real obstacle, not 2R;
- box edges frozen — pokes are T/F events, never redraws;
- non-breakout edge may stay single-touch;
- obstacles can be single-bar extremes (no 2-touch minimum);
- dominant pressure = M5 EMA25 slope + hysteresis; no HTF override of
  steep M5 pressure;
- TFF barrier-reclaim is a hard veto, checked on the signal extreme.
