# MT5-only >=98% frontier readout — 2026-07-26

Status: `FRONTIER_STOP_NO_LEGAL_MT5_ONLY_CANDIDATE`

This is a research closeout, not a hypothesis preregistration, source-build
authorization, Model-0 receipt, optimization result, promotion decision or live
authority.

## Owner boundary accepted prospectively

For the next otherwise-legal direct MT5 Model-0 run, tester history quality
`>=98%` is sufficient. This exception is prospective only. It does not validate
older runs retroactively and does not waive exact date coverage, clock parity,
closed-bar/non-repaint, report/lifecycle reconciliation, real bid/ask cost,
commission, slippage, swap, matched controls, sealed OOS, WFO/Monte Carlo or
delivery gates. It also does not turn broker quotes/ticks into dealer inventory,
signed order flow or primary-CLOB data.

## Search and independent review

- ChatGPT `GPT-5.6 Sol` + `Pro` + `Nghiên cứu sâu` was asked for at most three
  materially new EURUSD MT5-only mechanisms after an explicit local-family
  de-dup. Its exact final answer was `NO LEGAL MT5-ONLY CANDIDATE`.
- Parent primary-source review admitted one adversarial object for legality
  review only: `FX_FIX_INVENTORY_WAVE_PRE_ECB`, a short EURUSD position from
  Frankfurt 08:00 to the 14:15 ECB reference rate. The allowed MT5 surface was
  FivePercent server 09:00 to 15:15, with a prospective +60-minute placebo.
- No-outcome clock feasibility passed on the local EURUSD data: 1,039 paired
  2019-2022 days, positive tick volume on all sampled entry/exit rows, and
  2,078/2,078 server-to-Frankfurt clock mappings correct. Offline spread is not
  cost truth; zero-spread shares were about 28.1% at entry and 29.5% at exit.
- One bounded, read-only Grok forensic packet independently returned
  `NO_LEGAL_MT5_ONLY_CANDIDATE`. Runner gates passed: exit 0, structured schema
  valid, useful non-empty response, `EndTurn`, no subagents and web disabled.

## Why the candidate is not legal

1. The causal story is dealer pre-hedging/inventory around an institutional
   fixing. Closed MT5 OHLC, bid/ask ticks, timestamps, spread and tick volume do
   not observe inventory, dealer pre-hedging or fixing order flow. The mechanism
   therefore cannot be falsified on the proposed information set.
2. The actual MT5 decision surface is only an unconditional EURUSD local-time
   short window. This falls inside the terminal failure radius of
   `HYP-BR-SESSDRIFT-EURUSD-H1-001`, whose frozen 2015-2022 probe recorded
   N=4,146, gross PF=1.036, PF@1x cost=0.889 and short-partition PF@1x=0.911.
   Its SHA-bound readout expressly forbids window/local-time shifts, direction
   flips and conditioning rescue.
3. The primary benchmark-fix research reports a strong adverse execution prior:
   full quoted bid/ask costs turn most windows negative and average-trader
   exploitability is not established. The local offline spread field is too
   incomplete to overturn that prior.
4. A +60-minute placebo can test time anchoring only after the object is legal;
   it cannot create a new hypothesis identity for a closed session-clock family.

## Decision

Do not create a registry row, preregistration, EA source, compile, MT5 Model-0,
optimization or chart campaign for `FX_FIX_INVENTORY_WAVE_PRE_ECB`. Doing so
would be a relabeled post-hoc window rescue, not a new strategy. The GFI loop
stops before code/backtest because the candidate failed the de-dup and
observability gates; the `>=98%` tester-quality relaxation is not the blocker.

The frontier may reopen only with a materially different point-in-time
information set that actually measures the claimed causal state, under a fresh
Owner-scoped ID, cheap outcome-blind probe and frozen prereg. Paid acquisition
remains parked until the Owner supplies an explicit spending ceiling. A future
forward-only corpus must have immutable first-seen timestamps and an independent
cost contract; another broker-quote calendar window is not an unlock.

## Closeout verification

- Candidate registry: `CANDIDATE_REGISTRY_OK rows=258 hypotheses=84`.
- All six evidence paths referenced below exist and their SHA256 values were
  recomputed after the readout was written.
- Canonical source-of-truth validator is `PARTIAL`, not green: its only ten
  reported errors are pre-existing `backup-only` files under the currently
  unmounted Google Drive root `G:\Drive của tôi\META TRADING\Advisors`.
  No local authoritative/evidence/archive path error was reported. This session
  did not reclassify those backups from a transient missing drive and did not
  claim full source-of-truth validation.

## Evidence binding

- Input memo:
  `04. Memory/research/20260726_MT5_ONLY_98_GATE_FRONTIER_INPUT.md`
  — SHA256 `1BF7E4740A9C344B71D1C8F52351055AACDC1E4BB4F9EFAEB979B7B83FE4431F`.
- Grok request:
  `.context/fxfix_mt5_frontier_review_20260726/grok-request.json`
  — SHA256 `E50AE7D05A2200970C97887789F26D2B4249CA0F80CFD0853B46B67F548ACD27`.
- Grok response:
  `.context/fxfix_mt5_frontier_review_20260726/grok-response.json`
  — SHA256 `16CC14B988FB99D675A5798325846F1F4ED990ABBF1DF648B9FBFCB9DCB0F394`.
- Runner summary:
  `.context/fxfix_mt5_frontier_review_20260726/summary.json`
  — SHA256 `C304A2C973561E66A76AEB9F6C86F443FD9A6FB0ABF30896D8DC790E5E5E7E1F`.
- Prior terminal object:
  `03. EA Developer/EA_EURSessionDrift/research/HYP-BR-SESSDRIFT-EURUSD-H1-001_READOUT.md`
  — SHA256 `C6D7343E957EE9CA93E1D2E815CF16336391A85263D331D3C62E0E3B42F01EDA`.
