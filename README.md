# Trading-EA-MT5

An AI-assisted research and engineering workspace for designing, backtesting, and validating Expert Advisors (EAs) for MetaTrader 5.

The project explores how coding agents can help turn trading ideas into auditable MQL5 implementations while preserving an evidence trail from hypothesis to test result. It is intentionally research-first: failed strategies and negative results are recorded instead of being hidden, and no strategy is presented as profitable or production-ready without out-of-sample and execution validation.

> **Project status:** active public research / pre-release. Nothing in this repository is financial advice, a performance guarantee, or an invitation to trade live capital.

## Why this project exists

Algorithmic-trading repositories often publish a finished EA without showing how it was tested, how costs were modeled, or how failed ideas were rejected. Trading-EA-MT5 takes a more transparent approach:

- convert a market hypothesis into explicit, testable rules;
- keep signal logic causal and consistent between backtest, forward test, and live-capable code;
- model spread, commission, slippage, and broker constraints;
- separate engineering correctness from economic validity;
- protect sealed out-of-sample and holdout periods;
- use AI agents for implementation, review, test analysis, and research traceability;
- retain negative results so the same weak ideas are not repeatedly rediscovered.

The long-term goal is a contributor-friendly framework for reproducible MT5 strategy research, not a collection of unverifiable trading claims.

## What is included

- **AlphaFactory** — PowerShell orchestration for repository status, compilation, MT5 backtests, report analysis, and validation.
- **MQL5 strategy packages** — EAs, indicators, test harnesses, and research packages at different stages of the validation lifecycle.
- **Research tooling** — Python utilities for cost modeling, robustness checks, Monte Carlo analysis, walk-forward analysis, and evidence generation.
- **Agent workflow** — repository-level operating rules and focused review roles for AI-assisted development.
- **Audit trail** — hypothesis contracts, test evidence, and explicit `PASS`, `PARK`, or `KILL` outcomes.

## Repository map

| Path | Purpose |
| --- | --- |
| `01. GOAL/` | Current research objective and acceptance gates |
| `02. AlphaFactory/` | Build, backtest, analysis, and validation tooling |
| `03. EA Developer/` | MQL5 EA packages and package-level research |
| `04. Memory/` | Research registry and durable decision records |
| `05. Playbook/` | Engineering and validation workflow |
| `AGENTS.md` | Operating rules for coding agents and maintainers |

Machine-local configuration, broker exports, credentials, personal trading records, and runtime agent logs are intentionally excluded from the public repository.

## Quick start

### Requirements

- Windows with MetaTrader 5 installed
- PowerShell
- Python for the analysis utilities
- A local MT5 data directory and terminal path that you are allowed to use

### Setup

1. Clone the repository.
2. Copy `02. AlphaFactory/alpha.local.ps1.example` to `02. AlphaFactory/alpha.local.ps1`.
3. Edit only the local copy with your MT5 installation and data paths. The local file is ignored by Git.
4. Inspect the current project state:

```powershell
./02. AlphaFactory/alpha.ps1 status
./02. AlphaFactory/alpha.ps1 context
```

5. Review `AGENTS.md`, `01. GOAL/GOAL.md`, and `05. Playbook/WORKFLOW.md` before running an experiment.

Useful commands:

```powershell
./02. AlphaFactory/alpha.ps1 compile "<EA>"
./02. AlphaFactory/alpha.ps1 backtest "<EA>" -Symbol <SYMBOL> -Period <TF> -HypothesisId <ID>
./02. AlphaFactory/alpha.ps1 analyze -Report "<REPORT_PATH>"
./02. AlphaFactory/alpha.ps1 validate-full -Report "<REPORT_PATH>"
```

Command behavior in the current `alpha.ps1` source takes precedence over examples in documentation.

## Research standard

A green compile is not evidence of a trading edge. A strategy should advance only when it has:

1. deterministic and reviewable implementation;
2. realistic execution costs and broker geometry;
3. sufficient sample size and stable behavior;
4. independent out-of-sample or walk-forward validation;
5. robustness under cost and parameter stress;
6. risk controls suitable for forward testing.

Live trading is outside the default scope. It requires an explicit owner decision and separate operational review.

## Privacy and data hygiene

Do not commit:

- broker account exports or account identifiers;
- API keys, passwords, tokens, or recovery codes;
- local terminal paths or machine-specific configuration;
- raw live-session logs, quote captures, or personal trade history;
- generated binaries and bulky runtime artifacts.

Use redacted or synthetic fixtures when a test needs account-shaped data. See `.gitignore` and `SECURITY.md` before publishing evidence.

## Roadmap

- reduce the public repository to a clean, documented core;
- publish a reproducible baseline workflow and small example dataset;
- add automated secret and quality checks;
- improve contributor onboarding and issue templates;
- harden the MQL5 and orchestration surfaces with security review;
- tag the first public pre-release after the repository is reproducible from a clean clone.

## Contributing

Contributions that improve reproducibility, testing, documentation, MQL5 safety, cost modeling, or research integrity are welcome. Please read `CONTRIBUTING.md` before opening a pull request.

## Security

Please do not disclose credentials, broker identifiers, or exploitable details in a public issue. Follow `SECURITY.md` for responsible reporting.

## Disclaimer

This software is provided for research and educational purposes. Trading involves substantial risk, backtests can be misleading, and past performance does not predict future results. You are responsible for independent review, compliance, broker rules, and any use of real capital.

