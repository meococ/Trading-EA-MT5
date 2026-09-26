# PA-PRO LEADERBOARD

Program: PA-PRO (automated price-action, proven). Charter: `PA_PRO_CHARTER.md`
(SHA256 `3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C`).
Binding addendum 1 (zone-first perception + zone-generator bake-off):
`docs/CHARTER_ADDENDUM_1.md` (SHA256 `37756D6922C7134901E94940A10E03EF4E11F7B72418F754D2CEFFE525D38592`).

Splits: DESIGN 2016-01-01..2021-12-31 (search) | CONFIRM-PRE 2010-2015 | CONFIRM-VAL 2022-2023 |
OOS 2024-01-01..2025-06-30 | FINAL HOLDOUT 2025-07-01..2026-09-15 (sealed; Lead/Owner tokens only).
Cost tiers reported always: gross / x1 / x1.5 / x2. Screen gate: charter §8.

Status: **R01 complete (zone-generator level-physics bake-off). No winner. No valid evidence about
zone physics in either direction — the preregistered control was confounded by approach distance
(reviewer F1, Lead-accepted); one measured METHOD DEFECT found and carried to R02. No candidate
promoted; family screens not run.**

| rank | candidate | family | split | symbols | tf | N fills | WR x1 | PF x1 | PF x2 | lift vs random (95% CI) | t | gate verdict | ledger trials | report |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| — | (no candidate — R01 was a physics round, not a screen) | — | — | — | — | — | — | — | — | — | — | — | T000022..T000027 | `rounds/R01/ROUND_REPORT.md` |

R01 physics row (reaction proportions; NOT an economic candidate — no fills, no PnL):

| object | population | N resolved | bounce D_top (95% CI) | bounce gate | continuation D_top | verdict |
|---|---|---|---|---|---|---|
| 6 zone generators (baseline `line1_cluster`) | ARMED, DESIGN core, M5 | 3,288 … 30,782 | −5.3 to −7.4pp | FAIL ×6 | +20.9 to +28.7pp | **NOT VALID EVIDENCE either way** — control confounded by approach distance (F1); no winner |

Method defect: the Addendum-2 control compares two episode types (hover-arrival vs impulse-arrival),
so neither endpoint is attributable to the zones. Evidence: `rounds/R01/ROUND_REPORT.md`,
`rounds/R01/REVIEW_R01_PREFLIGHT.md`, `rounds/R02/CARRY_FORWARD.md`.



Reference row (NOT a candidate — mandatory regression of the dead DR3 object, kept for referee calibration):

| what | family | split | symbol | tf | N fills | WR x1 | PF x1 | lift vs random (95% CI) | verdict | ledger trials |
|---|---|---|---|---|---|---|---|---|---|---|
| frozen DR3 signals through the referee | `REGRESSION_DR3` | DESIGN | EURUSD | M5 | 2436 | 30.17% | 0.795 | +0.24pp [-1.61,+2.14] | FAIL (as in ECON-1) | T000002..T000021 |

Rules reminder: only `pa_eval.evaluate` may produce economic numbers (ledger-appended);
every evaluation is a trial; one look per frozen candidate at CONFIRM-PRE / CONFIRM-VAL;
OOS / FINAL HOLDOUT only with Owner approval.
