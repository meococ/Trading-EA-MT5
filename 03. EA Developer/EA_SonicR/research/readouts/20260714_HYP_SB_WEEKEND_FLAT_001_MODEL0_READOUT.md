# HYP-SB-WEEKEND-FLAT-001 Model 0 Readout — 2026-07-14

Status: A1_RESEARCH_NONDESTRUCTIVE / GOAL_UNMET

## Authority

Owner MT5 full autonomy (stop terminal/metatester + Model 0 without per-run
approval). Self-research only (no ChatGPT). Management-only A1 weekend-flat on
SilverBullet USDJPY — not a carry/COT/open-range rescue.

## MT5 actions

- Stopped orphan metatester64 PIDs and 	erminal64 (incl. prior 53760/46972
  blockers and later competitors) under Owner authorization.
- Cleared/contended 
untime/alpha_backtest.lock after stopping competing
  lpha.ps1 backtest holders (UsBillSlopeBasket / VolExpansion).
- Alpha closeout threw includes_sha256 mismatch after both reports were ready;
  reports + analysis retained as research evidence.

## Runs (authoritative)

| Role | run_id | Overrides | Trades | tpw | PF | Net | MaxDD% |
|---|---|---|---:|---:|---:|---:|---:|
| Control | 20260714_002046 | InpUseWeekendFlat=0 | 519 | 1.9907 | 1.3288 | 7600.35 | 0.830 |
| Challenger | 20260714_002505 | InpFridayFlatHour=21;InpFridayFlatMinute=45;InpUseWeekendFlat=1 | 520 | 1.9945 | 1.3443 | 7875.93 | 0.828 |

Elapsed weeks (2021-01-01..2025-12-31): **260.7143**.

Compare artifact:
preflight/sb_weekend_flat/20260714_SB_WEEKEND_FLAT_MODEL0_COMPARE.json

## Gate vs GOAL

| Check | Result |
|---|---|
| PF > 1.30 (tester current spread) | PASS (ctrl 1.329 / chal 1.344) |
| Cadence 2–5 tpw elapsed | **FAIL** (chal **1.9945** < 2.00) |
| Challenger non-destructive vs control | PASS (PF/net slightly better) |
| Verified broker cost / cost-stress | **FAIL** (MetaQuotes-Demo current spread only) |
| Holdout split / confirmed suite | not run |

Verdict: weekend-flat A1 is **research-viable** (does not destroy the SB book).
**GOAL not met** — cadence floor + cost provenance.

## Explicit non-rescues

- Do not mine Friday hours, add sessions, or retune 21:45 from this readout.
- Do not claim promotion or confirmed.
- Earlier registry rows citing control 20260714_000937 are superseded by
  20260714_002046 / 20260714_002505.

## Next autonomous moves

1. Keep SB weekend-flat as parked research sleeve seed pending Real cost capture.
2. Do not reopen ChopTrend/CI family (FAIL_CLOSED duplicate).
3. Highest remaining lawful unblock for USBILL survivor / USD-factor: Owner
   login FivePercentOnline-Real + QFSI (credentials not inventable).
4. Continue self-research for independent price families not in killed lists.
