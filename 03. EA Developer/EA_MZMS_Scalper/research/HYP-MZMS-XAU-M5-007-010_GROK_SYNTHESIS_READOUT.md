# HYP-MZMS-XAU-M5-007..010 — Grok synthesis closeout (Owner readout)

- **Campaign:** HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400
- **Validity:** INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99 (history quality 98% < 99%)
- **Verdict bound:** PARK_INVALID / DIAGNOSTIC ONLY
- **promotion_blocked:** true | **post_hoc_rescue_blocked:** true
- **Authority:** no promotion, no economic authority, no rerun/rescue of these IDs
- **Evidence:** 400 PNG charts rendered; all 400 had image_opened=true in 40 schema-valid Grok chunks
- **Sample mix:** 007=100 executed; 008=80 executed + 20 diagnostic near-miss; 009=100 executed; 010=2 executed + 98 diagnostic near-miss
- **Source synthesis:** 
esearch/evidence/HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400/GROK_SYNTHESIS_RESULT.json (extracted from .context/mzms-xau-007-010-vision-synthesis/grok-response.json)

---

# Báo cáo tổng hợp chẩn đoán — Campaign HYP-MZMS-XAU-M5-007..010

**Ranh giới hiệu lực (OBSERVED):** Cả bốn run Model-0 có **history quality 98% < 99%** → `INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99` → **DIAGNOSTIC ONLY**. `promotion_blocked=true`, `post_hoc_rescue_blocked=true`. Không promote, không live, không kill kinh tế có thẩm quyền, **không** rescue/retune/re-run 007–010.

**Phạm vi bằng chứng:** 400 chart đã validate (100/hyp), lifecycle reconcile exact từng arm, metrics đóng băng trong `campaign_metrics.json`. Offline indicator trên chart = visualization only (không parity CopyBuffer).

---

## 1. Kết luận có nhãn bằng chứng

| Hypothesis | Mechanism | Shape kinh tế (diagnostic) | Cadence (diagnostic) | Anatomy thất bại chính |
|---|---|---|---|---|
| **007** | Donchian fresh-impulse + ATR expand + ADX mid rising | n=3409, PF≈0.81, E≈−$0.61, net≈−$2065 | **OVER** ≈7.64 tpw (>5) | Adverse late/counter-structure + TIME_EXIT scrape; Mode2 hiếm khi pure |
| **008** | EMA20/100 pullback + pivot reclaim | n=80, PF≈1.07, E≈+$0.31, net≈+$25 | **UNDER** ≈0.18 tpw | Late/exhausted reclaim + **cadence bottleneck** full offline signal |
| **009** | BB/ATR compression → envelope break | n=1041, PF≈0.93, E≈−$0.24, net≈−$253 | **IN-BAND** ≈2.33 tpw | Archetype mismatch (fade/late) + TIME_EXIT partial R |
| **010** | RSI/wick/ADX-roll exhaustion MR | n=2, PF≈0.88, E≈−$0.56, net≈−$1.12 | **SEVERE UNDER** ≈0.0045 tpw | Incomplete multi-gate stack; fade vào impulse còn expand |

- **OBSERVED:** HQ 98%, counts n/PF/WR/net, exact reconciliation, coverage 100 images/hyp.
- **STRONG_INFERENCE:** adverse-selection-heavy 007/009; 008 conditional clean winners + starvation; 010 gate non-completion.
- **HYPOTHESIS (chưa test):** bốn prereg candidate mới bên dưới — **không** phải patch 007–010.

---

## 2. Verdict từng hypothesis (shape only)

### HYP-007 — yếu nhất về shape kinh tế quy mô lớn
- **Kinh tế (diagnostic):** PF < 1, expectancy âm, thua lỗ lớn, n rất lớn.
- **Cadence:** quá dày so với band 2–5.
- **Anatomy:** `bad_entry_or_adverse_selection≈47/100`; TIME_EXIT partial R lặp lại; exemplar sạch (007-E005-P246, 007-E012-P696) **không** modal.
- **Case hỗ trợ:** 007-E002-P36, 007-E007-P370, 007-E011-P634, 007-E018-P1080, 007-E047-P3066, 007-E001-P10.

