# Advisory Board — EA campaign subagent team

Placeholders: `<REPO_ROOT>` = thư mục gốc repo trên máy đang chạy (local hoặc Devin cloud VM); `<OWNER_GUI_TERMINAL>` = MT5 GUI của Owner — chỉ trên máy Owner.

Persistent specialist seats consulted at mandatory gates inside `/loop`.
Advisors are **read-only**: they review, measure, and return verdicts —
the lead agent executes all writes and governed runs.

## Invocation contract (every seat)

Prompt must include: repo root `<REPO_ROOT>`, the gate name,
specific artifact paths to review, and this ban list:

- NEVER `mcp__mt5__trade_*` / `trade_send_*` — observe only.
- NEVER `mt5.initialize(path=...)` — attach bare only if a terminal runs.
- Compile/backtest ONLY via `02. AlphaFactory\alpha.ps1` (advisors: read logs,
  do not launch).
- No worktrees, no commits, no pushes, no writes outside own scratch files.
- No MT5 process launches (no `terminal64.exe`, no metatester).
- NEVER print secret values to chat/logs/files — including demo credentials.

Output contract: `VERDICT: PASS | FAIL | WARN` + numbered defects with
file:line / data evidence + one-line "what would change my verdict".

## How to invoke

- **Local (Devin CLI on Owner machine):** `run_subagent` with profile
  `subagent_explore`, card text + gate context + ban list pasted in.
- **Devin cloud VM:** seat = ONE child Devin session via
  `devin_session_create`. Compose the prompt with
  `02. AlphaFactory\tools\vm\vm_seat_prompt.ps1` (seat card + gate +
  artifact paths + ban list + output contract). The child runs on its own
  machine: it must not commit/push or launch MT5; the Builder verifies with
  `git log`/`git status` on the reviewed branch after the verdict arrives.

## Roles — cloud era

- **Owner (anh Mèo Cọc):** direction, GOAL/contract, signs L3+/demo/live,
  merges PRs, money/accounts.
- **Lead (Linh/Claude):** task packets, counter-review, acceptance, keeps the
  rules, reports to Owner; does not code.
- **Builder (main Devin cloud session):** runs `/loop` on the VM, owns the
  processes it opens.
- **Reviewer (advisory seat = read-only child session, clean context):**
  gates A–E.
- **Chart review:** Gemini, routed via Lead.
- **Plane local (Owner machine):** MT5 GUI observed via MCP only + venue
  (FivePercent) data; Devin CLI local only does Owner-machine-only work
  (e.g. git sync).

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
