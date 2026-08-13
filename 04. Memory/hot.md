# Hot Cache — Current State

Updated: 2026-08-13.

Cache. Verify bằng registry, prereg, run manifest, report.

## Current state

- Goal: `ACTIVE / UNMET` — `01. GOAL/GOAL.md`
- Active mechanism: **none**
- Scope: XAUUSD + 7 FX majors; BTC out
- Native MT5 price/tick/quote là candidate hợp lệ
- Spend: in-scope < USD 10 với quote/cap; không live
- CLS flow: parked commercial object, cần Owner mới gửi inquiry — không thay native lane

## Next action

1. Không bịa một native candidate từ 137 registry leaves đã terminal hoặc từ
   Grok SonicR v10 đã outcome-contaminated.
2. Chỉ mở một candidate khi có cơ chế XAU/FX materially distinct, causal và
   preregistrable qua de-dup/failure lookup trước outcome.
3. Nếu Owner cho phép `Cho phép gửi inquiry CLS R2`, gửi đúng inquiry đã freeze;
   reply chỉ mở source/contract gates, chưa mở economics.
4. Khi có candidate hợp lệ: contract ngắn → EA → compile → một Model-0 →
   `run-forensics` FIX / REVISION / KILL.

## 2026-08-13 SonicR v10 recovery gate

- Grok recovered 9/9 named source/result artifacts, but the exact walk-forward
  assignment bounds and per-fold OOS ledgers are still missing.
- Direct source inspection identifies the same terminal Dragon breakout/
  pullback family with outcome-conditioned symbol filters and parameters.
- Verdict: `REJECT_GROK_SONICR_V10_AS_ECONOMIC_CANDIDATE`.
- Do not compile, backtest, repair or reconstruct this object as a revival.
- Goal remains `ACTIVE / UNMET`; CLS R2 may be sent only after explicit Owner
  authority.
- Receipt:
  `04. Memory/research/20260813_GROK_SONICR_V10_ORIGINAL_EVIDENCE_RECOVERY.md`.
