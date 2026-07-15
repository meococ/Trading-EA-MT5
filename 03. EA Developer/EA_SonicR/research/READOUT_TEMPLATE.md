# Sonic R Readout Template

Use this after a probe, backtest, or validation run.

## Identity

- Hypothesis ID:
- Registry state before:
- Registry state after:
- Date:
- Author/session:

## Source Identity

- Canonical source path:
- Source hash:
- Compiled artifact path:
- Compiled artifact timestamp/hash:
- Copied tester path:
- Input hash:
- Variant tag:
- Git status snapshot:

## Runs

| Role | Run ID | Symbol/TF | Window | Model | Telemetry tier | Report path |
|---|---|---|---|---|---|---|
| Control | | | | | | |
| Challenger | | | | | | |

## Outcome Matrix

Never aggregate train and holdout. Use one row per split and per challenger or
locked control; add control rows rather than collapsing them into one baseline.

| Split | Role/control | Trades | Elapsed days | Elapsed weeks (`days / 7`) | Trades/week | Net | PF | Cost PF x1 | Cost PF x1.5 | Cost PF x2 | Net R x1.5 | Mean net R/trade x1 | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | Challenger | | | | | | | | | | | | |
| Train | Control / S555 | | | | | | | | | | | | |
| Train | Control / S618 | | | | | | | | | | | | |
| Train | Control / S670 | | | | | | | | | | | | |
| Holdout | Challenger | | | | | | | | | | | | |
| Holdout | Control / S555 | | | | | | | | | | | | |
| Holdout | Control / S618 | | | | | | | | | | | | |
| Holdout | Control / S670 | | | | | | | | | | | | |

Legacy/reference-only trades/year (not a gate):

| Split | Role/control | Trades/year |
|---|---|---:|
| | | |

## Control Superiority Gates

| Split | Control | Challenger minus control cost PF x1 | Challenger minus control mean net R/trade x1 | PF margin pass | Expectancy margin pass |
|---|---|---:|---:|---|---|
| Train | S555 | | | | |
| Train | S618 | | | | |
| Train | S670 | | | | |
| Holdout | S555 | | | | |
| Holdout | S618 | | | | |
| Holdout | S670 | | | | |

## Stability And Concentration

| Split | Positive months x1.5 | Positive half-years x1.5 | Positive years x1.5 | Max pair/lane share x1.5 | Min required pair/lane share x1.5 | Result |
|---|---:|---:|---:|---:|---:|---|
| Train | | | | | | |
| Holdout | | | | | | |

## Cost And Outcome-Access Evidence

- Analyzer path/hash:
- Cost-source manifest path/hash:
- Outcome artifact path/hash:

No-censor accounting is separate for every split and role/control. An eligible
set with any missing row fails that split; do not aggregate away a failing set.

| Split | Role/control | Frozen episodes before quote/cost join | Complete after join | Missing | Outcome rows | No-censor pass |
|---|---|---:|---:|---:|---:|---|
| Train | Challenger | | | | | |
| Train | S555 | | | | | |
| Train | S618 | | | | | |
| Train | S670 | | | | | |
| Holdout | Challenger | | | | | |
| Holdout | S555 | | | | | |
| Holdout | S618 | | | | | |
| Holdout | S670 | | | | | |

| Symbol | Quote/tick source hash | Eligible-path coverage | Missing eligible episodes | Commission source/hash | Commission lifecycles or contract | Slippage source/hash | Buy/sell fill counts | P90 buy/sell/round-turn | Verdict |
|---|---|---:|---:|---|---|---|---|---|---|
| EURUSD | | | | | | | | | |
| GBPUSD | | | | | | | | | |
| USDJPY / XAUUSD | | | | | | | | | |

## Validation Artifacts

- `validate-full` status/path/hash:
- Cost stress status/path/hash:
- WFA status/path/hash:
- PBO/CSCV status/path/hash:
- Reality Check/SPA status/path/hash:
- Monte Carlo status/path/hash:
- Robustness suite status/path/hash:
- Equity audit status/path/hash:
- Execution/TCA status/path/hash:
- Non-repaint audit status/path/hash:
- Sidecar completeness:
- Header/schema changes:
- Casebook/snapshots path/hash:
- Candidate-registry validator result:

For a `confirmed` or `portfolio-sleeve` registry row, each validation reference
must be a `registry_gate_attestation.v1` JSON with exact `PASS`, hypothesis/run
identity, and a hash-bound producer artifact. Each split uses a
`registry_cost_attestation.v1` wrapper with `VERIFIED` cost evidence and a
`registry_split_outcome.v1` JSON whose metrics, controls, and zero-missing
no-censor counts exactly match the registry. A hash-pinned arbitrary text file
is not promotion evidence.

## Trade/State Anatomy

- Lane attribution:
- Direction attribution:
- Session/hour/weekday attribution:
- Month/year/half-year attribution:
- Market phase attribution:
- Top wins/losses:
- High-MFE misses:
- High-MAE false positives:
- Negative controls:

## Verdict

- Verdict: continue / park / kill / confirm / portfolio-candidate
- Reason:
- What was learned:
- What must not be inferred:
- Next action:

## Closure Checklist

- Registry appended:
- Source registry updated if authoritative:
- `hot.md` / `current_state.md` updated if needed:
- Run-local manifest exists:
- Common Files telemetry archived or confirmed clean:
- Stale tester processes reviewed:
