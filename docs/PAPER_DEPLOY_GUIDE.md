# Paper Deploy Guide — 4-EA Portfolio
## Updated: 2026-03-29 (Session 15, 177 tests, S313 Cobra upgrade)

## Portfolio Summary
| # | EA | Symbol | TF | Chart | Magic | Risk | Trades/yr | PF | WFA | Status |
|---|-----|--------|-----|-------|-------|------|-----------|-----|-----|--------|
| 1 | **EA_Cobra v2.5.1** | XAUUSD | M15 | Separate | 202604 | 0.5% | 28 | 1.90 | 4/5 | ⭐ Fund-grade |
| 2 | **EA_SilverBullet v2** | USDJPY | M15 | Separate | 20260325 | 0.5% | 101 | 1.28 | 4/5 | Deploy |
| 3 | **EA_Spark v1.4** | USDJPY | M15 | Separate* | 20260320 | 0.5% | 71 | 1.26 | 4/5 | Deploy |
| 4 | **EA_Spark v1.4** | GBPUSD | M15 | Separate | 20260321 | 0.5% | 30 | 1.35 | 5/5 | Deploy |
| 5 | **EA_InsideBar v1.0** | USDJPY | **H1** | Separate | 20260326 | 0.5% | 17 | 1.53 | 3/5 | Satellite |
| **TOTAL** | — | 3 assets | — | 5 charts | — | 2.5% max | **~255/yr** | **~1.42** | — | — |

*SB + Spark on USDJPY M15 CAN share same chart but with different magic numbers. Safer on separate charts.

## Setup Steps (MetaQuotes Demo)

### 1. Open 5 Charts
- XAUUSD M15 → Attach EA_Cobra v2.5.1
- USDJPY M15 → Attach EA_SilverBullet v2
- USDJPY M15 → Attach EA_Spark v1.4 (separate chart window)
- GBPUSD M15 → Attach EA_Spark v1.4
- USDJPY H1 → Attach EA_InsideBar v1.0

### 2. Load Presets
Each EA should have its OPTIMAL preset loaded:
- **Cobra**: `02. EA Developer/EA_Cobra/v2/PRESET_OPTIMAL.txt`
- **SilverBullet**: `02. EA Developer/EA_SilverBullet/Presets/SB2_USDJPY_baseline.set`
- **Spark USDJPY**: Default inputs with: `InpRiskPct=0.5, InpSkipMon=true, InpSkipThu=true, InpSkipFri=true`
- **Spark GBPUSD**: Default inputs with: `InpRiskPct=0.5, InpSkipMon=true, InpSkipTue=true, InpSkipFri=true`
- **InsideBar**: Default inputs with: `InpRiskPct=0.5, InpMagic=20260326`

### 3. Verify Settings
- [ ] Each EA has UNIQUE magic number
- [ ] Risk per trade = 0.5% for all
- [ ] Kill Switch = OFF (production mode)
- [ ] Datalog = ON (for monitoring)
- [ ] All EAs show correct symbol/TF in Properties tab

### 4. Risk Management Limits
| Parameter | Value | Why |
|-----------|-------|-----|
| Risk/trade | 0.5% | MC P95 portfolio DD < 16% |
| Max daily DD | 3% per EA | Prevent cascade |
| Max total DD | 10% portfolio | E8 compliance (8% target) |
| Max concurrent | 3 per EA | Prevent overexposure |
| Max spread | Symbol-specific | Auto-managed by EAs |

### 5. Monitoring Checklist (Daily)
- [ ] Check net equity vs starting equity
- [ ] Verify trade count matches expected frequency (~1/day average)
- [ ] Check that no EA has hit daily DD guard
- [ ] Review any new trades for proper SL/TP placement
- [ ] Compare actual spread vs backtest spread assumptions

### 6. Weekly Review
- [ ] Calculate rolling PF (should be near validated PF ±0.3)
- [ ] Check DD vs backtest DD
- [ ] Verify day-of-week distribution matches expectations
- [ ] If any EA DD > MC P95, investigate (stop if DD > 2× P95)

## Correlation Matrix
| Pair | Overlap | Risk |
|------|---------|------|
| Cobra ↔ SB/Spark/IB | ZERO (different asset) | Very Low |
| SB ↔ Spark (USDJPY) | ~20% same-day | Medium |
| SB ↔ IB (USDJPY) | Low (M15 vs H1) | Low |
| Spark USDJPY ↔ GBPUSD | Low (different pairs) | Low |

## Prop Firm Deployment (MT5-Compatible — Researched 2026-03-29)

### Prop Firm Risk Sizing
Prop max DD=10%. Scale risk: `prop_risk = 0.5% × (9.0% / MC_P95_DD)`.
- Cobra: 0.20% (MC P95 23.7% → ~9.5%)
- SB: 0.30% (MC P95 16% → ~9.6%)
- Spark USDJPY: 0.40% (MC P95 12.1% → ~9.7%)
- Spark GBPUSD/IB: 0.50% (MC P95 ≤7.1%)

Gold leverage: The5ers 1:25 (best), FTMO Swing 1:9 (too low). At 0.20% risk, lot sizes tiny → leverage NOT a concern.

### Top 3 Recommended Firms
| Rank | Firm | Daily DD | Max DD | Gold Leverage | EA Policy | Split |
|------|------|----------|--------|---------------|-----------|-------|
| 🥇 | **The5ers HS** | 5% | 10% | **1:25** | ✅ No consistency rule | 80-100% |
| 🥈 | **FTMO Standard** | 5% | 10% | 1:100 | ✅ <2000 req/day | 80-90% |
| 🥉 | **FundedNext** | 5% | 10% | ~1:25 | ✅ Must stay consistent | 80-95% |

### Recommended Deployment Plan
| Account | EA | Firm | Size | Expected Time to Pass |
|---------|-----|------|------|----------------------|
| A | EA_Cobra v2.5.1 (XAUUSD) | The5ers | $50K | 20-40 days (28t/yr) |
| B | EA_SilverBullet v2 (USDJPY) | FundedNext | $100K | 10-20 days (101t/yr) |
| C | EA_Spark v1.4 (USDJPY+GBPUSD) | FTMO | $100K | 15-25 days (101t/yr) |
| D | EA_InsideBar (USDJPY H1) | The5ers | $25K | 30-60 days (17t/yr) |

### Why The5ers for EA Trading
- **NO consistency rule** = EA can have big win days without penalty
- Operating since 2016 (longest track record)
- No minimum trading days
- Allows overnight + weekend holding
- Scales to $4M with 100% profit split

### Key Restrictions (ALL Firms)
- ❌ No grid/martingale
- ❌ No arbitrage
- ❌ No HFT (>50% trades < 1 min)
- ✅ Our EAs all compliant (shortest hold = ~4hrs SB M15)

## Emergency Procedures
- **If any EA DD > 2× MC P95 DD**: Disable that EA, investigate
- **If portfolio DD > 20%**: Disable ALL EAs, review regime
- **If spread spikes > 3× normal**: Market stress, disable until normal
- **If trades cluster (>5 same day)**: Check for signal contamination