### HYP-008 — mạnh nhất *tương đối* (vẫn không promote)
- **Kinh tế (diagnostic):** PF hơi >1, net dương nhỏ; **n=80** + HQ invalid → không có quyền promote.
- **Cadence:** đói lệnh; near-miss full signal bị chặn (008-N011-B453496, 008-N012-B498457).
- **Anatomy:** winner khi stack chín + pullback giữa chân (008-E023-P46, 008-E029-P58); loser late/post-climax (008-E015-P30, 008-E042-P84).

### HYP-009 — cadence đạt band nhưng edge diagnostic âm
- **Kinh tế:** PF≈0.93, expectancy âm.
- **Cadence:** duy nhất nằm trong 2–5 tpw (diagnostic).
- **Anatomy:** breakout giả / counter-HTF / late-extension trộn với squeeze sạch thỉnh thoảng (009-E029-P584, 009-E038-P748, 009-E093-P2008).

### HYP-010 — suy sụp mật độ / stack gate
- **Kinh tế:** n=2 → không suy luận expectancy.
- **Cadence:** gần như zero-fire.
- **Anatomy:** `good_rejected_near_miss≈70`; incomplete gates + knife-catch risk (010-E001-P2).

---

## 3. So sánh chéo

- **Strongest (diagnostic shape):** **008** — PF/net dương + winner anatomy có điều kiện.
- **Weakest (diagnostic economics at scale):** **007** — n lớn, PF/E xấu, over-cadence, fidelity non-modal.
- **010** yếu nhất về *khả dụng mật độ*; **009** “trung tính xấu” (cadence ổn, expectancy diagnostic âm).
- **Không** có arm nào vượt PF≥1.35 + HQ≥99% + cost verified → **không ranking promote**.

---

## 4. Tối đa 4 prereg candidate *mới* (không rescue 007–010)

1. **Compression-base first-expansion Donchian initiation** — phase nén→mở rộng đầu tiên + DI concordance (tách chase). Evidence: 007 clean vs late cases trên.
2. **Mature EMA-stack pullback-reclaim + post-vertical-displacement exclusion** — stack-age/maturity + cấm reclaim sau climax. Evidence: 008 winners vs late losers + near-miss cadence.
3. **HTF-coaligned true squeeze→envelope expansion only** — nén thật + envelope break + HTF đồng hướng. Evidence: 009 mismatch vs clean aligned.
4. **Impulse-completion ADX-roll + structural reclaim exhaustion MR** — hoàn tất impulse rồi mới fade; cấm RSI extreme mid-waterfall. Evidence: 010 near-miss/executed.

Mỗi candidate cần **hypothesis_id mới**, probe offline rẻ, freeze pre-outcome — **cấm** gắn lại ID 007–010.

---

## 5. Khuyến nghị STOP

**`recommend_stop = true`** cho vòng 007–010:

1. HQ 98% khóa toàn bộ authority kinh tế/promote.
2. Forensics 400 case đã đủ để mô tả failure anatomy — không cần re-run cùng ID.
3. Post-hoc rescue bị cấm cứng bởi prereg + doctrine.
4. Việc tiếp theo hợp lệ: **sửa history quality / data engineering**, rồi (nếu Owner muốn) **ID mới** + offline probe — không Model-0 “vá” 007–010.

---

## 6. Hạn chế

- History quality 98% → diagnostic only.
- Cost provenance unverified; news guard off → promotion blocked dù HQ đạt.
- Offline indicators ≠ MT5 parity.
- Casebook stratified / full-pop / near-miss — không phải population effect-size đầy đủ cho mọi nhãn mechanism.
- 008 n=80 và 010 n=2: khoảng tin cậy hẹp.
- TIME_EXIT partial R là quan sát geometry; **không** cấp quyền kéo timeout/BE hậu nghiệm.

