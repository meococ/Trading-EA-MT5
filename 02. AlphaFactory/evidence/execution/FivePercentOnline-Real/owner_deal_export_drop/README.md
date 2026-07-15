# Owner drop — Real deal history / commission evidence

Drop MT5 **Account History** exports here. Agent import tool:

```text
python "02. AlphaFactory/tools/import_owner_deal_history_qfsi.py" --from-drop "<this folder>" --out-dir "02. AlphaFactory/evidence/execution/FivePercentOnline-Real/20260714_DEAL_HISTORY_IMPORT"
```

## What to export (MT5 Toolbox)

1. Login `FivePercentOnline-Real` (same Real account already verified).
2. Toolbox → **History** (Account History).
3. Right-click history → **All History** (or a range covering ≥90 calendar days of closed deals).
4. Right-click → **Report** / **Save as Report** → save as:
   - `Deals.htm` / `Deals.html` (preferred), and/or
   - `Deals.csv` if your build offers CSV.
5. Optional: broker PDF/CSV **commission schedule** → drop as `commission_schedule.*` (reference only; does not mint slippage).
6. Copy files into **this folder** (do not invent rows).

## Required Deal columns

| Field | Why |
|---|---|
| Time (open/close or deal time) | lifecycle open/close UTC |
| Symbol | must include USDJPY / EURUSD / GBPUSD / XAUUSD |
| Volume / Lots | per-lot commission normalization |
| Commission | non-zero on Real FX preferred |
| Position / Position ID | groups open+close into one lifecycle |
| Profit / Swap (nice-to-have) | audit only |

Gate: **≥30** independent closed commission lifecycles **per symbol**.

## Slippage (separate — deal export alone is not enough)

Passive quote capture **cannot mint** slippage. Need either:

- Broker execution report with independent pre-send BID/ASK reference, or
- Side-referenced fills joined to a logged pre-send quote (≤1000 ms age),

with **≥100** fills/symbol (≥30 buy + ≥30 sell). Missing ≠ 0.

## Do not drop

Tester reports, Demo history, fabricated zeros, or “commission = 0 so cost = 0” claims.
