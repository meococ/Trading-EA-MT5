# HYP-CME-OI-CONT-H1-FX-001 readout

State: **KILL_AT_OFFLINE_PROBE**  
Outcome opened: 2026-07-16 only after V2 preregistration, source profile and
candidate-registry authorization were hash-bound.

## Result

The official CME futures-OI participation field had enough density but did not
have positive post-cost expectancy in either unsealed split.

| Split | N | Trades/week | Gross PF | PF x1 | PF x1.5 | PF x2 | Net x1 | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train 2018-2021 | 886 | 4.245 | 1.121 | 0.878 | 0.787 | 0.706 | -43.01R | 14.93% |
| Internal validation 2022-2023 | 426 | 4.085 | 1.069 | 0.924 | 0.854 | 0.788 | -11.95R | 3.63% |

The price-only control PF was 0.784 train and 0.855 validation. The candidate
did not clear the frozen +0.10 PF margin. It passed 15/26 total gates. Cadence,
sample size and source integrity passed; edge, cost stress and net expectancy
failed in both splits. Train also failed the drawdown gate.

## Integrity

- Official source: 1,763 daily workbooks, 122,190,328 bytes on `D:`.
- Extracted exact EC/BP/J1 futures rows: 5,289; source failures: zero.
- Pre-outcome V1 was preserved after a hash-management error; the corrected
  V2 preregistration was separately hash-bound before any MT5 price bar loaded.
- Five of five probe tests and seven of seven source tests passed.
- Price-source skips: zero in both splits.
- 2024-2025 feature rows, bars and outcomes loaded: zero.
- Protected C-drive MT5 roots were metadata-identical before/after; terminal
  count at closeout was zero.

## Verdict

This is a terminal family kill. Do not reverse the direction, change the OI
threshold/ranking, mine symbol/day/hour, alter the 17:00-20:00 window, change
stop/RR or open holdout under this ID. No `.mq5`, MetaEditor compile or Model 0
is authorized because the frozen offline economics failed before build.

The next legal research action requires a materially different information
field and a new preregistration. Engineering or compiling this killed rule
would not provide valid GOAL evidence.
