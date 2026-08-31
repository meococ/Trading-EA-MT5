# AlphaFactory + EA Full-System Review — Grok Deep Research Campaign

Date: 2026-07-27  
Mode: read-only forensic review; no source, registry, verdict, run, or deployment mutation  
Campaign: `.context/alphafactory-full-review-20260727/`  
Coverage: 18/18 compilable MQL5 packages + 14/14 research-only records

## 1. Executive verdict

The workspace has a materially stronger research and evidence discipline than a
typical MT5 repository: canonical source routing, one active registry, pre-outcome
freeze rules, closed-bar/non-repaint doctrine, cost and robustness tools, global
MT5 locking, D:-resident tester storage, and broad automated tests are all real.
The current review does **not** establish a deploy-ready EA or a new positive edge.

The system is best classified as:

| Layer | Review verdict |
|---|---|
| Engineering-valid | **PARTIAL** — 18 packages are discoverable and 131 AlphaFactory tests pass, but the promotion path still contains semantic honor-system fields and several EA sources have execution/state defects. |
| Economic-valid | **PARTIAL / record-specific** — most terminal economics remain usable only inside their declared failure radius; Kalshi and CFTC need terminal-class correction, and HybridRegimeMR HYP-001 did not run the frozen C1 object. |
| Promotion/deploy-ready | **NO** — no package has a complete, semantically reconciled real-tick/report/lifecycle/cost/robustness delivery chain. |

The highest-leverage work is not a new entry filter. It is to make the evidence
authority fail closed, then standardize order/fill/risk/state handling across the
reusable EA kernels. Until those controls are complete, a good signal can still
be misclassified by the harness or implemented with unsafe execution semantics.

## 2. Scope and method

The parent froze one campaign manifest, then used the `grok-cli-runner` in bounded,
read-only packets:

- one `/deep research` benchmark packet;
- one AlphaFactory orchestration/gates/statistics packet;
- three disjoint MQL5 logic packets covering all 18 canonical `.mq5` packages;
- three accepted research-record packets covering all 14 research-only packages.

Two oversized research packets were cancelled/superseded; they are not accepted
evidence. Accepted packets ended with `EndTurn`, parsed against their requested
JSON schemas, and remain under the campaign directory. The Deep Research wrapper
SHA256 is:

`CE27F59057E0AB89000186239A4A6E89973EDF5F3B37749326732194F425238A`

Grok emitted 75 raw findings (7 critical, 29 high, 33 medium, 6 low). Those counts
are not unique defects: several are duplicate manifestations or known terminal
facts. Parent QC rejected the two GLDFlow/GoldMacro clock findings and one invalid
low-severity citation, downgraded findings on terminal/non-authorized sources, and
reconciled the remainder against local artifacts and prior review evidence.

## 3. Priority decision surface

### P0 — block false promotion/economic authority

#### P0.1 Model 0 is mislabeled as real ticks

`02. AlphaFactory/analysis/unified_validation.py:2658-2668` passes
`run_manifest.model == 0` under a gate named `mt5_real_ticks_model` and explicitly
calls it “MT5 real ticks”. `02. AlphaFactory/tools/research_loop_engine.ps1:1219-1221`
repeats the label. MetaTrader distinguishes generated “Every tick” from “Every
tick based on real ticks”; local `02. AlphaFactory/STRATEGY_LOG.md:2674-2676` also
records real ticks as Model 4.

Impact: Model-0 research can still be useful when prospectively declared, but it
must not satisfy a real-tick-fidelity claim. This is a promotion blocker, not a
claim that every Model-0 result is economically meaningless.

#### P0.2 Report identity is partly built from the manifest, not read from the report

`02. AlphaFactory/alpha.ps1:1032-1076` parses broker/account/history quality/bars/
ticks, but the data fingerprint injects manifest symbol/period/window/model. It
does not semantically parse and reconcile the report's actual expert, model,
window, or effective inputs. A dropped or malformed override can therefore leave
the receipt internally consistent while the tester executed a different object.

#### P0.3 Delivery and fast-kill accept self-asserted semantic reconciliation

- `02. AlphaFactory/tools/validate_ea_delivery_packet.py:207-225` checks supplied
  values such as `report_lifecycle_reconciled`, counts, model, and unresolved errors,
  but does not derive those values from the report/lifecycle files.
