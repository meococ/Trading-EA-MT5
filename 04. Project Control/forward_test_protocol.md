# Forward Test Protocol — EA_SonicR

Updated: 2026-06-03

## Overview

Mọi EA đã pass 5/5 validation gates phải trải qua forward test trước khi live.
Forward test là bước xác nhận rằng backtest không phải artifact của mô phỏng.

## Pre-Forward Test Checklist

- [ ] Sleeve đã pass 5/5 validation gates (WFA, MC, Robustness, Cost, Equity)
- [ ] Model 0 Every Tick confirmed
- [ ] Non-repaint audit passed
- [ ] Source hash recorded
- [ ] Preset file (.set) exported và lưu trong `deploy/demo/`
- [ ] Demo account ready (same broker, same leverage)
- [ ] VPS setup (24/7 connectivity)
- [ ] Monitoring alerts configured (Telegram/Email)

## Forward Test Phases

### Phase 1: Demo Forward (2-4 tuần)

| Parameter | Requirement |
|-----------|-------------|
| Account | Demo, same broker as planned live |
| Lot size | Fixed 0.01 hoặc risk-based |
| Duration | Minimum 2 tuần, target 4 tuần |
| Trade target | ≥50 trades (ưu tiên hơn calendar time) |

**Daily log:**
```
Date | Trades | Win | Loss | PnL | Spread | Slippage | News Skip | Notes
```

**Pass criteria:**
- PF within backtest 95% confidence interval
- No execution errors or SL rejection
- News filter behaving correctly (fail-closed when calendar unavailable)
- OrderCalc lot sizing producing valid lots

**Fail criteria (immediate stop):**
- PF < 0.8 after ≥30 trades
- Max DD exceeds backtest max DD × 1.5
- Systematic execution failures
- SL/TP fill quality consistently worse than expected

### Phase 2: Micro-Live (4-8 tuần)

| Parameter | Requirement |
|-----------|-------------|
| Account | Real money, minimum deposit |
| Lot size | 0.01 (minimum possible) |
| Risk per trade | ≤0.5% equity |
| Duration | 4-8 tuần |

**Additional monitoring:**
- Actual slippage vs. demo slippage
- Swap costs per overnight position
- Broker execution speed
- Weekend gap behavior

### Phase 3: Scale Up (ongoing)

- Tăng risk% từ từ: 0.5% → 1.0% → target risk%
- Mỗi bước tăng: chạy ≥2 tuần trước khi tăng tiếp
- Monthly review required

## Kill Switches

| Trigger | Action |
|---------|--------|
| Daily loss > 3% equity | Disable EA for rest of day |
| Weekly loss > 5% equity | Disable EA, review |
| Total DD > 10% equity | Disable ALL EAs, full review |
| 3 consecutive losing weeks | Review, consider pause |
| PF < 1.0 after 100+ trades | Park/kill the sleeve |

## Reporting

After each forward test phase, create a readout:
```
research/readouts/YYYYMMDD_SONICR_FORWARD_TEST_PHASE_X_READOUT.md
```

Include:
- Trade-by-trade comparison with backtest expectations
- Execution quality metrics
- Slippage/spread analysis
- News filter behavior log
- Verdict: PASS / FAIL / EXTEND
