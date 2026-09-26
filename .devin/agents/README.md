# Advisory Board — EA campaign subagent team

Placeholders: `<REPO_ROOT>` = thư mục gốc repo trên máy đang chạy (local hoặc Devin cloud VM); `<OWNER_GUI_TERMINAL>` = MT5 GUI của Owner — chỉ trên máy Owner.

Persistent specialist seats consulted at mandatory gates inside `/loop`.
Advisors are **read-only** (`subagent_explore` profile): they review, measure,
and return verdicts — the lead agent executes all writes and governed runs.

## Invocation contract (every seat)

Prompt must include: repo root `<REPO_ROOT>`, the gate name,
specific artifact paths to review, and this ban list:

- NEVER `mcp__mt5__trade_*` / `trade_send_*` — observe only.
- NEVER `mt5.initialize(path=...)` — attach bare only if a terminal runs.
- Compile/backtest ONLY via `02. AlphaFactory\alpha.ps1` (advisors: read logs,
  do not launch).
- No worktrees, no commits, no writes outside own scratch files.

Output contract: `VERDICT: PASS | FAIL | WARN` + numbered defects with
file:line / data evidence + one-line "what would change my verdict".

## Seats

| Seat | File | Objective |
|---|---|---|
| Alpha Researcher | `alpha-researcher.md` | Find causal mechanisms; rank candidate classes |
| Quant Methodologist | `quant-methodologist.md` | Probe design rigor; stats validity |
| Data-Integrity Auditor | `data-integrity-auditor.md` | Kill measurement-plane artifacts BEFORE they become hypotheses |
| Microstructure & Execution | `microstructure-execution.md` | Fill/cost realism; SL vs noise band; model-0 divergence |
| Adversarial Auditor | `adversarial-auditor.md` | Red-team reasoning, lookahead, selection bias, contract violations |
| GOAL Gatekeeper | `goal-gatekeeper.md` | Contract fidelity; honest cadence; binding-constraint analysis |
| MQL5 Architect | `mql5-architect.md` | Substrate reuse; audit conformance; no dead code |

## Mandatory gates (wired in loop SKILL.md)

- **GATE A — post-probe, pre-prereg**: Data-Integrity Auditor +
  Quant Methodologist. No prereg without both PASS.
- **GATE B — pre-freeze prereg**: Adversarial Auditor + GOAL Gatekeeper.
- **GATE C — post-run, pre-verdict**: Microstructure & Execution +
  Adversarial Auditor on any probe-vs-governed divergence.
- **GATE D — direction selection**: Alpha Researcher ranks classes;
  Gatekeeper states binding constraint.
- **GATE E — build review (optional)**: MQL5 Architect on new substrate use.

Gates run in parallel where independent. FAIL from any seat blocks the
phase until resolved or explicitly overruled by Owner.
