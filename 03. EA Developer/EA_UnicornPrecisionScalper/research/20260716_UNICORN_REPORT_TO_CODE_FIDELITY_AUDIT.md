# Unicorn report-to-code fidelity audit — 2026-07-16

## Verdict

`FIDELITY_GAP_CONFIRMED / PRIOR MODEL-0 KILLS APPLY TO THE PROXY, NOT THE FULL MEMO`

The completed Model-0 runs are valid evidence against the exact MQL5 detector
and execution paths that produced them. They are not a faithful test of the
full report-level Unicorn setup. The canonical detector is an alert-first
research skeleton and must remain non-mutating.

The main failure is not a hidden profitable parameter. The report defines a
conditional market-structure object; the EA reduced it to H4/D1 EMA state,
rolling sweep, one displacement candle, a three-candle FVG and geometric
overlap with any recent opposite candle body. Several report hard gates were
never implemented.

## Evidence boundary

- Strategy source: `05. Playbook/Strategy/Unicorn_Precision_Scalper_Deep_Research_Report.md`.
- Audited canonical source: `EA_UnicornPrecisionScalper.mq5` v1.21 before the
  correctness patch, SHA256
  `DF86D6CDB00B28CBAFD7FC9540497C60EDE8CD922F9B54470BB8AAD14D11C166`.
- Corrected alert-only source: v1.22, SHA256
  `A1AD68BC668C277D5EF85E54F61C28F0688D6FF9AC037A43368CECF45383B003`.
- No new PnL, fill, MFE, MAE or forward-return outcome was evaluated in this
  audit.
- Grok 4.5 supplied a read-only second opinion. The first call was cancelled
  before a useful answer; the resumed call completed. Final judgment and all
  local verification remained with the coordinator.

## Requirement-to-code mapping

| Report requirement | Report evidence | Current implementation | Status |
|---|---|---|---|
| Alert-first before full auto | lines 5–13, 37–41, 287–292, 460–464 | default-off mutation and bounded casebook (`mq5:7-10,376-386`) | Exact |
| Closed-bar/new-bar decision | lines 151–176, 246 | `CopyRates(...,1,...)` and M5 new-bar gate (`mq5:481-489,653`) | Exact |
| H4/Daily structure state | lines 116, 158–163 | close/EMA20/EMA50 proxy (`mq5:507-527,658-664`) | Weak proxy |
| M15 structure, M5/M1 entry | lines 5, 17, 78–79 | structure and pattern are M5-only | Missing |
| Sweep reclaim | lines 117, 162 | prior-range wick breach plus close reclaim (`mq5:561-627`) | Close proxy |
| MSS/BOS close hard gate | lines 118, 144, 161–164 | no swing parser or close-break state | Missing |
| Displacement quality | lines 119, 136, 191–195 | body/ATR only; minimum 1.20, 1.80 only scores strong (`mq5:22-23,673-676`) | Weak proxy |
| Fresh/unfilled FVG and fill ratio | lines 120, 185–197 | three-bar gap plus size only (`mq5:679-696`) | Missing |
| True breaker block intersecting FVG | lines 121, 182–190 | any opposite candle body overlap (`mq5:547-559,705-710`) | Weak proxy |
| Premium/discount hard condition | lines 122, 197 | rolling 25-M5 midpoint adds 10 points but does not reject (`mq5:712-726`) | Contradictory |
| Micro-confirmation/rejection/CISD | lines 123, 145 | not detected; label column only | Missing |
| Measured two-tier score | lines 140–176 | fixed `+15` and `+10` score mass has no measured feature (`mq5:722-726`) | Contradictory |
| News blackout | lines 144–156 | default off; required mode intentionally blocks all entries until data is bound (`mq5:41,538-545`) | Incomplete |
| Retest/confirmation execution | lines 231–244 | completed runs entered market immediately; CE-limit feasibility was separately killed | Contradictory |
| Fixed-fractional risk and hard guards | lines 204–227, 260–275 | cost-aware sizing, daily/weekly/DD/streak guards, BE and max hold | Largely exact |

Independent web discovery was used only as an ontology cross-check, not edge
evidence. Practitioner explanations converge on the minimum identity
`liquidity/structure shift -> breaker block intersecting FVG -> retest`; they
do not supply a reproducible pivot/freshness taxonomy or proof of profitability.

## Correctness and identity findings

### 1. Closed-bar invalidation bug fixed

The frozen HYP-006 prereg says the sweep remains valid only until any completed
M5 bar closes beyond the sweep extreme. The old MQL5 loop started at `left`, so
it did not explicitly examine the two most recent completed displacement/FVG
bars. v1.22 now scans every closed bar from index `0` through the bar after the
sweep for both directions.

