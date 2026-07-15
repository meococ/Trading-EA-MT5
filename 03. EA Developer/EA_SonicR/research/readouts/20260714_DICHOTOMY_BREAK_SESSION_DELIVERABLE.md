# Deliverable — Dichotomy-break R&D (2026-07-14)

## Verdict

**3/3 offline KILL · 0 Model 0 · GOAL unmet.** Shelf vẫn RR2 `194548`.

## Đã làm

1. Panel 3-critic (trader/quant/systems, `cursor-grok-4.5-high-fast`) → chỉ còn 3 class khả thi: kiến trúc cost-resilience, exo gate, CorrCap book.
2. Chọn ≤3 object ngoài kill shelf → probe offline joint screen.
3. Kết quả: BE@1R phá edge; yield gate không nâng stress + cắt cadence; CorrCap vẫn fail +$12.

## Action (ưu tiên)

1. **Không** densify D1–D3 / V1–V8 / Wave / MaxKZ/RR.
2. **Next EV:** acquire surface mới (spread table broker hoặc CFTC COT lagged) rồi gate-probe trên RR2 đóng băng — không clone session/price.
3. Phase-0 compose vẫn BLOCKED; Real/QFSI chỉ hygiene.
4. Model 0 chỉ khi có `PROBE_SURVIVOR`.

## Evidence

- Merge: `20260714_DICHOTOMY_BREAK_3CRITIC_MERGE_MEMO.md`
- Probes: `20260714_DICHOTOMY_BREAK_OFFLINE_PROBES.md` SHA `2788A3B4…AED7F`
- Closeout: `20260714_DICHOTOMY_BREAK_SESSION_CLOSEOUT.md`


## Addendum COT

Đã acquire CFTC FinFut JPY (2018–2025), freeze panel, probe gate trên RR2 →
**KILL** (tpw **0.9781**, x1.5 **0.9435**).
Surface giữ trên disk. Next: spread table broker hoặc join COT kiểu size-budget mới (không retune z).
