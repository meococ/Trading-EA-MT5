# Mechanical MT5 / git hooks

Grok hooks in `.grok/hooks/` deny `mt5__trade_*`, bare `terminal64.exe`, Owner-GUI `path=`, blanket `git add`, and unsolicited worktrees. They ask on MCP `tester_run_backtest` and on `git commit` / `git push`.

On session start they write `04. Memory/mcp_session_status.json` (gitignored cache, not authority). Read it before claiming account/MCP state. `mcp_trade_allowed` is MCP-only — confirm with `get_trading_account_info`.

Do not treat an MCP backtest as a decision number. Compile evidence is a fresh `0 errors, 0 warnings` log plus a new EX5 via `alpha.ps1 compile`.
