# De-dup Fail-Closed — HYP-CHOP-TREND-M15-001 — 2026-07-14

Status: `KILL_AT_INTAKE_DUPLICATE / FAIL_CLOSED`

## Proposed ID (from TickVolImpulse next-move)

| Field | Value |
|---|---|
| Hypothesis ID | `HYP-CHOP-TREND-M15-001` |
| Proposed EA | `EA_M15ChopTrend` |
| Seed cited | STRATEGY_LOG `S630 / EA_ChopRegime` (PF~1.26, Mon+Wed+Thu Europe) |

## Closed family check

| Family / evidence | Result |
|---|---|
| `EA_ChopRegime` shelf | **`KILL_FAMILY`** — untouched 2018-2020 OOS PF `1.025976` (`20260710_EA_FAILURE_PORTFOLIO_AUDIT.md`) |
| Mechanism | CI regime gate + EMA fast/slow cross + trend EMA — identical causal surface as proposed ChopTrend |
| S629 baseline (no Mon/Wed/Thu tight mining) | PF 1.12 — already below Gate 1 / GOAL 1.30 |
| S630 / S631 | Day-of-week mining on the same CI+EMA engine; post-hoc density filters |
| Killed M15 cadence-book / TickVolImpulse | Explicitly **not** the same entry; cadence-book prereg already labels ChopRegime `KILL_FAMILY` |

## Why this is a twin rescue

Removing Mon/Wed/Thu day mining and renaming to `EA_M15ChopTrend` does **not** create an independent hypothesis. It reopens the killed ChopRegime family on the same USDJPY M15 CI+EMA-cross surface. Doctrine: fail closed on twin rescue; do not prereg / compile / Model 0.

## Authority granted / denied

- **Denied:** registry row, prereg freeze, EA build, compile, Strategy Tester / Model 0 for `HYP-CHOP-TREND-M15-001`.
- **Allowed next (independent, already contracted):** `HYP-VOLEXP-M15-001` / `EA_M15VolExpansion` (S639 VolCluster RV-expansion; prereg explicitly no CI; differs from ChopRegime).
- USBILL Model 0 remains blocked on `FivePercentOnline-Real` cost provenance — orthogonal lane.

## Owner context

Owner unlimited MT5 backtest authority (2026-07-14) does **not** waive de-dup / no-rescue. Free Model 0 applies to legal independent IDs only.