The no-outcome replay found zero candidate changes from this correction on the
2024-01-01 through 2025-12-25 window. Therefore a new economic Model-0 rerun is
not justified: it would reproduce the same candidate identities after the
outcome was already opened.

### 2. Frozen build probe and Model-0 source were not identity-equivalent

The HYP-005 density probe used an eight-bar breaker scan, while the exact
Model-0 input and source used `InpBreakerLookback=6`. The identity audit found:

| Semantics | Candidates | Long | Short |
|---|---:|---:|---:|
| Build probe: breaker 8, invalidation through `left` | 251 | 205 | 46 |
| Model-0 source: breaker 6, invalidation through `left` | 234 | 190 | 44 |
| Corrected source: breaker 6, invalidation through decision | 234 | 190 | 44 |

There are 17 candidate identities in the probe/source symmetric difference.
This is a ceremony/provenance defect in build authorization, not evidence of a
profitable alternative. It does not erase the fact that the actual breaker-6
Model-0 source lost; it prevents treating the 251-candidate probe as an exact
preflight for that source.

### 3. The score is not a faithful confidence model

The scorer grants fixed points after earlier gates instead of measuring the
missing MSS and micro-confirmation. A score of 75 therefore does not mean the
report's confluence stack was present. Tuning the score threshold would tune a
mis-specified label and is prohibited.

## Interpretation of completed backtests

- `HYP-UPSC-XAU-M5-002` and `HYP-UPS-XAU-M5-006` falsify their exact market-entry
  proxies after cost; `HYP-UPS-XAU-M5-008` confirms changing RR did not repair
  them.
- `HYP-UPS-XAU-M5-007` falsifies the frozen three-bar CE resting-limit policy at
  the fill/cadence gate, without reading PnL.
- None of those runs tests a labeled book requiring MSS/BOS close, a true
  failed-order-block breaker, fresh FVG state and zone response.
- This distinction does not revive the family or imply that the full memo has
  edge. It means the full memo remains untested.

## Next legal research gate

Do not add MSS, retest or another structure threshold directly to the trading
EA. That would silently recombine killed PO3/KLR structure families and turn a
fidelity problem into post-hoc rescue.

The next candidate can be frozen only after the existing 200-row pre-outcome
HYP-005 casebook is reviewed without trade outcomes:

1. label true sweep, true displacement, MSS/BOS close, valid breaker, fresh
   FVG, zone response and final accept/reject;
2. use two independent reviewers where possible and require Cohen kappa
   `>=0.70` on final accept/reject;
3. if accepted density is below `25%`, close the detector-to-memo gap and stop;
4. freeze exactly one feature family from the label error matrix, de-duplicate
   it against PO3/KLR, and run a no-outcome density/separation probe;
5. only then create a new hypothesis id and one matched Model-0 challenger on a
   window not already opened for the child.

## Verification

- Signal-identity audit:
  `research/evidence/20260716_UNICORN_SIGNAL_IDENTITY_AUDIT.json`, SHA256
  `734804C00AAE08F6AAC3573BE86860C50054DFC9202C88D8568990EB720A79C6`.
- Package tests: `44/44 PASS`.
- Compile: `0 errors / 0 warnings`; EX5 SHA256
  `800DD0D4030D52AE93DD47E0F1F874FB0B694E9B5BEB0298F7CF59ADD2929ED1`.
- Exact-source non-repaint: `PASS`, zero findings; audit SHA256
  `A835169C33F3B55BF17FC96A659FBB81BED20B546E71FE5B2D168AEB633FC277`.
- Runtime/data path: portable `D:`. Protected C Common stayed exactly 137 files
  / 20,008,308 bytes with identical metadata hash. MT5 was stopped at close.

## Final status

`LOGIC_NOT_YET_ASSURED FOR ECONOMIC AUTO-EXECUTION`.

Engineering safety is materially stronger and the closed-bar invalidation bug
is fixed. Strategy fidelity is now explicitly audited, but it cannot be called
complete until the missing trader taxonomy is validated on sealed labels.

## v1.23 engineering closure

The audit finding for breaker fidelity is now represented by a dedicated blank
`label_true_breaker_valid` field. Source SHA256 is embedded in every V1.3 row
and metadata file. This improves label provenance but does not implement a true
breaker detector or close any of the strategy-fidelity gaps above. The v1.23
source SHA256 is
`10E278435644E63FD6418047AC775537CECEE8BBA4A9E5D89842E0F15312CB18`;
run `20260716_155111` collected 200 outcome-blank rows with zero trades.
