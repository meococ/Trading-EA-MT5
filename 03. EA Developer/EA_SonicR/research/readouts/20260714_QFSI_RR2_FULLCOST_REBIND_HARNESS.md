# RR2 full-cost rebind harness

Updated: 2026-07-15T00:41:20.703260Z  
Gate: **`STOP_DATA_FRONTIER`**  
Execute: `False` · GOAL claim: `False` · confirmed: false

## Remaining frontier

```json
{
  "quote_days_need": {
    "USDJPY": 88,
    "EURUSD": 88,
    "GBPUSD": 88,
    "XAUUSD": 88
  },
  "commission_need": {
    "USDJPY": 30,
    "EURUSD": 28,
    "GBPUSD": 30,
    "XAUUSD": 30
  },
  "slippage_need": {
    "USDJPY": 100,
    "EURUSD": 100,
    "GBPUSD": 100,
    "XAUUSD": 100
  },
  "calendar_eta_quote_days_only": "~88 elapsed calendar days if continuous Real accumulate (commission/slip still Owner deal-export)"
}
```

## Blockers

- EURUSD_quote_days=2<<90
- EURUSD_commission_unique=2<<30
- EURUSD_slippage_fills=0<<100 (MISSING≠0)
- GBPUSD_quote_days=2<<90
- GBPUSD_commission_unique=0<<30
- GBPUSD_slippage_fills=0<<100 (MISSING≠0)
- XAUUSD_quote_days=2<<90
- XAUUSD_commission_unique=0<<30
- XAUUSD_slippage_fills=0<<100 (MISSING≠0)
- USDJPY_quote_days=2<<90 (book primary)
- USDJPY_commission_unique=0<<30 (book primary)
- USDJPY_slippage_fills=0<<100 (book primary; MISSING≠0)

## When GO

```powershell
python "02. AlphaFactory/tools/qfsi_rr2_fullcost_rebind_harness.py" --execute
```

Frozen books: RR2 `194548` / ctrl `194221` / fresh `231750` + Spark `193358`.  
**No signal retune.** Do not kill Real.
