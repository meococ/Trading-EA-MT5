---
name: alpha-correlation-exposure
description: Evaluate multi-symbol exposure & correlation risk using EA trade logs (overlap, same-direction clustering, daily PnL correlation). Use before scaling lot size or enabling many symbols.
status: PARTIAL — chưa có automation script, workflow manual
---

## Status
- **Script automation**: CHƯA CÓ (`correlation_exposure.py` chưa viết)
- **Workflow**: Manual — dùng Python/pandas inline hoặc trade log analysis
- **Khi nào cần**: Khi chạy multi-symbol hoặc scale lot size

## Dữ liệu cần có
- Trade logs theo symbol (AlphaFactory tự copy):
  - `02. AlphaFactory\\runs\\<EA>\\<RUN_ID>\\analysis\\logs\\<SYMBOL>_Trades_*.csv`

## Lệnh hỗ trợ (liệt kê trade logs)
- `powershell -NoProfile -Command "Get-ChildItem '02. AlphaFactory\\runs\\<EA>\\<RUN_ID>\\analysis\\logs\\*_Trades_*.csv' | Select-Object FullName"`

## KPIs nên đo

### 1. Max concurrent trades
- Đỉnh số lệnh mở đồng thời theo thời gian
- > 3 concurrent trên cùng basket (vd EURUSD+GBPUSD) → rủi ro cluster

### 2. Cluster risk
- Nhiều lệnh cùng direction trong cùng 1-2 giờ (đặc biệt London/NY open)
- Correlation direction > 70% → giảm exposure

### 3. Daily PnL correlation
- Pearson/Spearman giữa daily PnL của các symbols
- > 0.7: HIGH correlation → DD sẽ phình khi cả 2 symbols sụt cùng lúc

## Quy tắc quyết định
- Daily PnL correlation > 0.7 → giảm rủi ro:
  - Giới hạn tổng lệnh mở đồng thời
  - Cap theo basket tương quan (EURUSD/GBPUSD)
  - Giảm risk/trade khi nhiều symbols cùng bias
- Nếu chỉ chạy 1 symbol (XAUUSD) → skill này KHÔNG cần thiết

## Manual workflow (khi chưa có script)
```python
import pandas as pd
# Load trade logs
trades_sym1 = pd.read_csv("XAUUSD_Trades_*.csv")
trades_sym2 = pd.read_csv("EURUSD_Trades_*.csv")
# Group by day, sum PnL
daily1 = trades_sym1.groupby("Date")["Profit"].sum()
daily2 = trades_sym2.groupby("Date")["Profit"].sum()
# Correlation
corr = daily1.corr(daily2)
print(f"Daily PnL correlation: {corr:.3f}")
```

## TODO
- Viết `02. AlphaFactory\\analysis\\correlation_exposure.py` khi cần multi-symbol automation
- Output mong đợi: `correlation_exposure.json` với matrix correlation + concurrent trades chart
