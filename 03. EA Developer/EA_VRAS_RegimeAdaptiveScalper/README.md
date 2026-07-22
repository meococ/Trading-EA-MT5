# EA_VRAS_RegimeAdaptiveScalper

Trạng thái: HYP-001 terminal `INVALID_ENGINEERING_RUN_NO_ECONOMIC_VERDICT`.
Source được giữ nguyên byte để audit lỗi so sánh `OrderCheck` với retcode của
`OrderSend`; run zero-trade không có PF/WR/expectancy và không được rerun.

Package EA nghiên cứu EURUSD M5 triển khai VRAS theo báo cáo gốc và phụ lục 7
lỗ hổng kỹ thuật ngày 22/07/2026.

- Canonical source: `EA_VRAS_RegimeAdaptiveScalper.mq5`
- Primary diagnostic profile: tick-volume weighted Session VWAP, London-open
  anchor, ADX hysteresis 25/19 với dwell 6 nến.
- Execution: chỉ nến đóng, entry tại quote đầu nến kế tiếp, một vị thế/symbol,
  không martingale/average-down.
- Research boundary: cost hiện là proxy chưa đạt provenance; mọi Model-0 trong
  lane này là diagnostic-only, `promotion_eligible=false`.
- `InpResearchAutoMode=false` mặc định; EA không được attach/live từ kết quả
  package này.

Nguồn thiết kế:

- `05. Playbook/Strategy/BaoCao_DeepResearch_VWAP_Regime_Adaptive_Scalper_VRAS_22Jul2026.docx`
- Google Doc technical-gap supplement ID
  `1MtvWnLrYIkEWI73egiK7ErKn8dnNcB3KbywBqY0MIS4`