- `02. AlphaFactory/tools/validate_fast_kill_closeout.py:203-216` checks that economic
  metric fields are finite and sample-sized, but does not reconcile them to the
  bound report/summary artifact.

Hash existence is necessary but not enough: the validator must derive the decision
fields from the bound bytes.

#### P0.4 Candidate-registry validation does not hash-check terminal validation artifacts

`04. Memory/research/validate_candidate_registry.py:154-180` verifies canonical
source and prereg bindings for execution states, but not arbitrary paths/SHAs under
`validation`. This is no longer only a theoretical gap: the Kalshi terminal row
passes the registry validator while its bound probe/report/readout SHAs do not
match current files.

### P1 — correct three research-record decisions

#### P1.1 Kalshi kill authority is broken and the source corpus was incomplete

`04. Memory/research/CANDIDATE_REGISTRY.jsonl:64` binds:

- probe `4dbe6db7...`, current file `de69a3ac...`;
- report `21fafab5...`, current file `96ffefa2...`;
- readout `6761c551...`, current file `185cff39...`.

The evidence also sets `trade_acquisition.complete=true` despite 153 recorded
HTTP 429 acquisition errors. The row timestamp precedes the current evidence
files, so the current bytes cannot be the bytes that authorized that transition.

Decision: the exact row is **INVALID/PARK pending provenance repair**, not a clean
complete-corpus economic kill. Gross PF below 1 on the acquired subset remains a
useful diagnostic; it must not be generalized to the missing archive.

#### P1.2 CFTCOptions overstates a three-symbol economic kill

The probe rejected 532 GBPUSD historical rows because its market-name guard did
not accept the source identity. The readout honestly discloses that integrity
failure, but still closes the full CFTC TFF weekly-positioning object. EURUSD and
USDJPY economics remain diagnostic and negative; the three-symbol contract is not
economic-valid.

Decision: classify the exact three-symbol object **INVALID/PARK**, retaining the
two valid symbol results as diagnostics. Do not rescue or retune the same ID.

#### P1.3 HybridRegimeMR HYP-001 did not execute its frozen C1 object

`HYP-MR-REGIME-EURUSD-H1-001_PROBE_PLAN_V2.md:96-101` freezes C1 without trailing
or cooldown and allows C2 only after C1 survives. `mr_probe_engine.py:1-8` and its
trade loop always apply both. HYP-001 therefore cannot prove that the minimal C1
core failed.

The later HYP-002 grid did cover trailing on/off over 8,100 simulations and found
zero gross PF >= 1.25 survivors. That later result preserves the scoped Stage-1
family closure; it does not repair HYP-001's identity. No same-ID rerun is advised.

### P1 — standardize reusable EA execution semantics

Across the active source shelf, repeated risks are:

1. no `OrderCheck` before market entry;
2. treating send acceptance/`PLACED` as a confirmed fill;
3. no `DEAL_ENTRY_IN` reconstruction and post-fill cash-risk reconciliation;
4. position/identifier scans that continue after `ticket == 0` or selection failure;
5. daily, cooldown, pending, partial, BE, and initial-risk state held only in RAM;
6. minimum-lot normalization that can exceed the frozen cash-risk budget.

These are shared-kernel problems. Repairing package by package without a frozen
execution contract would create drift.

## 4. AlphaFactory system assessment

### Strengths confirmed

- `alpha.ps1 status` resolves the canonical D:-resident portable MT5 runtime,
  disallows `FILE_COMMON`, and discovers all 18 MQL5 packages.
- The registry is append-only in practice and currently parses as 262 rows / 86
  hypothesis IDs.
- Source/prereg canonical binding, global lock surfaces, closed-bar/non-repaint
  policy, exact-cadence doctrine, cost tiers, WFA, CSCV/PBO, White Reality Check,
  Monte Carlo, sensitivity, regime and execution analysis all exist.
- The Two-Speed split is conceptually sound: fatal preregistered cells can close
  cheaply while survivors require Heavy-Delivery.
- 131 current AlphaFactory tests pass. This proves the present contracts are
  internally satisfied; it does not prove the missing semantic checks above.

### Secondary gaps

