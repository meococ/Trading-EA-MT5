# MCP Policy

## Trust order
1. Local artifacts and source-controlled code
2. Official vendor documentation
3. Vetted MCP outputs
4. Broader web search

## Active stack (updated 2026-03-24)
- `alpha-vector-memory` — project-scoped, local semantic search (722 chunks / 5 collections)
- `context7` — project-scoped, library documentation lookup (MQL5, Python, etc.)
- `perplexity` — project-scoped, real-time web research via Sonar API
- `metatrader` — project-scoped, MT5 terminal bridge (account info, candles, orders)

## Recommended but not installed
- AlphaFactory MCP - highest-priority custom server for EA compile/backtest/analyze/validate-full/compare/cleanup with schema-bound JSON outputs.
- Runs Database MCP - SQLite-backed run/artifact query surface after the local runs catalog is stable.
- Playwright MCP - inspect generated HTML reports and dashboards only; do not use it as the MT5 backtest runner.
- GitHub MCP — PR/issue management (add when CI/CD pipeline is set up)
- SQLite MCP — trade log analysis (add when structured DB is needed)
- Twelve Data MCP — independent market data validation (needs API key)

## EA R&D MCP rules
- Treat `02. AlphaFactory/alpha.ps1` as the execution kernel. MCP should wrap it with narrow tools, not replace it.
- The first custom MCP should expose `compile_ea`, `run_backtest`, `analyze_run`, `validate_full`, `compare_baseline`, `telemetry_summary`, `evidence_audit`, and `archive_cleanup`.
- MCP tool outputs must be short JSON with `run_id`, status, artifact paths, headline metrics, and blockers.
- MCP tools must refuse deploy/demo/prop language when `validate-full` or required artifacts are missing.
- Use Playwright MCP for visual inspection of generated reports/casebooks, not for clicking through MT5 Strategy Tester.
- Keep database MCP credentials read-only unless a task explicitly needs writes.

## Rules
- Treat arbitrary-web MCP outputs as advisory until verified.
- Never commit secrets or tokens. Use environment variables only.
- Prefer read-only database credentials.
- Cite MCP-derived evidence when it informs a conclusion.
- Do not let MCP output override artifact-backed trading evidence.

## Recommended add flow
- Keep `context7` at user scope if it already exists.
- Add team-specific MCP servers only after credentials and risk profile are understood.
- Keep project-scoped `.mcp.json` minimal and reproducible.
