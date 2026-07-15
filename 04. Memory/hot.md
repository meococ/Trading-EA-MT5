# Hot Cache

Updated: 2026-07-16 | Project Control tách → `04. Memory/` + `05. Guidance/` (lean); doctrine cũ archived; GOAL unmet

Sự thật SỐNG ở block **▶ NEXT SESSION** ngay dưới. Bảng **Ledger** là lịch sử thí nghiệm nén 1-dòng/entry (đầy đủ 210 entry). Chi tiết config (indicator/EA param/run_id/path/SHA) nằm ở `00. Old File/hot_details/hot_ledger_details.json` (theo `#idx`); bản hot.md cũ nguyên si ở `00. Old File/hot_archive_20260715_full.md`.

## ▶ NEXT SESSION (đọc đầu tiên — live truth)

- **GOAL:** UNMET — "Mục Tiêu Tự Do": book FX PF>1.30 sau cost thật, cadence 2–5 trade/tuần, stress x1.5≥1.25 / x2≥1.00.
- **Active lanes (`03. EA Developer/`):** `EA_FVGConfluence` (Path-C build, **not** promotion-ready) · `EA_HybridICT_Sonic` (**KILL@Model0**, 0 trades — await Owner: park vs cơ chế mới).
- **HIS SIGATR:** killed — PF `0.98`, N=`76`, net `−$210`, DD ~2.2%. Cadence fixed nhưng **edge chết**. KHÔNG densify Europe/hour.
- **Best shelf:** RR2 `194548` (offline SURVIVOR PF `2.53` / x1.5 `1.81`) — **không** deployable, cần native tick-path Model 0. ⚠️ `EA_SilverBullet` source `.mq5` **mất trên đĩa** (chỉ còn `.ex5` binary; RR2 194548 evidence ở `02. AlphaFactory/runs/`).
- **Cost frontier:** `STOP_DATA_FRONTIER` — quote_days 2/90, commission/slip GAP. QFSI accumulate khi Real an toàn; KHÔNG invent cost freeze.
- **Housekeeping 2026-07-15/16:** docs↔disk sync (`4e2dace` pushed); 80 pkg → EA_Archive; GOAL đổi tên; hot.md nén (file này); `04. Project Control/` tách → **`04. Memory/`** (state) + **`05. Guidance/`** (4 file lõi); doctrine cũ → `00. Old File/project_control_archive_20260716/`.
- **Next move (await Owner):** park Hybrid family **hoặc** authorize cơ chế độc lập mới (hyp id mới, KHÔNG densify). Song song: FVGConfluence lane / QFSI cost. No live / no promote.

## Landmines (do-not-repeat — full: `do_not_repeat_failures.md` + archive §Next Move 1-11)

- KHÔNG densify param của bất kỳ KILL nào: session/hour/RR; FRED displace/ToT; XS factor-z; LNY coil; MFE arm/stall/giveback; Asia pctl/lookback.
- KHÔNG post-hoc rescue hypothesis vừa fail; phát hiện hậu nghiệm → `idea`/hyp mới.
- KHÔNG invent cost freeze; cost field = 0 hoặc thiếu ≠ cost thực = 0.
- Exit-path family trên RR2 (BE@1R + MFE stall-cut) **exhausted** — không revive.
- XAU S1: 2 hard-veto + 2 offline probe đã KILL — chỉ fresh prereg mới (Deposit=100000 matched control), không threshold-mine ATR/Dragon/H1-sweep cũ.
- Compile/backtest từ `00. Old File/` = evidence **không hợp lệ**.

## Ledger (nén — mới nhất trên cùng; `#idx` → hot_ledger_details.json)