- White Reality Check exists; Hansen SPA is not implemented. This matters when a
  large family contains many poor alternatives that can dilute White RC power.
- DSR exists in the research kit but is not a universal fail-closed promotion gate.
- History quality is fingerprinted, but real-tick journal/volume-mismatch evidence
  is not a semantic promotion gate.
- Delivery engineering/analysis status remains partly declarative; tests currently
  encode that honor-system surface as a passing contract.

## 5. MQL5 package review

The classifications below concern source integrity/reuse risk, not permission to
run, promote, or deploy.

| Package | Main reviewed risk | Parent classification |
|---|---|---|
| EA_FVGConfluence | No OrderCheck/fill reconstruction; stop may widen after sizing; fail-open traversal; RAM-only management flags | High reusable-kernel debt |
| EA_HybridICT_Sonic | Fail-open enumeration; no OrderCheck/post-fill risk/lifecycle | High reusable-kernel debt |
| EA_ICTFVGReportFidelity | Owned-position lookup continues after invalid ticket | Medium; fill-risk shell otherwise stronger |
| EA_ICTVisualEdge | Research scaffold can send direct market orders without preflight/guards | High terminal-source safety issue; not active deployment |
| EA_KLR_Scalper | Force-min volume can exceed budget; no preflight/post-fill risk | High |
| EA_LSSOBPropScalper | Fail-open position traversal | Medium |
| EA_MZMS_Scalper | No OrderCheck/post-fill risk; daily state not persistent; BE path disabled | High |
| EA_SweepCascadeContinuation | No actual-fill risk reconciliation; UTC-day key RAM-only; manage scan fail-open | High |
| EA_UnicornPrecisionScalper | Identifier scans fail open | Medium; comparatively strongest signal/execution shell, still not deploy-ready |
| EA_UnicornPrecisionScalperControl | No OrderCheck/post-fill enforcement; no focused behavior tests | Medium |
| EA_UnicornPrecisionScalperRR15 | Inherits Unicorn execution gaps; magic collides with Control | Medium |
| EA_VRAS_H1StructuralScalper | `InpResearchAutoMode`, risk/news/account inputs unused; flawed sizing/fill telemetry | High known terminal-source defect; no rerun authority |
| EA_VRAS_PathConfirmedTrend | Pending trend state is RAM-only and lost on restart | Medium |
| EA_VRAS_QuoteTickAcceptance | Collection-only authority is explicit; source is sound for that narrow role | Sound collection-only; not economic/deploy authority |
| EA_VRAS_RegimeAdaptiveScalper | Misinterprets OrderCheck success and blocks entry/close | Known terminal engineering-invalid record |
| EA_VRAS_RegimeAdaptiveScalperV2 | Default identity/magic conflicts with validation guard | Known terminal engineering-invalid record |
| EA_VRAS_RegimeAdaptiveScalperV3 | Send acceptance without fill proof; no post-fill cash-risk enforcement; fail-open scan | High reusable-kernel debt |
| EA_VRAS_VolatilityNormalizedStop | Measures post-fill risk but does not act; restart loses initial SL/entry globals | Medium |

No package receives a promotion or deployment recommendation from this source-only
review. `EA_VRAS_QuoteTickAcceptance` is accepted only for its frozen no-outcome
collection role.

## 6. Research-only record review

“Sound” below means internally sound for its narrow terminal/data-contract claim;
it does not mean profitable or deployable.

