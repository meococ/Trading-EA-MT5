# Contributing to Trading-EA-MT5

Thank you for helping improve reproducible, safety-conscious MT5 research.

## Before you start

- Open an issue or discussion for a substantial strategy, architecture, or workflow change.
- Keep each pull request focused on one coherent problem.
- Read `01. GOAL/GOAL.md` and `05. Playbook/WORKFLOW.md`.
- Do not present a compile result or a single backtest as evidence of profitability.

## Development workflow

1. Create a feature branch.
2. State the hypothesis or engineering problem clearly.
3. Add or update focused tests.
4. Compile through AlphaFactory and retain a fresh `0 errors, 0 warnings` result.
5. Run the smallest valid backtest or validation step for the change.
6. Document data range, costs, assumptions, and limitations.
7. Review the diff for secrets, account data, generated artifacts, and machine-local paths.

## Pull request checklist

- [ ] The change has a clear purpose and bounded scope.
- [ ] Signal and execution logic are causal and do not look ahead.
- [ ] Tests or reproducible verification steps are included.
- [ ] Costs and broker constraints are modeled where relevant.
- [ ] Claims distinguish engineering validity from economic validity.
- [ ] No holdout data was used to tune the implementation.
- [ ] No credentials, account identifiers, personal trade history, or local paths are included.
- [ ] Documentation is updated only where it helps a contributor reproduce the work.

## Data and privacy

Never commit live broker exports, credentials, API keys, recovery codes, account numbers, terminal profiles, or personal trading history. Use a small redacted or synthetic fixture when a test needs realistic structure.

If sensitive data is discovered in Git history, stop sharing it, rotate any affected credential, and report the exposure privately to the Owner directly; do not open a public issue. Removing a file in a new commit does not remove it from earlier Git history.

## Research integrity

Negative results are useful. Do not remove losing periods, select only favorable symbols, or tune on sealed validation data to improve a result. A failed hypothesis should remain traceable with a concise verdict and enough evidence to avoid repeating the same experiment.

## Scope of support

Maintainers may close proposals that encourage unsafe live deployment, unverifiable performance claims, retrospective overfitting, or the publication of private broker data.
