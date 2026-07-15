# Readout — HYP-H1-LOWVOL-DONCHIAN-MR-001 Model 0

Date: 2026-07-14  
Authoritative exclusive-lane run: `20260714_221055` (twin `20260714_220749` identical)  
Prior rebuild-lane kill also on disk: `20260714_191727` (N=13, PF 0.40, tpw~0.05) — same hyp family, also kill.  
EA: `EA_H1LowVolDonchianMR` (on-disk magic **880960**)  
Verdict: **`KILLED_AT_MODEL_0`** (confirmed under exclusive tester reopen)

## Team critic merge

- **Trader:** Low-vol Donchian fade is a real regime idea; one fill in five years is not a book.
- **Quant:** N=1 ≪ 80; tpw≈0.004 ≪ [1.0,6.0]; PF 999.99 meaningless. Kill. Tester-`current` only. Tick count ~6.5M vs ~124M on parked H1 ATR-mom same window — history thinner; even so, identical twin rerun → not a one-off race alone.
- **MQL5:** Closed-bar Donchian `shifts 1..N` OK; Alpha `includes_sha256` closeout flake after report ready — artifacts kept.

## Binding

| Item | Value |
|---|---|
| Symbol/TF | USDJPY H1 |
| Window | 2021.01.01–2025.12.31 Model 0 Deposit 10000 |
| Overrides | `` (defaults) |
| Cost | tester `current` / Demo — not Real QFSI |

## Metrics (`enhanced_summary.json`)

| Metric | Value |
|---|---|
| Trades | **1** |
| PF | 999.99 (single winner) |
| Net | +$45.36 |
| DD | 0% |
| tpw elapsed | **~0.004** |

Report SHA256: `D7FA0D5F016EA39B65590653A428A61772B8E26B0197B0CB1B5478DAFC699A0A`  
Receipt SHA256: `FF99F5037AD6AE78C3C8CCFDBF65E7A8F07B045812AD58B57B6E8D5A9B4914DD`.

## Gates

| Screen | Result |
|---|---|
| N ≥ 80 | **FAIL** |
| tpw ∈ [1.0, 6.0] | **FAIL** |
| PF ≥ 1.00 | n/a (sample invalid) |

**Kill.** Do **not** mine ATRRatioMax / DonchianLen / hour / day. Family budget `h1_lowvol_donchian_mr` **1/1 used**.

## Lane note

Owner reported Real out; agent cleared `terminal64`/`metatester64` for exclusive tester. `common.ini` had briefly still shown `FivePercentOnline-Real` before clear.