| # | Ngày | Strategy/EA | Kịch bản | Kết quả | Metrics chính |
|---|---|---|---|---|---|
| 0 | 2026-07-15 | Workspace/EA shelf (gener… | Audited workspace disk vs docs, found 82 EA packages instead of the documented empty shel… | Owner-authorized cleanup… |  |
| 1 | 2026-07-15 | EA_HybridICT_Sonic | Tested SL = signal ± 1.0×ATR to restore trade fills vs prior empty/DIAG runs; fills retur… | KILLED_AT_MODEL_0 | N=76 PF=0.98 net=-$210 DD=~2.2% tpw=0.22 |
| 2 | 2026-07-15 | EA_HybridICT_Sonic | Prior open hypothesis for SL-SigATR, superseded by the Model0 kill result above. | SUPERSEDED by Model 0 kil… |  |
| 3 | 2026-07-15 | EA_HybridICT_Sonic | Diagnostic B run disabled the Dragon SL floor to test plumbing; got 3 toy trades confirmi… | DIAG_PASS_PLUMBING | N=3 PF=4.85 (toy) DD=~0.2% |
| 4 | 2026-07-15 | EA_HybridICT_Sonic | Earlier note that Model0 B was ready/blocked, superseded by the DIAG B DONE result. | SUPERSEDED by Model 0 don… |  |
| 5 | 2026-07-15 | EA_HybridICT_Sonic | Owner authorized Option B: disable the antagonistic Dragon±40 SL floor and add OnDeinit g… | Owner chose B; authorized |  |
| 6 | 2026-07-15 | EA_HybridICT_Sonic | Ran an offline Python sequential gate-count on EURUSD M15 (2022-07-11→2026-07-15, ~100k b… | Owner A complete | other=PVSRA survivors 1372; SL OK 0; N8_sl_fail_dragon40=13… |
| 7 | 2026-07-15 | EA_HybridICT_Sonic | Owner chose Option A: run offline Python sequential pass-counts for Hybrid ICT-Sonic mech… | decision to run gate coun… |  |
| 8 | 2026-07-15 | EA_HybridICT_Sonic | Red-team council diagnosed why Hybrid ICT-Sonic produces zero trades, ranking a silent SL… | council PROBE |  |
| 9 | 2026-07-15 | EA_HybridICT_Sonic | Owner-directed Path-C Model 0 backtest on EURUSD M15 2020-2026 produced zero trades; PF/D… | KILL_AT_MODEL0_EMPTY | HQ=100% bars=162845 ticks=102936747 trades=0 |
| 10 | 2026-07-15 ~16:55 ICT | EA_HybridICT_Sonic | Owner explicitly overrode prior PARK history in the Hybrid lane and directed the team to… | override — build authoriz… |  |
| 11 | 2026-07-15 ~16:50 ICT | EA_FVGConfluence | Owner explicitly overrode prior PARK history for FVG Scalp+Confluence and directed the te… | override — build authoriz… |  |
| 12 | 2026-07-15 ~16:45 ICT | EA_FVGConfluence | Roster red-team recommended kill and research found no legal candidate for the FVG Scalp+… | PARK (superseded by Owner… |  |
| 13 | 2026-07-15 ~16:40 ICT | EA_HybridICT_Sonic | Roster red-team recommended killing the Hybrid ICT-Sonic build as a revival of a dead con… | PARK (superseded by Owner… |  |
| 14 | 2026-07-15 | Process/doctrine | Owner amended session closeout doctrine, merging AGENTS §6-§7 into one standing closeout… | Owner amendment |  |
| 15 | 2026-07-15 | Process/doctrine | Prior split session-closeout rule superseded by the merged chốt phiên rule above. | superseded by chốt phiên… |  |
| 16 | 2026-07-15 | Process/doctrine | AGENTS.md was slimmed to standing rules only, removing dated Owner section headers and co… | standing rules only |  |
| 17 | 2026-07-15 | Process/doctrine | Owner approved a canonical multi-agent roster with role specs and inserted a Failure Tria… | Owner-approved |  |
| 18 | 2026-07-15 | Workspace/EA shelf (gener… | Owner corrected a prior cleanup that left pointer stubs; agent moved README/SYNC/tests an… | correction of prior stub… |  |
| 19 | 2026-07-15 | Workspace/EA shelf (gener… | Earlier cleanup misread 'outdated' as needing refresh/stub instead of removal; corrected… | Owner-authorized (SUPERSE… |  |
| 20 | 2026-07-15 | Workspace/EA shelf (gener… | Archived 119 shelf/failed/duplicate EA packages to a single Old File archive home, keepin… | Owner-authorized |  |
| 21 | 2026-07-15 ~07:50 ICT | Process/infra | Owner requested a GitHub repo for the workspace, reversing the prior no-Git policy; creat… | Owner-authorized |  |
| 22 | 2026-07-15 ~03:00 ICT | QFSI / RR2 194548 | Watched a planned 4h QFSI no-live capture (PID 62392) that exited early after ~35 minutes… | REAL_ON__QFSI_006_EARLY_E… | other=USDJPY q1286 / EURUSD q1028 / GBPUSD q1510 / XAUUSD q… |
| 23 | 2026-07-15 ~01:04 ICT | RR2 194548 / EA_SilverBul… | Tested MFE-envelope ATR-trail exit variants offline as a tick-unavailable diagnostic; ARM… | EXO_FRED_DISPLACE_SPAM_PA… | PF=2.5323 / 2.2173 / 1.55 PF_x1_5=1.8099 / 1.5918 / 1.1151 |
| 24 | 2026-07-15 ~01:55 ICT | RR2 194548 / cost-tick ca… | Owner-authorized rebuild tested scale-out, timebox-scalp-lock, and vol-regime R-mult exit… | EXO_FRED_DISPLACE_SPAM_PA… | N=524/524/210 PF=1.0366 / 0.8081 / 1.3349 PF_x1_5=0.7296 /… |
| 25 | 2026-07-15 ~01:20 ICT | Greenfield XS/RV book | 3-critic panel proposed greenfield strategy classes outside existing session/RR2/FRED/COT… | OFFLINE_ALL_KILL / NO_MOD… | N=831/771/228 PF=1.0394/1.0412/1.0934 PF_x1_5=0.9811/0.9915… |
| 26 | 2026-07-15 ~01:05 ICT | London-NY / EUR-GBP overl… | Tested London-NY / EUR-GBP overlap structural objects (imbalance-fade, coil-break, lead-c… | OFFLINE_ALL_KILL / NO_MOD… | N=109/308/30 PF=0.964/1.028/0.769 |
| 27 | 2026-07-15 ~00:50 ICT | RR2 / USDJPY Asia-London… | Tested an MFE stall-cut exit on RR2 and an Asia-percentile-coil-to-London-break state fil… | EXO_FRED_DISPLACE_SPAM_PA… | N=524/276 PF=0.156/1.255 |
| 28 | 2026-07-15 ~00:35 ICT | RR2 / cost surface | Dual-track session: Track A sampled MT5 tick history for a cost surface (max 2 honest quo… | EXO_FRED_DISPLACE_SPAM_PA… | N=524/210 PF=1.443/1.328 PF_x1_5=0.990/0.981 |
| 29 | 2026-07-14 ~23:20 / n… | QFSI cost import / H4-Out… | Built an agent-executable deal-history importer to narrow the cost-surface gap using live… | PARTIAL — superseded as a… | other=raw deals 11; commission EURUSD 2/USDJPY 0/GBPUSD·XAU… |
| 30 | 2026-07-15 ~00:25 ICT | EURUSD ECB/Brent displace… | Acquired ECB balance-sheet and Brent crude series and tested displacement/time-of-trend s… | OFFLINE_ALL_KILL / NO_MOD… | N=463/456/579 PF=0.9274/0.9033/1.0303 |
| 31 | 2026-07-15 ~00:15 ICT | USDJPY/EURJPY PD (NY Fed… | Track A reconfirmed the cost-surface gap remains unresolved; Track B tested NY Fed Primar… | OFFLINE_ALL_KILL / COST_G… | N=481/412/497 PF=0.9494/1.0287/1.0571 |
| 32 | 2026-07-14 ~00:05 ICT | RR2 194548 (NYFed PD/MMF/… | Acquired NY Fed Primary Dealer signed inventory, retail MMF flows, and CME JPY forward-ba… | OFFLINE_ALL_KILL / NO_MOD… | N=284/514/193 PF=1.5726/1.3739/1.333 PF_x1_5=1.1485/1.0115/… |
| 33 | 2026-07-14 ~23:55 ICT | EURUSD/GBPUSD/XAUUSD stru… | Tested six new structural objects on EURUSD/GBPUSD/XAUUSD outside the existing USDJPY-foc… | OFFLINE_MULTISYM_ALL_KILL… | other=6 objects: London-overlap break N725 PF1.069; NY-open… |
| 34 | 2026-07-14 ~00:35 ICT | QFSI / RR2 | Set up a live QFSI accumulate watch (PID 62392, planned 4h) and armed the RR2 full-cost r… | REAL_ON__QFSI_006_LIVE__R… |  |
| 35 | 2026-07-14 ~24:20 ICT | USDCAD WTI / RR2 WALCL | Acquired WTI crude and Fed balance-sheet (WALCL) series; tested a USDCAD WTI continuation… | OFFLINE_BOTH_KILL / NO_MO… | N=635/318 PF=0.9494/1.2758 PF_x1_5=0.8906/0.9539 |
| 36 | 2026-07-14 ~23:55 ICT | QFSI / RR2 194548 / MaxKZ… | Continued live QFSI capture 005 on the Real account and repriced shelf strategies at part… | REAL_ON__QFSI_005_LIVE__P… | other=USDJPY P50 $5.2335/lot; lot-0.5 trade ~$2.6168; RR2 1… |
| 37 | 2026-07-14 ~23:45 ICT | Price sweep / thick compo… | Tested six new price-sweep and thick-compose ideas outside prior Wave6/V1-V8 densify bans… | WAVE7_EXECUTED_EMPTY / NO… | other=NZDUSD Asia-London N587 PF1.04; W1-open accept N233 P… |
| 38 | 2026-07-14 ~24:10 ICT | RR2 194548 (COT JPY lever… | Tested a COT-based position-size budget (prior-52w net-leverage percentile) on frozen RR2… | AUTH_SIZEBUDGET_KILL__SES… | N=524 PF=1.4134 PF_x1_5=1.0421 |
| 39 | 2026-07-14 ~23:55 ICT | QFSI cost table / RR2 194… | Built a partial broker cost-aggregate table from Real QFSI captures 001-005 and repriced… | QFSI_HYGIENE_PARTIAL__COS… | other=USDJPY trade-cost P50 ~$2.6168 / P90 ~$2.9251 |
| 40 | 2026-07-14 ~23:40 ICT | CHFJPY/USDJPY/NZDUSD stru… | Three new structural objects (CHFJPY displace-continuation, USDJPY expansion-bar continua… | OFFLINE_V9_ALL_KILL / NO_… | N=1730/664/0 PF=1.077/1.235/n/a |
| 41 | 2026-07-14 ~23:30 ICT | RR2 194548 / QFSI | Verified the live Real terminal and QFSI capture running, repriced shelf RR2 under frozen… | REAL_ON__QFSI_HYGIENE_ACT… | PF=1.323/1.297/1.271 (RR2 P50 reprice) |
| 42 | 2026-07-14 ~23:55 ICT | Mono/retest/dayfade + mot… | Joint screen of mono/retest/dayfade confirmation plus new mother-bar and three-day high/l… | WAVE6_EXECUTED_EMPTY / NO… | other=FX3 portfolio N2814 PF1.07; mother-bar N377 PF1.33; t… |
| 43 | 2026-07-14 ~23:50 ICT | RR2 exit / USDJPY yield g… | 3-critic panel tested a BE@1R exit path, a USDJPY yield z-gate, and an RR2+Spark correlat… | OFFLINE_DICHOTOMY_BREAK_A… | N=524/371/794 PF=0.13/1.38/1.30 |
| 44 | 2026-07-14 ~23:55 ICT | RR2 194548 (CFTC JPY leve… | Acquired public CFTC FinFut COT data 2018-2025 and tested a leveraged-money z-gate on RR2… | KILL | N=255 PF=1.2748 PF_x1_5=0.9435 |
| 45 | 2026-07-14 ~23:55 ICT | EURGBP-EURUSD lead / AUDU… | Tested net-new structural objects (EURGBP lead-EURUSD, AUDUSD overlap-fail fade) after co… | OFFLINE_V8_ALL_KILL / NO_… | N=207/1 PF=0.916/n/a |
| 46 | 2026-07-14 ~23:18-23:… | QFSI / MT5 ops | Owner authorized freely opening/closing MT5 except during a live backtest; verified the R… | auth RECORDED; first chec… |  |
| 47 | 2026-07-14 ~23:25 ICT | USDJPY JPY-cross catch-up | Tested a USDJPY quiet-lag JPY-cross catch-up thesis (dual EURJPY+GBPJPY confirm); killed… | KILLED_AT_OFFLINE_PROBE | N=138 PF=0.883 PF_x1_5=0.831 |
| 48 | 2026-07-14 ~23:20 ICT | RR2 (HYP-SB-MAXKZ2-RR2-FR… | Owner authorized killing the residual Real terminal to free the tester slot; the fresh RR… | MODEL0_RR2_LANDED__PARK_M… | N=518 PF=1.156 tpw=~1.99 net=+$4425 DD=1.58% |
| 49 | 2026-07-14 ~23:20 ICT | H1 mono / M15 broken-leve… | Tested mono contraction-break, broken-level retest, and forming-day extension fade object… | OFFLINE_V7_COIL_RETEST_DA… | N=1923/1555/505 PF=1.095/1.070/1.086 |
| 50 | 2026-07-14 ~23:25 ICT | H4 Outside/Engulf/Pin | Grok-confirmed independent Outside/Engulf/Pin-at-PD-level objects tested at Model 0 after… | DISCOVERY_WAVE3_EMPTY | PF=0.77/1.13/0.67 |
| 51 | 2026-07-14 ~23:40 ICT | IB-Overlap / GBPJPY-Lead… | Owner authorized stopping a residual Real terminal (PID 27628) to free the tester; three… | REAL_PID27628_STOPPED__WA… | other=IB-Overlap PF1.05 ~3.79/wk x1.5 0.89 FAIL; GBPJPY-Lea… |
| 52 | 2026-07-14 ~23:18 ICT | H1 impulse-halfback / EUR… | Tested impulse-halfback continuation, double H1 inside break, and D1 gap fade objects out… | OFFLINE_V6_ALL_KILL / NO_… | N=551/303/13 PF=1.213/1.018/1.08 |
| 53 | 2026-07-14 ~23:32 ICT | W1 sweep-reclaim / H4 bal… | Tested a prior-week H/L wick sweep to H1 reclaim fade and an H4 overlapping-balance break… | OFFLINE_PWHL_H4BAL_BOTH_K… | N=180/75 PF=0.85/1.67 |
| 54 | 2026-07-14 ~23:30 ICT | Orderblock/D1-inside/Lond… | Five fresh structural objects tested outside V1-V4/Wave3-5/Path-B without Phase-0 wait; a… | OFFLINE_V5_ALL_KILL / NO_… | other=Orderblock mitigation N412 PF0.985; D1-inside H4 brea… |
| 55 | 2026-07-14 ~23:12 ICT | EA_D1TrendH1PB | Owner picked option B (D1 trend, H1 pullback) over A/D; Model0 hard-killed on PF<1, confi… | KILLED_AT_MODEL_0 | N=959 PF=0.967 tpw=~3.68 net=-$4022 DD=10.3% |
| 56 | 2026-07-14 ~23:25 ICT | W1 sweep-reclaim / H4 bal… | Two new objects outside Waves 1-5/T1-T4/V2-V3 tested; both killed and evidence re-homed u… | OFFLINE_V4_BOTH_KILL / NO… | N=180/75 PF=0.85/1.67 |
| 57 | 2026-07-14 ~23:18 ICT | H1 displace+FVG / NY IB f… | Tested an H1 displacement+FVG continuation and an NY IB false-break fade; both killed off… | OFFLINE_V3_BOTH_KILL / NO… | N=247/82 PF=1.017/1.122 |
| 58 | 2026-07-14 ~23:15 ICT | Stop-run accept / LNY ran… | Tested a stop-run accept object and a LNY range-accept object; both killed. | OFFLINE_V2_BOTH_KILL / NO… | N=164/4 PF=1.11/n/a |
| 59 | 2026-07-14 ~23:05 ICT | T1 cost-arm / T2 AUDJPY-l… | First structural rebuild wave killed T1/T2/T3 offline while T4 RR2+Spark diagnostic showe… | OFFLINE_FIRST_COMPLETE /… | other=T4 RR2+Spark diagnostic PF1.38/tpw3.26 but ceremony B… |
| 60 | 2026-07-14 ~23:00 ICT | H1 ATR%ile / Asia-box Lon… | Authoritative board tested ATR-percentile break, Asia-box London break, and NY-IB drive-b… | WAVE5_EXECUTED_EMPTY | PF=1.10/0.90/1.018 N=n/a/500/983 |
| 61 | 2026-07-14 | SB+Spark portfolio runner | Tested an SB+Spark portfolio runner at Model0; research PF failed and +$12 cost stress fa… | KILLED_AT_MODEL_0 | PF=1.219 tpw=~3.23 |
| 62 | 2026-07-14 | IB / RV / GBPJPY | IB PARKed, RV killed on cadence, GBPJPY PARKed in this wave. | WAVE4_EXECUTED_EMPTY |  |
| 63 | 2026-07-14 | RR2 194548 | RR2 194548 remains the best verified shelf strategy: research-bar PF hit but fails the GO… | research HIT / GOAL +$12… | PF=1.378 N=524 tpw=~2.01 |
| 64 | 2026-07-14 (unspecifi… | Donchian MR | PIN+ThreeBar/Wave3/Donchian family closed as prior evidence with no reopen authorized. | closed as prior; no reopen |  |
| 65 | 2026-07-14 ~22:10 ICT | RR2 | Second re-run attempt blocked by a residual live Real terminal; superseded once the Owner… | MODEL0_RR2_NOT_RUN__RESID… |  |
| 66 | 2026-07-14 ~22:10 ICT | MaxKZ2 / RR2 / A1 / Spark… | Verified Real login FivePercentOnline-Real and repriced the shelf at live-tick cost; MaxK… | REAL_VERIFIED__MAXKZ2_FAI… | other=live-tick P50 ~$2.31/trade; MaxKZ2 x1/x1.5/x2 1.275/1… |
| 67 | 2026-07-14 ~22:15 ICT | MaxKZ2 (HYP-SB-MAXKZ2-DEN… | Aggregated Real capture reprice under an honest cost model showed MaxKZ2 fails GOAL cost-… | MAXKZ2_REAL_PATH_FAIL_CLO… | other=Real P50 x1/x1.5/x2 PF 1.267/1.235/1.204 FAIL |
| 68 | 2026-07-14 ~22:05 ICT | RR2 | First re-run attempt on Real login PID 6596, run_id null; superseded by attempt #2. | superseded by attempt #2… |  |
| 69 | 2026-07-14 (unspecifi… | Process/doctrine | Owner rebuked framing Real/QFSI login or 'close Real to unblock Model0' as the primary R&… | authoritative for R&D hea… |  |
| 70 | 2026-07-14 | RR2 (SilverBullet MaxKZ2… | Authoritative baseline Model0 20260714_194548 hits the research PF bar but the a priori $… | HIT research bar; PARK un… | PF=1.378 N=524 tpw=~2.01 net=+$9828 DD=~0.96% |
| 71 | 2026-07-14 ~19:54–19:… | Session VWAP / H1 BOS / A… | Tested VWAP reclaim, H1 BOS pullback, and Asian tail fade; all three killed. | CLOSED KILL | PF=0.90/1.07/0.91 tpw=n/a/6.24/n/a |
| 72 | 2026-07-14 | EA_SilverBullet (HYP-SB-M… | Tested a MaxHold A2 variant vs A1 baseline; non-destructive, parked. | PARKED | PF=1.334 N=521 tpw=1.998 net=+$7541 DD=~0.85% |
| 73 | 2026-07-14 | EA (Donchian low-vol MR) | Confirmed the Donchian low-vol mean-reversion Model0 was already killed; do not retune. | KILLED_AT_MODEL_0 | PF=0.4 N=13 |
| 74 | 2026-07-14 ~21:25 ICT | QFSI | Inspected and closed completed QFSI capture windows while a new extension kept running; i… | PARTIAL / parallel only | other=003_CONTINUATION quotes 3376/HB 3444; commission EURU… |
| 75 | 2026-07-14 | RR2 | Clarified that offline RR2 remained robust under frozen Real P50 cost, correcting a race-… | RR2 Model 0 was NOT null | PF=1.323/1.297/1.271 (x1/x1.5/x2) other=MC P95 DD ~2.37%; p… |
| 76 | 2026-07-14 ~20:55 ICT | RR2 194221 / MaxKZ2 192304 | Verified Real login, ran canonical no-live capture 002, and built a partial Real cost mod… | RR2_PARTIAL_REAL_COST_STR… | other=Real P50 base ~$2.31/trade; RR2 x1/x1.5/x2 1.323/1.29… |
| 77 | 2026-07-14 ~20:25 ICT | H4 NR7 break / D1 trend H… | Three new independent H4 Model0s tested; NR7-break was a near-miss PARK, D1-trend-PB weak… | THICK_EDGE_WAVE_EMPTY | PF=1.28/1.11/1.10 N=378/285/208 |
| 78 | 2026-07-14 ~20:12 ICT | PDH retest / H4 struct br… | Three Model0s tested (PDH retest, H4 structure break, LNY dual-window); all killed on PF/… | HARD_EMPTY_CONTINUES — su… | PF=0.83/0.91/1.42 N=279/817/69 |
| 79 | 2026-07-14 ~20:00 ICT | Session VWAP / Asian tail… | Three independent Model0s with an x1.5-aware screen all killed, confirming no survivor pa… | HARD_EMPTY_SHELF | PF=0.90/0.91/1.07 N=1357/1079/1626 |
| 80 | 2026-07-14 ~19:55 | SB/MaxKZ2/Spark/RR2/ATR-s… | The active rebuild queue (SB/MaxKZ2/Spark/RR2/ATR-stop) remained a structural friction de… | EXECUTED / CLOSED empty |  |
| 81 | 2026-07-14 ~19:46 ICT | MaxKZ2/A1/Spark/RR2 (Silv… | Cost-stress iteration confirmed all MaxKZ2/A1/Spark books are structural friction dead en… | CLOSED as primary | PF=1.378 N=524 tpw=~2.01 net=+$9828 |
| 82 | 2026-07-14 ~19:29–19:… | Asian sweep / London ORB… | Four independent Model0s run after the Owner rebuke; one killed on zero trades, one PARKe… | EXECUTED / CLOSED | PF=n/a/1.08/0.97/0.99 N=0/342/919/576 |
| 83 | 2026-07-14 ~19:42–19:… | Spark capacity / MaxKZ2 /… | Spark capacity variant parked null-densify, RR2 hit research bar but failed GOAL stress,… | CLOSED | PF=1.24 (ATR-stop, worse friction) |
| 84 | 2026-07-14 ~19:29 ICT | Process/doctrine | Owner rebuked the team in Vietnamese for treating Real/QFSI login as a blocker, mandating… | AUTHORITATIVE |  |
| 85 | 2026-07-14 ~20:55 | QFSI | Historical QFSI reprice prep packet superseded by the Real login + capture 002 + RR2/MaxK… | SUPERSEDED |  |
| 86 | 2026-07-14 evening | Process/doctrine | Owner directed the team to keep refining/testing options around the strategy to improve p… | campaign closed |  |
| 87 | 2026-07-14 ~19:50 | HYP-SB-MAXKZ2-DENSITY-002 | Multi-option structural refine campaign shipped 7+ Model0 children; primary survivor MaxK… | GOAL_NEAR_MISS | PF=1.33 N=546 tpw=~2.09 net=+$8123 DD=~0.85–0.93% |
| 88 | 2026-07-14 | SB+Spark book compose | Built an a priori matrix of SB+Spark compose variants (train/holdout, haircut, weight/ove… | concrete offline results | PF=1.320 (Spark CAPNORM×10) |
| 89 | 2026-07-14 | SilverBullet family (MaxK… | A 10-item Model0 board of SilverBullet-family variants was tested; only the RR2 friction… | queue cleared; mixed PARK… | other=RR2-friction PF1.38/524t; Density-002 PF1.33/546t (Re… |
| 90 | 2026-07-14 | Portfolio compose / ITSM/… | Prior blocked-needs-owner-QFSI freeze stopped net-new unrelated shelf spam; Owner reopene… | superseded as freeze on r… |  |
| 91 | 2026-07-14 ~03:25 | H1 ATR-regime mom / H1 sw… | After a run of Demo Model0s kept yielding kill or PF<<1.30 parks, declared Demo screens a… | policy declaration |  |
| 92 | 2026-07-14 | EA_H1ATRRegimeMom | USDJPY H1 2021-2025 ATR-regime momentum Model0 survives kill screen but GOAL unmet. | PARKED | PF=1.12 N=516 tpw=~1.98 net=+$1419 DD=~7.55% |
| 93 | 2026-07-14 | EA_H1SwingFailure | H1 pivot pierce-then-close-inside fade tested on USDJPY H1 2021-2025; cadence OK but PF k… | KILLED_AT_MODEL_0 | PF=0.97 N=798 tpw=~3.06 net=-$745 DD=~17.6% |
| 94 | 2026-07-14 | EA_M15ADRCont | Tested ADR continuation (opposite of ADRExhaust fade) on USDJPY M15 2021-2025; killed. | KILLED_AT_MODEL_0 | PF=0.887 N=146 tpw=~0.56 net=-$510.65 DD=~6.95% |
| 95 | unchanged | Portfolio Phase 0 | Phase 0 portfolio contamination review remains blocked; no compose authorized. | BLOCKED_REQUIRES_CLEAN_FU… |  |
| 96 | 2026-07-14 | SB + Spark portfolio | Pooled SilverBullet + Spark trades under a priori universe clear research PF/cadence but… | PROBE_NEAR_GOAL_CADENCE_A… | N=845 PF=1.339 tpw=~3.24 net=+$8975 |
| 97 | 2026-07-14 | EA_M15EMAStretchFade | Pure EMA20 stretch mean-reversion (≥1.5 ATR) tested on USDJPY M15; PF and cadence failed. | KILLED_AT_MODEL_0 | PF=0.84 N=1980 tpw=~7.59 net=-$6588 DD=~68.6% |
| 98 | 2026-07-14 | EA_M15FailedORBFade | Opposite of LondonORB break (pierce OR then close inside → fade) tested on USDJPY M15; ca… | KILLED_AT_MODEL_0 | PF=0.83 N=522 tpw=~2.00 net=-$2279 DD=~29.2% |
| 99 | 2026-07-14 | EA_M15NYOpenDrive | Independent NY first-hour ORB tested on USDJPY M15; survives kill but GOAL unmet. | PARKED | PF=1.08 N=292 tpw=~1.12 net=+$5108 DD=~5.89% |
| 100 | 2026-07-14 | EA_M15PDHBreak | Continuation break of D1 shift≥1 PDH/PDL tested on USDJPY M15; paper-thin edge, GOAL unme… | PARKED | PF=1.027 N=440 tpw=~1.69 net=+$289.83 DD=~11.65% |
| 101 | 2026-07-14 | EA_UsBillSlopeBasket | Owner free-MT authorization unlocked this EA (previously an offline PROBE_SURVIVOR); chal… | KILLED_AT_MODEL_0 | other=control InpMode=0 PF1.05 net$586.28 N1124 DD13.59%; c… |
| 102 | 2026-07-14 ~01:05 | USDJPY VIX risk-off z-gate | Independent CBOE VIXCLS z-gate tested on USDJPY D1; killed offline, no registry/prereg/Mo… | KILL_AT_OFFLINE_PROBE | N=202 tpw=0.97 other=PF-A 0.686 < 1.05; loses to mom contro… |
| 103 | 2026-07-14 | EA_M15LondonORB | USDJPY M15 London ORB survives kill screen but GOAL unmet on PF+cadence+Demo cost. | PARKED | PF=1.17 N=413 tpw=~1.58 net=+$1751 DD=~8.13% |
| 104 | 2026-07-14 | SB 002505 + Spark 002614… | Bound SB+Spark trade series with cost manifests marked unverified-tester-default; still b… | BLOCKED_NOT_READY_FOR_PRE… |  |
| 105 | 2026-07-14 | Process | Prior no-legal-thesis blocker memo is superseded by the London ORB Model0 park result. | superseded by London ORB… |  |
| 106 | 2026-07-14 | EA_SilverBullet | Confirmed the weekend-flat A/B test on SilverBullet was already run this campaign; A1 sho… | COMPLETE (research-proxy) | other=control 002046 PF1.33 N519 tpw~1.99; challenger A1 00… |
| 107 | 2026-07-14 | SB / Spark | A disabled-signal/random-hour matched control for the best-parked strategies is not autho… | MATCHED_CONTROL_PREREG_GA… |  |
| 108 | 2026-07-14 ~00:46 ICT | Process/doctrine | Owner reconfirmed free backtesting authority toward the GOAL.md joint target (PF>1.30 + 2… | free MetaEditor/Strategy… |  |
| 109 | 2026-07-14 | EA_M15LondonORB | Earlier London ORB Model0 run (005126) survives kill floor but fails GOAL joint PF+cadenc… | PARKED research near-miss… | PF=1.17 N=413 tpw=~1.58/week net=+$1751.13 DD=~8.13% |
| 110 | 2026-07-14 | EA_KeltnerSqueeze | Keltner squeeze seed tested on USDJPY M15; PF ok but cadence outside [1.0,6.0] range, kil… | KILLED at Model 0 | PF=1.1 N=112 tpw=~0.43/week net=+$335.81 DD=~4.55% |
| 111 | 2026-07-14 | SB | SB meets research near-GOAL PF/tpw metrics but no frozen prereg authorizes a disabled-sig… | blocked |  |
| 112 | 2026-07-14 | Spark + ITSM portfolio | Frozen exact universe pooled compose of Spark+ITSM passes cadence but fails pooled PF; no… | FAIL_POOLED_PF_BELOW_1_30… | N=1177 tpw=~4.51/wk PF=1.175 |
| 113 | 2026-07-14 | InsideBar/HourOpen/Openin… | Surface inventory plus H1/multi recheck confirmed InsideBar H1, HourOpen, OpeningMomentum… | reconfirmed |  |
| 114 | 2026-07-14 | EA_ITSM | USDJPY M15 ITSM pullback survives the prereg kill screen but fails the research PF>1.30 b… | PARKED research near-miss… | PF=1.16 N=852 tpw=~3.27/week net=+$3959.60 DD=~8.93% |
| 115 | 2026-07-14 | SB / Spark / ITSM | Parked shelf summarized as SB (~1.99/wk PF~1.34) + Spark (~1.25/wk PF1.31) + ITSM (~3.27/… | BLOCKED_NOT_READY_FOR_PRE… |  |
| 116 | 2026-07-14 | SB / Spark | Confirming SB/Spark requires Real FivePercentOnline-Real + QFSI since research-proxy cann… | awaiting Real+QFSI |  |
| 117 | unspecified | Process/doctrine | Declared GPT Deep Research waived in favor of local self-research only. | policy |  |
| 118 | 2026-07-14 ~00:01 ICT | Process/doctrine | Owner authorized free MetaEditor/Strategy Tester/AlphaFactory Model0 use with self-direct… | free MetaEditor/Strategy… |  |
| 119 | 2026-07-14 | Chop/VolExp/TickVol/HourO… | Prior dual-filter near-miss shelf remains closed/parked, unchanged by this session. | closed/parked as before |  |
| 120 | 2026-07-14 | EA_SilverBullet | Authoritative control/challenger pair for weekend-flat on USDJPY M15 2021-2025 shows a ne… | PARKED (GOAL unmet) | other=control 002046 PF1.33/519/~1.99wk/net+7600.35; challe… |
| 121 | 2026-07-14 | EA_UsBillSlopeBasket | Reconfirmed authoritative control/challenger pair for the USBILL slope basket; challenger… | KILLED at Model 0 | other=control 013628 InpMode=0 PF1.05/1124 legs/~0.9-1.0wk/… |
| 122 | 2026-07-14 | EA_M15SparkAsian | Seed S111 Tue-Wed Asian session strategy tested on USDJPY M15; PF near research bar but c… | PARKED (research near-mis… | PF=1.31 N=325 tpw=~1.25/week net=+$1099.38 DD=~3.2% |
| 123 | 2026-07-14 | EA (Vol Expansion M15) | Vol-expansion M15 strategy killed on weak PF. | KILLED | PF=1.01 tpw=~2.84/wk |
| 124 | 2026-07-14 | EA (Chop-Trend M15) | Chop-Trend M15 strategy failed closed with weak PF. | FAIL_CLOSED | PF=1.08 other=race run 20260714_000557 |
| 125 | 2026-07-14 | InsideBar / GoldJPY | Both InsideBar and GoldJPY strategies killed tonight; do not rescue. | killed | PF=0.96 / ~0.97 |
| 126 | 2026-07-14 | Process | Reiterated that Real login is required for QFSI / confirmed / GOAL after-cost claims. | standing requirement |  |
| 127 | 2026-07-13 | EURUSD OIS / USDJPY JGB-U… | Acquired hash-bound overnight RFR/OIS-proxy and MoF JGB panels; both probes killed offlin… | KILL_AT_OFFLINE_PROBE | other=OIS-SOFR-ESTR train 159/0.76wk PF-A 1.003<1.05; USJP… |
| 128 | 2026-07-13 late night | EA_M15TickVolImpulse | Closed-bar volume-spike + body ATR strategy tested on USDJPY M15; cadence OK but edge fai… | KILLED at Model 0 | PF=1.0 N=890 tpw=~3.41 net=-$109.56 |
| 129 | 2026-07-13 | EA_UsBillSlopeBasket | Offline survivor result for the USBILL slope basket, now archival only after the Model0 k… | PROBE_SURVIVOR offline (M… | other=train 237/1.14wk PF-A 1.090>mom1.087; holdout 153/0.9… |
| 130 | 2026-07-13 | HYP-SR-FX-CROSS-SECTIONAL… | Cleared US bill-slope as independent from the cross-sectional USD-factor hypothesis. | INTAKE_CLEARED / INDEPEND… |  |
| 131 | 2026-07-13 | V8_EQUITY_BOND_DIFF_V1 | Equity-bond excess-return probe beat equity-only control but fell below the gate; killed. | KILL_AT_OFFLINE_PROBE | N=282 tpw=1.35 other=PF-A 1.004<1.10 |
| 132 | 2026-07-13 late night | EURUSD/USDJPY/GBPUSD bond… | Acquired US Treasury, ECB, and BoE yield curve panels and tested three yield-differential… | KILL_AT_OFFLINE_PROBE (al… | other=USEU 10Y diff train224/1.07wk PF-A0.579; USUK 10Y dif… |
| 133 | 2026-07-13 late night | EA_M15HourOpenBreak | Single-file closed-bar hour-open break strategy tested on EURUSD M15; cadence OK but edge… | KILLED at Model 0 | PF=0.94 N=829 tpw=~3.18 net=-$1445.39 DD=~21.9% |
| 134 | 2026-07-13 evening | Carry Δ-event H4 / carry-… | Four independent local freezes tested (carry event, carry-level, DGS2-DFR shock, COT Asse… | all killed | other=tpw1.37 PF-A1.12 (kill cadence<1.5); tpw14.8 PF-A0.91… |
| 135 | 2026-07-13 late night | Process/doctrine | Owner (Vietnamese) directed waiving ChatGPT Deep Research entirely for this campaign in f… | policy override |  |
| 136 | 2026-07-13 | EA_UsBillSlopeBasket | An earlier concurrent race-condition note claimed a kill that does not match the current… | stale, does not match cur… | other=claimed year-conc 0.78/233 trades/PF-A 1.195 |
| 137 | 2026-07-13 | V8_COT_TFF_SPEC_NET_CHG_V1 | Two independent implementations both killed the COT TFF spec-net-change probe, one via ye… | KILL_AT_OFFLINE_PROBE | other=train 225/2.16wk PF stress-A 1.194 beats control 1.14… |
| 138 | 2026-07-13 | V8_COT_TFF_LEVMONEY_H4_V1 | COT leveraged-money level probe beat the momentum control but failed the stress-PF gate;… | KILL_AT_OFFLINE_PROBE | N=392 tpw=2.51 other=PF stress-A 1.019 fails train_pf_stres… |
| 139 | 2026-07-13 | V8_CARRY_VOL_REGIME_V1 | Carry×volatility regime probe (Menkhoff-style) killed on weak stress PF. | KILL_AT_OFFLINE_PROBE | N=423 tpw=2.71 other=PF stress-A 0.947, expectancy -0.97 pi… |
| 140 | 2026-07-13 | EA_SilverBullet (HYP-SB-W… | Weekend-flat control/challenger frozen for Model0 but blocked by an unrelated terminal64… | BLOCKED (unrelated termin… |  |
| 141 | 2026-07-13 | carry/COT/bond-diff family | Closed out the GPT-waived self-research campaign as no-legal-candidate for carry/COT/bond… | NO_LEGAL_LOCAL_CANDIDATE… |  |
| 142 | 2026-07-13 late night | V8_CARRY_DIFF / V8_CARRY_… | Three independent carry-differential rebalance probes (weekly, daily, rate-event) all kil… | KILL_AT_OFFLINE_PROBE (al… | other=Weekly 13trades/0.05wk PF-A1.75; Daily 68trades/0.261… |
| 143 | 2026-07-13 | EA_CarryPublicRates | Compiled EA_CarryPublicRates successfully as an engineering scaffold, not probe survivor… | engineering scaffold only |  |
| 144 | 2026-07-13 night | Process/infra | alpha.ps1 Get-GitSnapshot now returns a fail-closed NOGIT hash when root is not a Git wor… | fail-closed handling added |  |
| 145 | 2026-07-13 late | Process/doctrine | Declared public exogenous FX archives exhausted for North-Star survivors; recommended fre… | frontier assessment |  |
| 146 | 2026-07-13 late eveni… | Process/doctrine | Owner granted unrestricted execution authority for the GOAL pursuit (research, data acqui… | unrestricted execution au… |  |
| 147 | 2026-07-13 evening | Process/doctrine | Autonomous loop mode set to 1A fail-closed as the preferred evidence-quality path; sub-ag… | 1A fail-closed preferred… |  |
| 148 | 2026-07-13 | EA_SonicR (H4/D1 expansio… | Deep Research V7 returned no legal H4/D1 candidate for the price-only surface; work conti… | NO_LEGAL_H4_D1_CANDIDATE_… |  |
| 149 | 2026-07-13 | Process/doctrine | Established that a poor-performing strategy run must close its hypothesis version and pre… | policy |  |
| 150 | 2026-07-12 (through 2… | EA_SonicR new-strategy di… | Ran a sequence of ChatGPT Deep Research submissions (V2 fix/benchmark family killed at in… | multiple Deep Research cy… | other=Impact-per-Pressure proxy probe: 74178 trades/177.70… |
| 151 | 2026-07-12 | Infra (log storage) | Deduplicated 327 byte-identical log mirror pairs into NTFS hardlinks, saving ~1.807 GiB w… | complete |  |
| 152 |  | Infra (log tooling) | large_log_reader.py now streams and hash-indexes large logs without printing unbounded ra… | complete |  |
| 153 | 2026-07-12 | Process/doctrine | Established that this personal project uses a single active implementation lane by defaul… | standing rule |  |
| 154 | 2026-07-12 (contextua… | Process/infra | Found an empty root .git placeholder that regenerates itself; instructed not to trigger r… | not a repository, no repe… |  |
| 155 |  | EA_SonicR / fx_portfolio_… | EA_SonicR remains research-only; the SilverBullet portfolio lane is open only for Phase 0… | standing rule |  |
| 156 |  | EA_SonicR / EA_SilverBull… | Canonical sources are EA_SonicR.mq5 and, for the new lane, pinned EA_SilverBullet_v2.mq5;… | standing rule |  |
| 157 |  | EA_SonicR | Canonical Sonic symbols remain unsuffixed XAUUSD/EURUSD/GBPUSD; the new lane additionally… | standing rule |  |
| 158 |  | Process | Plus-suffix symbols such as XAUUSD+ are legacy/E8 context unless explicitly reopened. | standing rule |  |
| 159 |  | EA_SonicR | EA_SonicR is research-only; no demo/prop/live promotion is allowed. | standing rule |  |
| 160 | 2026-07-10/11 | Portfolio-wide audit | Portfolio audit across 34 EAs found no run meeting both the PF and cadence GOAL gates sim… | audit complete | other=217 identity-valid runs across 34 EAs; 64 exceed PF1.… |
| 161 |  | Process/infra | Runner/validator evidence path is fail-closed hardened: exact run markers, source/EX5/con… | standing rule |  |
| 162 |  | Process/infra | MetaEditor CLI exit 1 is only accepted as a compile pass when the new compile log proves… | standing rule |  |
| 163 |  | EA_SonicR telemetry | Lifecycle telemetry v3 adds deal-level commission/swap/fee/net fields required by the ver… | standing infra |  |
| 164 |  | Process/infra | The cost builder derives spread, commission P90, and side-aware slippage from raw CSV/JSO… | standing rule |  |
| 165 |  | Process/infra | Current robustness/PBO/White Reality Check producers are diagnostic-only and always set p… | standing rule |  |
| 166 |  | Registry (workspace-wide) | The workspace-wide FX research registry has 54 rows, with three still-open idea-state str… | three nonterminal rows at… |  |
| 167 |  | Portfolio Phase 0 | Shared runner source/telemetry contracts pass 338/338 but the deterministic artifact repo… | BLOCKED |  |
| 168 |  | Portfolio Phase 0 | A sub-agent accidentally displayed a SilverBullet RunMeta summary before the access contr… | BLOCKED_REQUIRES_CLEAN_FU… |  |
| 169 | 2026-07-11 | Process/infra | Root .git was removed and archived; recovery-only, never a compile/evidence source, until… | root .git absent, must no… |  |
| 170 | 2026-07-12 | Process/infra | A newly created empty root .git was quarantined again; 16 safe cache/empty targets remove… | complete |  |
| 171 | 2026-07-12 | External repo (M2 risk fo… | A separate external Git repo's m2-risk-v3 engineering foundation is hash-closed and red-t… | ENGINEERING_ONLY / OWNER-… |  |
| 172 |  | Process/cost data | Broker-cost coverage remains far too sparse to treat missing fields as zero cost. | standing blocker | other=2024-2025 non-zero M15 spread coverage ~4%; commissio… |
| 173 |  | Process | The remaining 2026-05/06 narrative is backup-indexed history whose registered artifacts a… | chronological context only |  |
| 174 | 2026-05-09 | EA_SonicR | Backup-indexed history says public Sonic R .mq4/.tpl source was recovered into quarantine… | backup-indexed history |  |
| 175 |  | EA_SonicR | InpUseSourceSrInteractionV1=false does not fully isolate Source S/R because source_sr_run… | blocked pending code fix |  |
| 176 |  | EA_SonicR | PVA V1 decision override, S/R WHQ V1, and Classic Wave/Dragon V1 probes were parked as de… | parked |  |
| 177 |  | EA_SonicR | sonic_* headers and replay fields passed sidecar/join checks; not a decision patch. | passed sidecar checks, no… |  |
| 178 | 2026-05-10 | EA_SonicR | Trader-State label loop cites runs 20260510_005641/010229/010813 whose counts are unavail… | counts unverified until a… |  |
| 179 | 2026-05-10 | EA_SonicR | direction=NONE rows now map to unknown/observe/no-management-edge; full M15 runs show run… | parked as correctness pat… |  |
| 180 | 2026-05-10 | EA_SonicR | Found 262 candidate-like scanner rows but zero aligned to a directional candidate; main b… | analysis complete, no pat… | other=262 candidate-like rows; 0 aligned to directional can… |
| 181 |  | EA_SonicR | Locked-label separation found run_for_profits weaker than position_building; no context-d… | complete and parked | other=120/120 labels joined; run_for_profits 9 cases, posit… |
| 182 |  | EA_SonicR | Margin precheck, restart-state rebuild, retry default, and warmup compile cleanly with no… | execution hardening only |  |
| 183 | 2026-05-11 | EA_SonicR (EUR London Cla… | Route-scope mismatch (M5-scoped Classic vs disabled legacy M15 flag) caused zero trades. | killed as configured | other=49558 signals, 0 trades, all direction=NONE |
| 184 | 2026-05-11 | EA_SonicR (EUR M15 Classi… | Fixed the route-scope issue and fired 2 London ClassicTrend trades over 2 years; killed a… | killed by prereg (2 trade… | PF=1.59375 net=$29.64 |
| 185 | 2026-05-12 | EA_SonicR (EUR density re… | Source-core improved candidate density but remained far below cadence/edge targets; trap/… | killed | other=M5 T1 route 4 trades PF0.5054; M15 no-PVSRA 2 trades… |
| 186 | 2026-05-12 | EA_SonicR | Built a lightweight HTML casebook and 60-row blind source-core label packet with no forbi… | label input only |  |
| 187 | 2026-05-10 | EA_SonicR (XAUUSD opportu… | Opportunity-score-gated XAUUSD M15 option produced 2 trades with catastrophic PF. | failed, do not advance | N=2 PF=0.003 net=-292.59 |
| 188 |  | EA_SonicR | Created a strict blind manual label packet V1 with 89 cases across run_for_profits/positi… | label packet created |  |
| 189 | 2026-06-05 | EA_SonicR (EURUSD sleeve… | Patched static inputs to runtime variables and restored SMC/Sweep config; verified equiva… | restored/verified | other=6 trades, Win Rate 83.3%, PF2.31 (Q1-2021) |
| 190 | 2026-06-08 | XAU S1 (Gemini-proposed A… | A closed-M15 ATR(14)>=1.20*EMA100 impulse gate improved PF but collapsed S1 cadence from… | Killed | other=control 20260608_002730 326 trades PF1.2976 net1079.7… |
| 191 | 2026-06-08 | XAU S1 (Dragon/Trend dist… | A Dragon-Trend EMA distance veto preserved cadence but removed the key impulse winners, c… | Killed | other=control 20260608_024033 326 trades PF1.2976 net1079.7… |
| 192 | 2026-06-08 | XAU S1 (micro-structure f… | Body ratio, micro clearance, and Dragon congestion features were tested to separate impul… | Killed offline | other=best rule PF1.1836 net371.56, kept only 48.93% of imp… |
| 193 | 2026-06-08 | XAU S1 (H1 structure swee… | Rebuilt H1 structure from M5 sidecars and found a real but insufficient sweep-depth signa… | Killed offline | other=cadence-safe best rule 287 trades PF1.3563 net1166.32… |
| 194 | 2026-06-08 | EUR (Asian-range stop hun… | Rebuilt M15 bars from a donor run and tested an Asian-range manipulation reversal; failed… | Killed offline | other=573 candidates (2.21/wk); synthetic PF1.1014; cost PF… |
| 195 | 2026-06-08 | EUR (counter-EMA high-swe… | Preregistered post-hoc counter-EMA extension anomaly; PF looked high but sample size, sep… | Killed offline | other=holdout H4-extension cost PF1.8113 but only 14 candid… |
| 196 | 2026-06-08 | GBPUSD (London Dragon val… | GBPUSD London value-drift idea failed before any EA work due to insufficient target runwa… | Killed offline | other=258 candidates; train cost PF0.6554; mean anchor dist… |
| 197 | 2026-06-08 | EA_SonicR registry-wide | Registry-by-hypothesis audit found no confirmed or portfolio-sleeve latest state; marked… | audit complete |  |
| 198 | 2026-06-08 | XAU S1 labeling | Exported a 60-case blind label packet from existing XAU S1 artifacts with outcome fields… | new evidence-class probe… |  |
| 199 | 2026-06-08 | XAU S1 labeling | Built an analyzer to validate frozen labels; smoke against unlabeled data correctly produ… | ready, smoke failed close… |  |
| 200 | 2026-06-08 | XAU S1 labeling | Merge tool only writes a frozen label CSV once all 60 batch case IDs are present; smoke w… | ready, smoke failed closed |  |
| 201 | 2026-06-08 | XAU S1 labeling | Deterministic proxy labels separated against the private key as a benchmark, not human la… | analysis-only benchmark | other=label_sr_runway=near_whole_half_quarter: 39 cases, im… |
| 202 | 2026-06-08 | XAU S1 labeling | Four Gemini label batches merged and separated with 0 errors, mirroring the proxy baselin… | authorizes full S/R runwa… | other=mirrors proxy: near_whole_half_quarter 39 cases impul… |
| 203 | 2026-06-08 | XAU S1 (S/R runway filter) | Applied the label-supported S/R runway clue to all 321 S1 trades; high-PF variants cut ca… | Killed offline | other=baseline 321 trades PF1.288648; RUNWAY-only 98 trades… |
| 204 | 2026-06-08 | XAU S1 (H1 EMA34 slope co… | Four signed H1 EMA34 slope rule screens tested; none passed gates. | Killed offline | other=keep_positive_velocity 118 trades PF1.191458 net267.76 |
| 205 | 2026-06-08 | EURUSD/GBPUSD London Clas… | Local de-dup rejected this Gemini proposal as a renamed blend of already-killed Asian-ran… | Killed before prereg/donor |  |
| 206 | 2026-06-08 | EA_SonicR frontier | After excluding several dead families, Gemini returned a frontier-reached reply, treated… | FRONTIER_REACHED_NO_LEGAL… |  |
| 207 | 2026-06-08 | XAUUSD M5 donor (MFE-base… | Proposed replaying an MFE>=1.0R move-to-+0.2R management rule; rejected as overlapping al… | Killed before prereg/repl… |  |
| 208 | 2026-06-08 | EA_SonicR frontier | After management replay was also banned, Gemini again returned a frontier-reached reply;… | FRONTIER_REACHED_NO_LEGAL… | other=registry snapshot: 51 rows, 23 hypotheses, killed=15/… |
| 209 | 2026-06-08 | Infra (MT5 Common Files) | Backup index says 225 stale MT5 Common/Files telemetry/cache items (439.72 MB) were archi… | backup-indexed history |  |


---
*Ledger đầy đủ 210 entry, detail config theo `#idx` ở `00. Old File/hot_details/hot_ledger_details.json`. Lịch sử prose nguyên si: `00. Old File/hot_archive_20260715_full.md`. Không sửa entry lịch sử; append entry mới lên ĐẦU bảng.*
