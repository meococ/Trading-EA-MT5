# EA_FiveIndicatorAtomicV2

Campaign package for **Owner-authorized** five-indicator atomic rebuild
(`FIV2-20260808-ATOMIC`).

## Status (three-layer)

| Layer | Status |
|---|---|
| engineering-valid | PARTIAL — Stage-0 EA compiles 0 errors (24448-byte EX5); indicator forks SHA-bound; contracts frozen; MT5 census not yet run |
| economic-valid | NOT STARTED — zero PnL authority |
| promotion-ready | NO |

### Compile bind (engineering only)

| Artifact | SHA256 |
|---|---|
| `EA_FiveIndicatorAtomicV2.mq5` | `4B7931CDA9C4DCB8004C69A7897AD378D8622D08C0E54AC57B246B6B06817E08` |
| `EA_FiveIndicatorAtomicV2.ex5` | `3B22BEF7178DA650C1BD7485FAFCCE047F559B8BDA7E7ED88B544192F280E932` |

## What this is

Intelligent **role-based** combination of five closed-bar MT5 indicators into
three **atomic engines** tested separately:

1. **ENGINE_R** — range / mean reversion  
2. **ENGINE_T** — trend pullback  
3. **ENGINE_B** — squeeze breakout  

Not a five-indicator majority vote. Not a reuse of
`EA_RegimeStructureFusion` / `EA_AIRQMB_RegimeFusion` economics.

## Authority

- Base commit: `00f8a2f5661a2c089fe16b5084fc02e7694b8008`
- Branch/worktree: `codex/five-indicator-rebuild-v2`
- Manifest: `04. Memory/research/campaigns/FIV2_20260808/CAMPAIGN_MANIFEST.json`
- Prior failures bind as **radius only**:
  - `04. Memory/research/20260807_INDICATOR_FUSION_FRONTIER_STOP.md`
  - `04. Memory/research/20260808_FIVE_INDICATOR_NATIVE_CENSUS_CLOSEOUT.md`

## First Stage-0 ID

`HYP-FIV2-R-EURUSD-M5-STAGE0-001` — outcome-blind zero-trade census for
ENGINE_R on EURUSD M5 DESIGN window only.

## Layout

```
EA_FiveIndicatorAtomicV2/
  README.md
  ALPHAFACTORY_EA_CONTRACT.json   # after EA exists
  indicators/                     # hash-bound forks after re-audit
  research/
    contracts/                    # semantic contracts per indicator
    engines/                      # R/T/B logic matrices
    stage0/                       # prereg + packets
    evidence/
  tests/
```

## Hard rules

- MT5-only. No TradingView charts as parity/evidence.
- Closed-bar only. Fail-closed warm-up / EMPTY_VALUE / history insufficiency.
- No economics until Stage-0 passes and atomic prereg is frozen.
- Old PF/N from RSF/AIRQMB/census are **not** evidence for this package.
