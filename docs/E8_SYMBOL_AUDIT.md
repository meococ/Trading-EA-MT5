# E8 Markets Terminal — Symbol Availability Audit
Last verified: 2026-04-09

## Evidence sources (authoritative order)

1. **MT5 tester live test** — `logs/20260409.log` — definitive: tester rejects symbols not on server
2. **`bases/E8Markets-Server/ticks/`** — 26 symbols with tick data = confirmed deployed/tradeable
3. **`bases/E8Markets-Server/history/`** — 22 history dirs — NOT sufficient alone (see trap below)
4. **MT5 log sync message** — "38 symbols, 0 spreads" — server advertises 38 total; 12 not yet locally cached

## Critical trap: history-only ≠ tester-accessible

Five no-suffix symbols appear in E8 history dirs but have NO tick data and fail in the tester:

| Symbol | History | Ticks | Tester | Note |
|--------|---------|-------|--------|------|
| XAUUSD | ✅ .hcc | ❌ | ❌ BLOCKED | Stale data download artefact |
| USDJPY | ✅ .hcc | ❌ | ❌ BLOCKED | Confirmed: log "symbol USDJPY not exist" |
| EURUSD | ✅ .hcc | ❌ | likely ❌ | No ticks = likely blocked |
| USDCHF | ✅ .hcc | ❌ | likely ❌ | No ticks = likely blocked |
| AUDJPY | ✅ .hcc | ❌ | likely ❌ | No ticks = likely blocked |

**Rule: presence in `ticks/` = deployable. History-only = NOT deployable.**

## Confirmed E8 symbol catalogue (26 via ticks, all + suffix)

### Forex (14)
AUDCAD+, AUDCHF+, AUDJPY+, AUDNZD+, AUDUSD+,
CADCHF+, CADJPY+, CHFJPY+,
EURAUD+, EURCAD+, EURJPY+, EURUSD+,
GBPJPY+, GBPUSD+,
USDCHF+, USDJPY+

### Metals (2)
XAUUSD+, XAGUSD+

### Energy (2)
BRENT+, WTI+

### Indices (6)
ASX+, DAX+, DOW+, NIKKEI+, NSDQ+, SP+

**12 additional symbols exist on server (38 total) but are not locally cached yet.**
Likely candidates: EURGBP+, NZDUSD+, USDCAD+, GBPCAD+, EURCHF+, NZDJPY+ and similar.

## Naming convention

- **Universal rule**: E8 uses `<BASE><QUOTE>+` suffix for ALL symbols
- No exceptions found among the 26 confirmed ticks symbols
- Any EA hardcoded to no-suffix symbol (XAUUSD, USDJPY, GBPUSD…) will fail with:
  `shutdown with -1000012358 (tester symbol does not exist)`

## Portfolio deployment decision

| EA | Validated on | E8 symbol | Deployable? | Caveat |
|----|-------------|-----------|-------------|--------|
| EA_Cobra | XAUUSD+ | XAUUSD+ | ✅ CONFIRMED | Validated natively on E8 symbol |
| EA_ITSM | USDJPY | USDJPY+ | ⚠️ NEEDS RETEST | + suffix = different spread/execution; PF may degrade like Cobra did (−9.5%) |
| EA_LondonNY | USDJPY | USDJPY+ | ⚠️ NEEDS RETEST | Same caveat as ITSM |
| EA_Spark | GBPUSD | GBPUSD+ | ⚠️ NEEDS RETEST | Baseline PF 1.35 before spread difference |
| EA_InsideBar | USDJPY (H1) | USDJPY+ | ⚠️ NEEDS RETEST | Borderline PF 1.648; degradation could kill edge |
| EA_Gotobi | USDJPY | USDJPY+ | ❌ DISQUALIFIED on merit | Equity curve fail regardless of symbol |
| EA_SilverBullet | USDJPY | USDJPY+ | ❌ DISQUALIFIED on merit | PF < 1.0 on XAUUSD; USDJPY edge not validated on E8 |

## How to pre-check symbols in future

**Fastest pre-check before any new backtest:**
```
ls "C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases\E8Markets-Server\ticks\"
```
If the symbol dir is present → safe to test. If absent → will fail.

**Secondary check (bar history available):**
```
ls "...\bases\E8Markets-Server\history\"
```
History-only (not in ticks) = data may exist but tester will reject.

## Note on 38 vs 26 discrepancy
The MT5 log states "38 symbols" at login. Only 26 have local tick data.
The remaining 12 exist on the server but have never been subscribed in this terminal's
market watch. To discover them: open MT5 → View → Symbols → search E8 catalogue.
They are almost certainly additional forex crosses with + suffix.
