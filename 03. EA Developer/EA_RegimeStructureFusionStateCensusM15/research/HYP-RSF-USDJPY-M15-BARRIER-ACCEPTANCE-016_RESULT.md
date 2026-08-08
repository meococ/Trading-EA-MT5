# HYP-RSF-USDJPY-M15-BARRIER-ACCEPTANCE-016 - result

## Verdict

`KILL_NO_STABLE_BARRIER_EDGE`

Changing the target from terminal return to first-hit barrier acceptance did
not produce a stable USDJPY M15 edge. All six preregistered classifier/barrier
cells failed after dynamic cost; 2023+ remained sealed.

## Discovery result

The bound 2018-2022 M15 census generated 122,477 valid decision timestamps.
Unconditional long/short target-first rates were approximately symmetric:

- TP0.75/SL1.0: 53.12% long, 52.87% short;
- TP1.00/SL1.0: 44.43% long, 44.24% short;
- TP1.25/SL1.0: 36.72% long, 36.80% short.

All 24 expanding-year model fits and 72 threshold-fold evaluations ran. Best
was shallow HGB at TP0.75/SL1.0:

- 761 primary trades, cadence valid in all four folds;
- pooled PF 0.876617 and net -40.210299R;
- median yearly PF 0.854272;
- adjacent cadence PF 0.856233 and 0.878723;
- 2019, 2020 and 2021 lost; only 2022 won.

The selected book was heavily short-biased in early folds and did not improve
the unconditional path population enough to overcome cost. This is not a
threshold near miss.

## Decision

No barrier, threshold, direction, year, session or classifier rescue. The
failure radius is all-bar candidate generation. A legal successor may change
the event clock to sparse, rising-edge MBB S1/S2/S3 setup events and must pass
an outcome-blind cadence gate before any labels. That uses MBB as setup rather
than asking a model to scan every bar; it is not evaluated by this ID.

## Bound artifacts

- Parent census SHA256: `1FFA026BF50C431C87EC9EC9CE5DD7D17ABB26DBDB179680B8E75C5421642D2A`
- Results SHA256: `B413A33271B0BFA95A48F4DFD4EF8CE6B47C5DBFBE6D82FBDABF2B6A950E591A`
- Walk-forward folds SHA256: `17DF2E3E9D5187C745A3215B6557FA2A120E6F7CC8714F6B2E3CC8EF24B6755C`

