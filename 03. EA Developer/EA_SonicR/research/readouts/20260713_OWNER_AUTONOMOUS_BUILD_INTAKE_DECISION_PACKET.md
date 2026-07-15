# Owner Autonomous Build Intake — Decision Packet

Date: 2026-07-13  
Worker: Grok 4.5 high-fast execution lane  
Status: `BLOCKED_NEEDS_OWNER / NO_EA_BUILD / NO_COMPILE / NO_BACKTEST`

## Intake

Owner requested autonomous research → plan → AlphaFactory compile/backtest.
This session audited living truth and V6/V7/Phase 0 receipts, then applied
fail-closed 1A judgment. Progress toward compile/backtest is desired; gate
waiver is not authorized.

## Verdict

`BLOCKED_NEEDS_OWNER`

One-sentence reason: V2–V7 left no legal candidate under the current data
contract, V8 remains `DRAFT / NOT SUBMITTED`, and no registry row or frozen
prereg exists — so AlphaFactory compile/Model 0 would be unauthorized ceremony.

## A. Exact blockers forbidding AlphaFactory compile/backtest

| # | Blocker | Evidence |
|---|---|---|
| 1 | No legal strategy candidate | V7 result `NO LEGAL H4/D1 CANDIDATE`; receipt `preflight/20260713_NEW_STRATEGY_DEEP_RESEARCH_RESULT_V7.json` sets `ea_code_compile_backtest=false` |
| 2 | V6 also stop | `NO_LEGAL_CANDIDATE_CONFIRMED / FRONTIER_STOP / NO_EA_BUILD` |
| 3 | V5 sole proxy killed offline | Impact-per-Pressure `KILL_AT_OFFLINE_PROBE` before registry/prereg |
| 4 | No registry row + frozen prereg for a new EA | Hard rule: meaningful backtest requires both |
| 5 | V8 data-contract packet not submitted | `20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md` footer: `DRAFT / NOT SUBMITTED`; Owner confirm required before Browser Deep Research |
| 6 | Phase 0 SilverBullet/portfolio | Artifact sufficiency `BLOCKED`; contamination forces clean future freeze review; Phase 1+ blocked |
| 7 | Same-broker cost provenance incomplete | QFSI still `STOP_DATA_FRONTIER` (MetaQuotes-Demo ≠ FivePercentOnline-Real); promotion-grade Model 0 claims remain blocked even if a research probe later appears |
| 8 | MT5 terminal currently STOPPED | `alpha.ps1 status` 2026-07-13 — CLI healthy; Strategy Tester cannot run until MT5 is up **and** a lawful contract exists |

## B. Nearest lawful path to Owner GOAL

North Star still requires PF > 1.30 after verified cost, 2–5 trades/week
(elapsed calendar weeks), cost stress, etc.

Nearest **lawful** sequence (no gate waiver):

1. Owner confirms Deep Research V8 submit on the frozen carry/public-rates
   packet (or explicitly rejects V8 and names a different exogenous surface).
2. Browser UI readback of `GPT-5.6 Sol` + `Pro` + `Nghiên cứu sâu` → submit →
   result receipt + local coordinator audit against
   `20260713_V8_EXOGENOUS_LOCAL_DEDUP_BASELINE.md`.
3. If and only if one legal candidate survives de-dup: cheap offline probe on
   hash-bound public-rate series joined with lag rules.
4. Probe survivor → registry row → frozen prereg → MQL5 under `03. EA Developer`
   → non-repaint audit → AlphaFactory compile → Model 0 → readout.
5. Parallel / later: Owner broker re-login to `FivePercentOnline-Real` for QFSI
   capture so Model 0 promotion claims are not forever stress-proxy-only.

Price-only ideation, V6/V7 renames, Phase 0 compile, and archive-path builds
remain illegal shortcuts.

## C. What this session did / did not do

### Done

- Re-read `hot.md`, `GOAL.md`, `INDEX.md`, V6/V7 result receipts, V7
  coordinator audit, Owner 1A panel merge, V8 draft + exogenous inventory +
  de-dup baseline.
- Ran `alpha.ps1 status` (tooling OK; MT5 STOPPED). Did not compile or backtest.
- Confirmed root is not a Git work tree (empty `.git` placeholder only;
  `git rev-parse` fails closed as required).
- Wrote this decision packet and updated living truth in `hot.md`.

### Explicitly not done (correct fail-closed)

- No Deep Research V8 ChatGPT submission (draft banner requires Owner confirm).
- No public-rate/COT download treated as a probe or candidate.
- No registry append, prereg freeze, EA source edit, MetaEditor compile, or
  Strategy Tester run.
- No Phase 0 clearance claim.

## D. Owner decisions that unlock build

Answer each with yes/no (or exact alternative):

1. **V8 submit?** Confirm Browser → ChatGPT Deep Research on
   `20260713_NEW_STRATEGY_DEEP_RESEARCH_DATA_CONTRACT_V8.md`
   (SHA256 `DFC7B7F7923E4437B8735EB7F971941B6EBE801057A78B7160CB01576CF8401F`,
   12009 bytes) as the next research action.
2. **Pre-acquire rates?** Optionally authorize hash-bound download of ECB/BoE/
   Treasury (and FRED if API key exists) into
   `research/preflight/v8_exogenous/` **before** V8 result — acquisition only,
   still no probe until coordinator freezes join keys after a legal candidate.
3. **QFSI broker login?** Schedule read-only login to `FivePercentOnline-Real`
   so cost provenance can advance in parallel (required for promotion-grade
   claims; not a substitute for a legal candidate).
4. **Reject V8?** If Owner rejects carry expansion, name the alternative
   external-state change; do not ask agents to invent a price-only EA.

Until (1) is yes and a post-V8 legal candidate survives local audit + probe +
prereg, the truthful status remains `NO_EA_BUILD`.

## Authority reminder

Owner 1A fail-closed: research/plan freely; build/compile/Model 0 only after
surviving offline probe + frozen prereg. Unchanged blocker / duplicate family
stops the loop until external state changes.
