# HYP-004 Random100 chart timebase erratum

Status: `ORIGINAL_VISUAL_PATH_EVIDENCE_INVALID / ECONOMIC_KILL_UNCHANGED`

## Finding

The original Random100 case builder copied MT5 lifecycle `event_time` directly
into fields named `entry_time_utc` and `exit_time_utc`. Lifecycle `event_time`
comes from `HistoryDealGetInteger(..., DEAL_TIME)`, which is FivePercent broker
server time. `chart_case_render.py` then used its default `time_utc` bar column.
The original 200 PNGs were complete and hash-bound, but their candle windows
were on the wrong clock.

An entry-price alignment audit over the frozen 100 cases produced:

| Clock used for the case timestamp | Matched entry bars | Median distance | P90 distance | Within 5 points |
|---|---:|---:|---:|---:|
| Original mislabeled UTC | 99 | 54.0 points | 180.2 points | 7 |
| Broker server clock | 99 | 0.0 points | 2.0 points | 93 |

This invalidates the original Grok path-shape labels and the derived
43/21/21/15 mechanism counts. It does not invalidate the frozen sample IDs,
the report/lifecycle P/L, or the matched control/challenger economics.

## Correction

1. `prepare_hyp004_random100.py` now converts broker server time through the
   canonical `fivepercent_server_clock.py` before populating any UTC field.
2. `chart_case_render.py` records the selected `time_col` in its manifest.
3. `validate_hyp004_random100_casebooks.py` binds the bar/case hashes and
   fail-closes unless all 200 entry/exit marker events map to UTC M1 bars with
   median distance at most 5 points, P90 at most 10 points and maximum at most
   20 points.
4. The corrected V2 corpus is separate from the original corpus:
   `random100_forensics_clock_v2/`.

Corrected V2 QC:

- 100 decision-as-of PNGs and 100 anatomy PNGs;
- 200/200 marker events matched;
- median marker-to-bar distance `0.0` points;
- P90 distance `2.0` points;
- maximum distance `15.0` points;
- receipt status `PASS`.

## Hash bindings

| Artifact | SHA256 |
|---|---|
| `random100_forensics_clock_v2/random100_sample_manifest.json` | `C009F6554F46084D57A59C0D3F766CD0D68442ABA49D32D5C50A756E49144D16` |
| `random100_forensics_clock_v2/random100_cases.csv` | `B6B7E87BC78EFA37C3984D7034CF3C6D97B5CF7015136DB3623CD4CCB9D66753` |
| `random100_forensics_clock_v2/decision_asof/cases_manifest.json` | `F5617EE72638D12D74358A8BEDBD3D06B00C9B051651C1C25A5EBCCF113AC221` |
| `random100_forensics_clock_v2/anatomy/cases_manifest.json` | `23D5FD11428FD771CA91ADEE0CAD2E4E8346509C0BA37E9331B9503C45B5DCA8` |
| `random100_forensics_clock_v2/random100_casebook_qc.json` | `4CD04614A5A388AD56538CEF1E2CFA07CE0B37B8BCA0250D92CECD795854DAA3` |
| `path_geometry_analysis_v2.json` | `5BFDE9E63EB9AB67F55A750E128D93DFAD82453A587041EA0F0B280916A08729` |

## Economic boundary

The terminal decision remains
`KILL_VALID_MATCHED_PAIR_NO_POSITIVE_EXPECTANCY`: control PF `0.698096`,
challenger PF `0.691278`, and challenger mean realized R `-0.231790`.
Corrected visual review may change the explanation of realized paths, but
cannot reopen HYP-004 or authorize same-ID optimization, tuning, paper, live or
promotion.
