# HYP-SMOM-JPY-M5-002 — FROZEN PREREGISTRATION

Status: FROZEN before any governed run of this hypothesis ID.
Parent: HYP-SMOM-JPY-M5-001 (run 20260918_115433, PF 1.0045, n=6205).

## 1. Post-observation basis (declared per no-heuristic doctrine)

The 001 run was scored PF 1.0045 ≈ economic null and the family was about to
be written off. The trade-path autopsy (`tools/autopsy_mae_mfe.py`,
MAE/MFE reconstructed per executed trade on the 2025-26 coverage window,
n=312) showed the leak is in POSITION MANAGEMENT, not the signal premise:

- Winners (n=159): median MFE +43.7p (LDN) / +36.6p (NY), tMFE ~4-7h —
  the premise DOES precede large moves.
- Median MFE-capture: 0.38-0.43 — the session-end time-stop donates back
  ~60% of the available move.
- Losers (n=153): median MAE -38.9p / -33.9p with median MFE only 8.0p /
  2.2p — losers never produce movement yet ride the full drawdown to the
  catastrophe distance; there is no premise-invalidation exit.

Declared autopsy caveat: counterfactual exits on winners are
selection-on-survival, not proof. The engineered exits below are a NEW
mechanism variant; the governed run decides.

## 2. What changes (exactly the management layer)

Signal premise, levels, trigger windows, entry timing, session definitions,
filters, sizing: UNCHANGED from HYP-001 (frozen semantics).

New exit stack (checked every closed bar while a position is open):
1. BE move: floating profit >= 15 pips -> SL moved to entry + 2 pips.
2. Chandelier trail: once peak favorable >= 20 pips -> SL = peak - 12 pips
   (ratchets up only, never down).
3. Premise-invalidation cut: trade age >= 2h AND floating < 0 AND
   position-MFE so far < 10 pips -> close at market.
4. Session-end time stop, daily flat, Friday flat: unchanged backstops.

Rationale vs autopsy: losers' median MFE 8p means most never trigger BE or
trail; the inv-cut caps their tail near the -10..-20p region instead of
-39p. Winners' median MFE 43.7p means BE+trail typically locks ~25-30p.

## 3. Environment

Identical to HYP-001: USDJPY M5, 1999.01.01-2026.09.11 verified_m1_asof,
HQ 99%, build 6201, all spec inputs pinned via exact_overrides.

## 4. Kill / pass criteria (frozen)

- PASS: PF > 1.30 at cost x1, n >= 300, DD within budget.
- KILL this variant: PF <= 1.05 at x1 on n >= 300 (management engineering
  added no economics) OR per-leg shows the exit stack did not reduce the
  loss tail (losers' mean MAE not materially shallower than -39p baseline).
- FAMILY kill if 002 fails: premise confirmed dead end-to-end; no further
  SMOM cells without NEW Stage-0 evidence.
- Selection-on-survival subsets are not evidence; full executed set only.
