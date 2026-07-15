# Task Packet — FVG Scalp Confluence (red-team)

- `packet_id`: `TASK_PACKET_20260715_FVG_SCALP_CONFLUENCE_REDTEAM`
- `hypothesis_id`: none (pre-registry de-dup)
- `role_assigned`: red-team
- `model`: `cursor-grok-4.5-high-fast`
- `mode`: readonly
- `created_by`: coordinator
- `created_at`: 2026-07-15 ~16:40 ICT

## Scope

- Objective: Attack Owner council brief “FVG Scalping + confluence (OB, MS, Premium/Discount, session)” as EA-build request; decide if illegal revive vs independent mechanism.
- In-scope paths: `do_not_repeat_failures.md`, `hot.md` Active Truth / Next Move, `MERGE_MEMO_20260715_HYBRID_ICT_SONIC_BUILD_REQUEST.md`, Structural V3 FVG kill readout, registry/STRATEGY_LOG if present.
- Out-of-scope: EA code, compile, prereg freeze, Model 0, shelf restore.
- Decision surface: N/A (readonly)

## Bound inputs

- Owner brief summary (council):
  - Core: 3-candle FVG; entry on retrace + rejection or 40–60% gap; ≥2–3 confluence (HTF BOS/CHoCH, OB, P/D, liq sweep, session).
  - TF: H1/H4 bias + M5 entry; London/NY only; news filter; max 3–5 setups/day.
  - Symbols: EURUSD primary (min gap 8–12 pip), GBPUSD, XAUUSD (stricter).
  - Exit: SL outside FVG + buffer; TP structure or ≥1:2; partial 50% @1:1; BE @1:1.
  - Risk: challenge 0.25%/trade, max 3/day, daily loss 2%; live 0.15%.
  - Council itself: start manual/semi-auto demo before full EA; edge = discipline + confluence filter, not pattern alone; live WR ~52–58% after cost.
- Prior PARK (same day): Hybrid ICT-Sonic `PARK` — FVG class + Dragon/Sonic DNA revive.
- Killed hyp: `HYP-H1-DISPLACE-FVG-CONT-001` — N=247 PF=1.0168 tpw=0.947; x1.5 PF=0.9447; cadence+stress fail; do-not densify FVG%.
- Shelf: empty; `ea_contract.ps1` fail-closed; archive compile invalid.
- Cost frontier: QFSI STOP (quote days << 90).

## Stop rules

- Stop if: clear revive of Structural V3 FVG-cont densify or Hybrid ICT-Sonic stack.
- Do not: authorize impl/GO; invent new PF claims; recommend densify of killed FVG%.

## Required out receipt

`verdict` (`PASS_WITH_RISK` | `KILL_RECOMMEND` | `BLOCKED`), `evidence_paths[]`, `blockers[]`, `kill_reasons_or_risks[]`, `confidence`

Also answer explicitly:
1. Is M5 FVG+confluence materially different from `HYP-H1-DISPLACE-FVG-CONT-001`?
2. Does empty shelf + doctrine block EA scaffold now?
3. Recommended Owner path: A manual / B new-mechanism probe / C override / other.
