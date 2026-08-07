# Indicator-fusion campaign frontier stop — 2026-08-07

## Decision

- Workspace goal: **ACTIVE / UNMET**.
- Engineering work on the indicator ports, native MT5 visual workflow and
  bounded telemetry is valid.
- No new EA, source probe or economic run is authorized from another
  AIRD/VRC/MBB/QQE/TB recombination.
- Current verdict:
  `FRONTIER_STOP_NO_LEGAL_FREE_OR_BROKER_NATIVE_M5_M15_EVENT_CLOCK`.

This is a scoped research stop, not a claim that markets contain no edge. It
means the declared free/broker-native information boundary has no remaining
novel, point-in-time, M5/M15 event clock that both survives de-duplication and
has an honest path to the full required symbol universe.

## Evidence chain

1. Native MT5 Visual Mode supplied eight real trade-chart cases with MBB, QQE,
   TB structure and actual entry/SL/TP/exit markers. The visual explanation was
   useful, but winner traits are outcome-locked and cannot become filters.
2. RSF HYP010 was engineering-valid and economically negative: N162,
   PF0.714519, net -USD3,981.17, WR38.30%, mean -0.136032R. No session,
   direction, engine, freshness, corridor-rebind or risk/target rescue is legal.
3. JCDR HYP005 collected one complete zero-trade, outcome-blind stage dataset:
   934 rows, 100% history quality, 3.5844 raw events/week, zero trades and zero
   outcome labels. The legacy continuation funnel ended at zero after geometry;
   TB structure-event was zero on all rows; the event clock is structurally
   incompatible with the indicator roles.
4. Independent Grok de-dup review returned `C_REJECT_RECOMBINATIONS` at high
   confidence. Candidate A (TB sweep/reclaim clock) was a weak delta across
   ASRS/HYP-017/RSF; candidate B (fresh BOS/MSS first retest) was a duplicate of
   RSF HYP010.
5. A resumed web-backed Grok deep-research run completed with exit 0,
   `EndTurn` and JSON-schema PASS. It returned `NO_LEGAL_CANDIDATE` at high
   confidence after checking primary academic/official sources and local
   failure radii.

## Bound artifacts

| Artifact | SHA256 |
|---|---|
| `03. EA Developer/EA_RegimeStructureFusion/research/liquidity_pool/HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-ECON-010_RESULT.md` | `5A7DB85A0C6CF3585D53EA2D7BB158CBA89CC1A5709919AEB3C1D2B799A7CFE3` |
| `03. EA Developer/EA_JumpClusterDecayReversal/research/HYP-JCDR-EURUSD-M5-005_FAILURE_PACKET.md` | `7EC0DF2A05538BB645466DA63E6C6F61378B2CEF6B7472CCFA1EA4AEAA59B02F` |
| `02. AlphaFactory/runs/EA_JumpClusterDecayReversal/20260807_180115/analysis/jcdr005_stage_alignment_analysis.json` | `F8AB90F5731ADD14203ABECD8021E7B72F7DBA4299042C6BD61AF84023D4A0D9` |
| `.context/structural_successor_dedup_review/run2/summary.json` | `BCAA5D1ADC44E763AED36802120A575E186B1C8CE7607B534B797CED23E4CB46` |
| `.context/structural_successor_dedup_review/run2/grok-response.json` | `23A4A091896B5955DBBABBBDC193436BB42A429890300DED5B8351B9D7E17FD2` |
| `.context/fresh_causal_mechanism_deep_research/run2_resume/summary.json` | `D07F2F60F8F7A6D3FEC06757CE220FE69029229D76F2BD5B7793D29F32C75894` |
| `.context/fresh_causal_mechanism_deep_research/run2_resume/grok-response.json` | `EDA47E1365994AF15DDA638D28319CEDB51DE4973D3F8001A8E03EEFA96CFEF7` |

The `.context` files are immutable runner evidence for this campaign. This
readout is the durable routing pointer; Grok opinions do not grant execution
authority by themselves.

## Independent review conclusion adopted by Lead Quant

- Do not implement TB sweep/reclaim + indicator context as a new EA.
- Do not implement fresh TB BOS/MSS + first retest + live corridor as a new EA.
- Do not reopen JCDR, RSF HYP010, ASRS, HYP-017, Unicorn, PO3 or generic
  compression/indicator-consensus families through renamed inputs.
- QQE primary and secondary RSI are one evidence family on the tested contract;
  they must not be double-counted.
- Pair/session/timezone adaptation remains forbidden until a new causal object
  passes outcome-blind source gates and enters purged training folds.

## Why the remaining mechanisms are blocked

Primary-source verification confirms that the most defensible remaining
information sets are not currently a legal research input:

- [CME DataMine](https://www.cmegroup.com/datamine.html) offers EBS spot FX,
  market-by-order and other historical datasets through an order, account and
  data-license workflow. No Owner-authorized hash-bound pilot, cost ceiling or
  live connectivity contract exists here.
- [CLS market data](https://www.cls-group.com/products/data/) provides dense
  executed-FX data products, but the workspace has no licensed continuous
  point-in-time history/live feed contract.
- [ICE LBMA Gold Price](https://developer.ice.com/fixed-income-data-services/catalog/lbma-gold-price)
  is a twice-daily benchmark surface, not a free full-universe M5 event clock.
- [New York Fed SOFR](https://www.newyorkfed.org/markets/reference-rates/sofr)
  is official and point-in-time, but daily frequency cannot be densified into
  an honest 2–5-trades/week M5 clock.

## Exact unblock contract

Research may resume only after the Owner explicitly unlocks a materially new
point-in-time information set and sets:

1. vendor/product and license terms;
2. maximum one-time and recurring data budget;
3. immutable historical sample window plus acquisition timestamp/hash;
4. live publication/transport latency and MT5 integration path;
5. instrument-family mapping covering all nine required symbols with no silent
   skips;
6. a zero-trade source-semantics pilot before a full purchase;
7. a frozen full-universe cadence/coverage/quality contract before outcomes.

Only a source pilot passing those gates can authorize a fresh hypothesis ID.
Economics, optimization, validation, holdout, paper and live trading remain
closed.