| Record | Assessment |
|---|---|
| EA_ASRS_AdaptiveSweepReclaim | Sound scoped terminal record |
| EA_CFTCOptionsPulse | Defect: three-symbol failure radius exceeds valid data plane |
| EA_CME6E_RawBreakBookState | Sound scoped terminal record, including clock-corrected successor and image forensics |
| EA_CMEParticipationPulse | Sound scoped terminal record |
| EA_DRAT_ONNX_ICT_Hybrid | Sound scoped terminal record |
| EA_ECRS_CompressionReleaseScalper | Governance debt: HYP-001 cadence floor was not bound in a PROBE_PLAN; HYP-002 memo predeclares it. Both were outcome-blind parks, so no economic verdict is invalidated. |
| EA_EURSessionDrift | Sound scoped terminal record |
| EA_GLDFlowPulse | Sound within frozen as-run contract after parent refuted Grok's clock finding |
| EA_GoldMacroPulse | Sound within frozen as-run contract after parent refuted Grok's clock finding |
| EA_HybridRegimeMR | HYP-001 identity defective; later HYP-002 grid preserves scoped Stage-1 family closure |
| EA_KalshiMacroPrint | Critical provenance and incomplete-acquisition defect; reclassify exact row INVALID/PARK |
| EA_PO3_AMD_Scalper | Deep Research intake HTML is missing and HYP-001 lacks a registry-bound plan; probe artifact remains bound. Medium provenance debt, not evidence of hidden edge. |
| EA_SGEFixingPulse | Sound; profiler has a low-severity hardcoded audit-time gate |
| EA_VRAS_FirstPassageAcceptance | Plan overclaimed MT5-equivalent partial-bar handling, but the parity gate caught it and the readout correctly parked engineering-invalid before outcomes. Terminal decision remains sound. |

### Refuted Grok findings

Grok claimed GLDFlow and GoldMacro treated FivePercent server-wall time as UTC.
Both scripts obtain bars through MetaTrader5 Python `copy_rates_range` and convert
the returned epoch with `pd.to_datetime(..., utc=True)`. The official MetaQuotes
Python contract states that returned bar times are UTC. The workspace's explicit
server-to-UTC clock model applies to naive exported/parquet server timestamps, not
these Python API epochs. Their kill scopes are unchanged by this review.

## 7. Existing blockers versus new information

| Class | Findings |
|---|---|
| Existing and reconfirmed | Model-0/real-tick mislabel; report/effective-input reconciliation gap; delivery/fast-kill self-assertion; registry validation surface; H1Structural unused inputs; broad order/fill/traversal weaknesses; V1/V2 terminal engineering defects |
| New/material today | Kalshi current bytes do not bind the kill row and acquisition is incomplete; HybridRegimeMR HYP-001 C1/C2 identity breach; CFTC three-symbol failure-radius overreach; complete 18-EA execution/state map |
| Refuted/dropped | GLDFlow clock; GoldMacro clock; one low Unicorn citation outside file bounds |

## 8. Recommended repair order

1. **Evidence authority first:** semantic report/receipt/effective-input/lifecycle
   reconciliation; validation-path SHA checking; Model 0 relabel plus a prospectively
   defined Model-4 confirmed tier.
2. **Correct record classifications:** append-only correction path for Kalshi and
   CFTC; immutable clarification for MR HYP-001. Do not rerun/tune those IDs.
3. **One frozen execution kernel contract:** OrderCheck, send, `OnTradeTransaction`,
   actual-fill reconstruction, post-fill cash-risk enforcement, fail-closed scans,
   restart rehydration, and non-upsizing volume normalization.
4. **Migrate only candidate-worthy/reusable sources:** do not spend implementation
   budget repairing terminal V1/V2/H1 scaffolds unless a fresh authorized mechanism
   needs their code.
5. **Then continue expectancy search:** new hypotheses remain legal only through
   de-dup, cheap probe, fresh prereg, and the hardened evidence path.

## 9. Verification and limitations

Current read-only verification:

- `python -X utf8 -m pytest "02. AlphaFactory/tests" -q` → `131 passed`, two
  openpyxl style warnings.
- `python -X utf8 "04. Memory/research/validate_candidate_registry.py"` →
  `CANDIDATE_REGISTRY_OK rows=262 hypotheses=86`.
- `python -X utf8 "04. Memory/validate_source_of_truth.py"` →
  `SOURCE_OF_TRUTH_OK entries=83 local=68 backup_only=10 unavailable_unresolved=5`;
  optional Google Drive `G:` backup was unavailable and not audited.
- `alpha.ps1 status` → MT5 stopped, D: portable runtime, `FILE_COMMON allowed: False`,
  18/18 canonical packages discovered.

No MT5 compile/backtest, economic rerun, source edit, registry edit, archive, Git
stage/commit/push, or live/paper action was performed. Existing worktree changes
were preserved.

Grok runner accounting:

- accepted packets: USD `6.2516848`;
- total campaign including cancelled/superseded sessions: USD `7.3416512`;
- Deep Research packet: USD `0.6162112`.

