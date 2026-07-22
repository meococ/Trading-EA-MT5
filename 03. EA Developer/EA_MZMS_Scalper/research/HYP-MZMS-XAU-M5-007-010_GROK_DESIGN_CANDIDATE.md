# HYP-MZMS-XAU-M5-007..010 — Grok Design Candidate (pre-source / pre-outcome)

**Status:** `DESIGN_ONLY_CANDIDATE`  
**Author role:** bounded Senior Quant / MQL5 strategy architect  
**Frozen before:** source edit, compile, Model 0, outcome access, registry append  
**Date (design stamp):** 2026-07-22  
**Parent authority:** Owner-authorized four-mechanism campaign in `04. Memory/hot.md`  
**Package:** `EA_MZMS_Scalper`  
**Reserved IDs:**

| Mode | Hypothesis ID | Family short name |
|---:|---|---|
| `InpSignalMode=2` | `HYP-MZMS-XAU-M5-007` | Fresh impulse initiation |
| `InpSignalMode=3` | `HYP-MZMS-XAU-M5-008` | Trend pullback reclaim |
| `InpSignalMode=4` | `HYP-MZMS-XAU-M5-009` | Volatility compression breakout |
| `InpSignalMode=5` | `HYP-MZMS-XAU-M5-010` | Exhaustion / rejection mean reversion |

This document is implementation-ready design only. It does **not** authorize code change, backtest, rescue of HYP-003/005/006, promotion, paper, or live.

---

## 0. Epistemic boundary and hard non-goals

### 0.1 What this is

- Four **materially different closed-bar entry mechanisms** for XAUUSD M5.
- Preferred delivery: **one canonical multi-variant EA** extending the existing package, with
  `ENUM_SIGNAL_MODE` values `2..5` (retain `0` control and `1` legacy MZMS for identity/tests).
- Shared frozen risk/execution shell so the only intentional difference across the four
  research arms is the **entry boolean object**.

### 0.2 What this is not

- Not four threshold tweaks of the killed local-MACD-histogram-extremum object
  (`HYP-MZMS-MACD-HIST-SLOPE-*` 003/005/006).
- Not post-hoc hour / day / year / direction / BE / timeout filters derived from HYP-006
  outcomes or the 200-chart loser forensics.
- Not an economic claim. No PF, expectancy, or edge is asserted.
- Not a license to reopen HYP-006.

### 0.3 Lessons that shape the quartet (prospective, not rescue)

From the invalid HYP-006 XAU pair and the 200-chart integrated forensics (diagnostic only):

1. Local MACD histogram extrema frequently fire **after** a mature impulse; the micro-turn is
   not a freshness detector.
2. Side-only EMA200 + permissive RSI mid-band + elevated ADX can all remain true on both
   continuation and reversal paths.
3. Loser mass split into rapid full-stop adverse paths and 15-bar / 75-minute no-follow-through
   timeouts; “tight stop” was **not** established as a general cause.
4. Cadence of the old object was far above the 2–5 trades/elapsed-week research ceiling.
5. History quality 98% failed the frozen ≥99% gate → **economics diagnostic-only** if any future
   run repeats that condition.

Therefore the four successors deliberately target **different causal objects**:

| ID | Causal object (what must be true at decision) |
|---|---|
| 007 | Fresh **range expansion / impulse start**, not a late oscillator turn |
| 008 | **Pullback into trend** then closed-bar reclaim of the pullback pivot |
| 009 | **Volatility compression** then closed-bar break of the squeeze envelope |
| 010 | **Exhaustion / rejection** after extension, fade the spike (mean reversion) |

### 0.4 Explicit history-quality acknowledgment

**If MT5 report history quality is below 99%, the entire economic surface of that run is
`INVALID_ENGINEERING_RUN` / diagnostic-only.** No PF/net/DD/WR may be used as authoritative
backtest evidence, and no kill-for-no-edge or promotion claim may be issued from that run.
The known XAU prior is adverse (HYP-006 reported 98%). A future authoritative XAU campaign
requires a pre-run data source capable of satisfying the frozen history gate. This design
still freezes full economic kill gates for the case when history quality **does** pass ≥99%,
and freezes parallel diagnostic reporting rules when it does not.

---

## 1. Shared frozen research contract (all four IDs)

These fields are **common** across HYP-007..010 unless a section explicitly overrides a
signal-local constant. Overrides may only change **signal geometry / signal-local
indicators**, not the risk or cost shell.

### 1.1 Market / tester identity

| Field | Frozen value |
|---|---|
| Symbol | `XAUUSD` |
| Timeframe | `M5` |
| Model | `0` (every tick based on real ticks) |
| Window | `2018.01.01` – `2026.07.22` (inclusive requested bounds) |
| Deposit / leverage | USD `100000` / `1:100` |
| Risk per accepted entry | `0.01%` of current equity |
| Digits / point / PipSize | 2 digits, point `0.01`, `PipSize() = _Point` (XAU contract) |
| Max spread | `InpMaxSpreadPips = 35.00` → **35 XAU points** (= USD 0.35) |
| Structure buffer | `InpStopBufferPips = 40.00` → **40 XAU points** (= USD 0.40) |
| Optimization / genetic / rerun | **Forbidden** |
| BE / trailing | **OFF** (`InpUseBreakEven=false`; no trailing) |
| Intrabar signal evaluation | **Forbidden** (closed-bar only; `shift >= 1`) |
| Promotion / paper / live | **Forbidden** |

### 1.2 Cost and news provenance (diagnostic boundary)

- Cost provenance remains **tester-reported only** → even a history-valid run is at most
  `DIAGNOSTIC_COMPLETE_NO_PROMOTION` unless a later Owner contract upgrades cost evidence.
- Embedded news calendar is EUR/USD 2019–2022, **not** XAU full-window PIT. Freeze
  `InpRequireNewsGuard=false` uniformly for all four arms (same limitation as HYP-006).
  This forbids promotion; it is not a post-outcome toggle.

### 1.3 Clock / session / ownership / risk guards

Reuse the existing FivePercent EU-DST server→UTC contract
(`CLOCK_CONTRACT = fivepercent_server_eu_dst_to_utc_v1`):

| Guard | Frozen value |
|---|---|
| Session | `08:00` ≤ UTC minute `< 17:00` |
| Hard flatten | `18:15` UTC |
| Max entries / UTC day | `5` |
| Daily loss guard | `1.5%` of day-start equity |
| Account DD guard | `8%` from peak equity |
| Cooldown | `5` closed M5 bars after last **accepted entry bar** |
| Concurrent exposure | one owned position max; any same-symbol exposure blocks new entry |
| Mutation authority | `InpResearchAutoMode=true` **and** `MQL_TESTER` only |

### 1.4 Shared stop / target / time-exit geometry

Common geometry (deliberately **not** a HYP-006 rescue; it is a matched execution shell so
entry objects are comparable):

| Component | Rule |
|---|---|
| Entry quote | First tick of the **new** M5 bar after signal bar close (see §1.5) |
| Structural stop | Long: `min(low[1..L]) - 40 points`; Short: `max(high[1..L]) + 40 points` with lookback `L = 5` closed bars, series index aligned to decision bar |
| ATR stop | Long: `entry - 1.5 * ATR14[1]`; Short: `entry + 1.5 * ATR14[1]` |
| Final stop | Farther of structural and ATR stop (more protective) |
| Target | `1.6R` from fill vs initial stop distance |
| Time exit | Close at or after `15` M5 bars from position open time, or hard flatten 18:15 UTC, whichever first |
| BE | OFF |
| Partial / trail | None |

**Kill note:** stop/target/time are **shared** and frozen pre-outcome. Post-run “tighten stop /
extend hold / BE on” are illegal same-hypothesis rescues; they would require new IDs.

### 1.5 Earliest executable quote (all variants)

Notation (MT5 closed-bar, series as-of decision):

- At the first tick where `iTime(M5,0)` advances, the just-closed bar is **shift 1**.
- All indicator / OHLC predicates use **shift ≥ 1 only**.
- `CopyRates(..., start_pos=1, ...)` as in current source: `bars[0] ≡ shift 1`.

**Earliest fill:** market order on that first new-bar tick at `Ask` (long) or `Bid` (short),
subject to spread ≤ 35 points and all ownership/risk guards. No limit resting, no
intrabar confirmation, no wait-for-retest beyond what the closed-bar rule already encodes.

### 1.6 Indicator parity declaration

Model-0-bound surface uses **MT5 native** handles (per workspace parity doctrine):

| Indicator | MT5 call | Formula note |
|---|---|---|
| ATR | `iATR(M5, 14)` | SMA of True Range (`atr_mt5`) |
| ADX / +DI / −DI | `iADX(M5, 14)` | MT5 ADX path (`adx_mt5`) |
| RSI | `iRSI(M5, 14, PRICE_CLOSE)` | Wilder (matches MT5) |
| EMA | `iMA(..., MODE_EMA, PRICE_CLOSE)` | standard |
| MACD | `iMACD(12,26,9, PRICE_CLOSE)` | only where a mode uses it |
| Bollinger | `iBands(M5, 20, 2.0, 0, PRICE_CLOSE)` | mode 009 |
| Donchian high/low | pure OHLC over closed bars | modes 007/009 |

No Wilder-ATR / classic-Wilder-ADX offline substitute may be claimed as MT5 truth without a
parity artifact.

### 1.7 Shared implementation preference

**One package, multi-mode:**

```text
enum ENUM_SIGNAL_MODE {
  SIGNAL_CONTROL = 0,                 // retained engineering control
  SIGNAL_MZMS_LEGACY_HIST_EXT = 1,    // HYP-006 object; not re-run as 007-010
  SIGNAL_IMPULSE_INIT = 2,            // HYP-007
  SIGNAL_PULLBACK_RECLAIM = 3,        // HYP-008
  SIGNAL_SQUEEZE_BREAK = 4,           // HYP-009
  SIGNAL_EXHAUST_REJECT = 5           // HYP-010
};
```

Each hypothesis run binds:

- unique `hypothesis_id` string per mode (007..010),
- unique `InpMagic` per mode (recommended: `5600722 + mode`),
- exact `InpSignalMode` override in the AlphaFactory task packet,
- one serial Model-0 run only after parent prereg + registry row exist.

### 1.8 Shared falsifiable acceptance envelope (when history ≥ 99%)

Inherited research envelope (context, not rescue authority). A single arm is
`DIAGNOSTIC_COMPLETE_NO_PROMOTION` only if history ≥ 99% **and** engineering integrity holds;
economic kill/park uses the gates below.

| Gate | Pass condition |
|---|---|
| History quality | report ≥ **99%** else `INVALID_ENGINEERING_RUN` |
| Bars / ticks | materially covers requested window; bind data fingerprint |
| Lifecycle | exact open/close reconciliation; net P/L gap `$0.00` |
| Non-repaint | exact-source audit PASS after signal change |
| Cadence | **2.0 – 5.0** trades per **elapsed calendar week** of requested window |
| PF | ≥ **1.35** (workspace GOAL uses ≥1.30; campaign freezes 1.35 to match HYP-006 transfer bar) |
| Max DD | ≤ **6.0%** at 0.01% risk |
| Cost stress | only if verified cost exists: PF@x1.5 ≥ 1.25 and PF@x2 ≥ 1.00; else report diagnostic cost only |
| Year concentration | not all economic mass in one calendar year; kill if ≤1 of ≥8 full years PF≥1 **and** pooled PF&lt;1.35 |
| Direction | both long and short must each produce ≥15% of trades **or** arm is labeled single-direction diagnostic (not auto-kill alone) |
| Monte Carlo | P95 max DD ≤ 6% when N≥100; sequence-shuffle does not invent edge if total P/L &lt; 0 |
| Matched identity | source/EX5/config/report hashes bound; one RunMeta + Lifecycle pair |

**Per-arm economic kill (history-valid):** fail cadence **or** PF &lt; 1.00 **or** expectancy &lt; 0
with N≥100 **or** max DD &gt; 6% → `KILL_DIAGNOSTIC_NO_EDGE` for that ID. No threshold rescue.

**Invalid history path:** report metrics as diagnostic shape only; terminal
`PARK_INVALID_ENGINEERING_RUN_HISTORY_QUALITY_BELOW_99`; do not convert adverse shape into a
legal no-edge kill that pretends the run was authoritative.

### 1.9 Explicit de-dup vs killed families

| Candidate | Distinct from | Why |
|---|---|---|
| 007 impulse initiation | HYP-006 MACD local extremum | Trigger is Donchian/range expansion + ADX **rising** + ATR expansion; no hist local min/max |
| 008 pullback reclaim | HYP-006; ICT sweep/reclaim killed family | No sweep/FVG/MSS; trend EMA stack + pivot reclaim after measured pullback |
| 009 squeeze break | HYP-006; MR-grid / session-drift | Compression→expansion of BB width + ATR percentile, then envelope break |
| 010 exhaustion fade | HYP-006 continuation bias | Opposite economic intent: fade extension via rejection wick + RSI extreme + ADX roll-over |
| All four | Unicorn/PO3/KLR/FVG densify | No FVG, breaker, killzone raid, or score composite |

---

## 2. Notation for shift-indexed boolean rules

Let series indexing at decision time (new bar open) be:

- `C[k]`, `O[k]`, `H[k]`, `L[k]` = close/open/high/low of shift `k` (`k=1` last closed).
- `ATR[k]`, `ADX[k]`, `PDI[k]`, `MDI[k]`, `RSI[k]`, `EMA_n[k]`, `MACD_main[k]`,
  `MACD_sig[k]`, `BB_upper[k]`, `BB_mid[k]`, `BB_lower[k]` similarly.
- Body: `Body[k] = |C[k] - O[k]|`.
- Range: `Range[k] = H[k] - L[k]` (require `Range[k] > 0` for wick fractions).
- Bull/bear close: `Bull[k] = C[k] > O[k]`; `Bear[k] = C[k] < O[k]`.

**Implementation constraint:** current `ReadIndicator` only accepts shifts `{1,2,3}`. Design
requires generalizing to `CopyBuffer(handle, buffer, shift, 1, ...)` for shifts up to the
maximum lookback used below (≤ 40). Decision remains closed-bar.

---

## 3. HYP-MZMS-XAU-M5-007 — Fresh impulse initiation  
### `InpSignalMode = 2` · `SIGNAL_IMPULSE_INIT`

### 3.1 Causal thesis

Gold M5 continuation edge, if any, lives at the **start** of a volatility expansion out of a
recent range, when directional DI confirms and ADX is **rising from a non-exhausted base**,
not at a late MACD histogram micro-turn after the impulse is mature. The object is
**fresh range-break initiation** with expansion confirmation on the same closed break bar.

### 3.2 Indicators and fixed parameters

| Name | Spec | Role |
|---|---|---|
| Donchian channel | period `N_dc = 20` closed bars, shifts `2..21` (exclude shift 1 from channel so break is non-tautological with the break bar itself) | Range boundary |
| ATR | 14 | Expansion + stop |
| ADX / +DI / −DI | 14 | Trend initiation vs mature grind |
| EMA | 50 close | Directional side filter (not 200 side-only of HYP-006) |
| Body expansion | vs median body of shifts `2..11` (10 bars) | Impulse bar quality |

Fixed thresholds (pre-outcome; not from HYP-006 readout mining):

| Symbol | Value | Meaning |
|---|---:|---|
| `N_dc` | 20 | Donchian lookback excluding signal bar |
| `ADX_min` | 16 | Floor so pure flat noise is rejected |
| `ADX_max` | 32 | Cap so already-vertical regimes are rejected (anti late-impulse) |
| `ADX_rise` | `ADX[1] > ADX[2]` | Rising strength on signal bar |
| `ATR_exp` | `ATR[1] > ATR[3]` | Short-horizon ATR expansion |
| `Body_mult` | 1.20 | `Body[1] >= 1.20 * Median(Body[2..11])` |
| `EMA_period` | 50 | Side bias |
| `DI_lead` | `PDI[1] > MDI[1]` long / inverse short | Directional leadership |

### 3.3 Exact shift-indexed entry rules

**Common gates (both sides):**

```text
G_imp_common :=
    ATR[1] > 0
AND Range[1] > 0
AND ADX[1] >= 16
AND ADX[1] <= 32
AND ADX[1] > ADX[2]
AND ATR[1] > ATR[3]
AND Body[1] >= 1.20 * Median(Body[2], ..., Body[11])
AND DonchianHigh_20 = max(H[2], H[3], ..., H[21])
AND DonchianLow_20  = min(L[2], L[3], ..., L[21])
```

**Long (`direction = +1`):**

```text
Long_007 :=
    G_imp_common
AND C[1] > DonchianHigh_20
AND Bull[1]
AND C[1] > EMA50[1]
AND PDI[1] > MDI[1]
AND C[1] >= O[1] + 0.55 * Range[1]   // close in upper 45% of bar (outer close)
```

**Short (`direction = -1`):**

```text
Short_007 :=
    G_imp_common
AND C[1] < DonchianLow_20
AND Bear[1]
AND C[1] < EMA50[1]
AND MDI[1] > PDI[1]
AND C[1] <= O[1] - 0.55 * Range[1]   // close in lower 45% of bar
```

**Signal exclusivity:** if both true (pathological), return 0.  
**No MACD histogram extremum, no RSI 42–58 band, no EMA200.**

### 3.4 Invalidation (setup-level, pre-entry)

If after signal detection but before send any guard fails (spread, exposure, session, risk),
abort without entry. There is no multi-bar pending state in v1: signal is **single-bar
consumable** at the open of the bar following the break close.

Post-entry invalidation is only the shared stop / time / flatten geometry (§1.4).

### 3.5 Adversarial prior

- Donchian-20 breaks on gold M5 are often noise or late continuation; ADX cap may delete
  the only strong trends **or** still admit grind.
- Cadence may exceed 5/week if gold trends; or starve if ADX window is too tight.
- Close-location filter can correlate with the break definition (partial redundancy risk).
- Cost at 35-point spread ceiling can erase small R multiples on M5.

### 3.6 Kill gates specific to 007

In addition to §1.8:

1. If median MAE path shows ≥60% of losers already beyond 0.8R within 3 bars **and** PF&lt;1 →
   object is late-or-fake break (family fail), not “widen stop”.
2. If ADX at entry has median ≥28 and PF&lt;1 → “freshness” claim fails (still mature).
3. If trades/week &gt; 8 after all gates → density object fails research cadence even if PF
   looks modest; kill/park without densify-by-loosening.

### 3.7 Decision-time telemetry (007)

Emit per accepted or rejected candidate (decision snapshot):

- `signal_mode=2`, hypothesis id, bar time UTC+server, spread points  
- `C/O/H/L[1..3]`, `DonchianHigh_20`, `DonchianLow_20`  
- `ATR[1], ATR[3], ADX[1], ADX[2], PDI[1], MDI[1], EMA50[1]`  
- `Body[1]`, median body reference, body_mult ratio  
- each boolean subgate PASS/FAIL  
- planned stop/target/R if accepted  

---

## 4. HYP-MZMS-XAU-M5-008 — Trend pullback reclaim  
### `InpSignalMode = 3` · `SIGNAL_PULLBACK_RECLAIM`

### 4.1 Causal thesis

In a **pre-established M5 trend**, temporary counter-moves that tag a fast EMA and then
**reclaim** a closed-bar pullback pivot contain a different information set than breakout or
oscillator micro-turns: the market has already chosen a side; the edge hypothesis is
continuation after a measured, non-breakdown pullback.

### 4.2 Indicators and fixed parameters

| Name | Spec | Role |
|---|---|---|
| EMA fast | 20 close | Pullback magnet |
| EMA slow | 100 close | Higher-span trend bias (not HYP-006 EMA200 alone) |
| ATR | 14 | Pullback depth + stop |
| ADX | 14 | Trend present |
| Swing pivot | 3-bar fractal high/low on closed bars | Reclaim reference |

Fixed thresholds:

| Symbol | Value | Meaning |
|---|---:|---|
| `EMA_fast` | 20 | Pullback reference |
| `EMA_slow` | 100 | Trend side |
| `ADX_trend` | 20 | Minimum trend presence |
| `Pull_min` | 0.40 ATR | Minimum adverse excursion of pullback vs local pivot |
| `Pull_max` | 1.80 ATR | Reject deep breakdown-sized pulls |
| `Reclaim_buf` | 0.05 ATR | Close beyond pivot by small buffer |
| `Pivot_k` | 3 | Fractal half-width |

### 4.3 Pivot definitions (closed-bar)

A **confirmed bullish pullback pivot low** at shift `p` (with `p >= 4` so fractal is closed):

```text
PivotLow[p] :=
    L[p] < L[p-1] AND L[p] < L[p-2] AND L[p] < L[p+1] AND L[p] < L[p+2]
    // with series: need shifts p-2..p+2 all existing; p is the center
```

Operational search at decision time: find the **most recent** `p ∈ {3,4,5,6,7,8}` such that
the five-bar fractal using shifts `{p-2,...,p+2}` is a pivot low (long) or pivot high (short)
and that pivot is fully closed (`p+2 >= 1` ⇒ center `p >= 3`).

Use center shift `p*` = smallest `p` in `{3..8}` satisfying the fractal (most recent).

### 4.4 Exact shift-indexed entry rules

**Long:**

```text
TrendLong :=
    EMA20[1] > EMA100[1]
AND C[1] > EMA100[1]
AND ADX[1] >= 20
AND PDI[1] > MDI[1]

PullbackLong :=
    exists p* in {3..8}:
         PivotLow confirmed at p*
     AND (min(L[1], L[2], ..., L[p*]) - EMA20[p*]) is not required
     AND depth = (H_ref - L[p*]) / ATR[1]
         where H_ref = max(H[p*], H[p*+1], ..., H[p*+3])  // pre-pivot swing reference
     AND depth >= 0.40
     AND depth <= 1.80
     AND L[p*] <= EMA20[p*] + 0.15 * ATR[1]   // tagged / approached fast EMA zone
     AND L[p*] >= EMA100[p*] - 0.25 * ATR[1]  // did not decisively break slow bias

ReclaimLong :=
    C[1] > L[p*] + 0.05 * ATR[1]
AND Bull[1]
AND C[1] > EMA20[1]
AND C[2] <= L[p*] + 0.15 * ATR[1]   // prior bar still interacting with pivot zone
AND not (C[1] > max(H[2], H[3], H[4], H[5]))  // NOT a fresh 4-bar high break (anti-007 overlap)

Long_008 := TrendLong AND PullbackLong AND ReclaimLong
```

**Short:** mirror all inequalities / pivot high / DI.

```text
Short_008 := TrendShort AND PullbackShort AND ReclaimShort
```

**Material non-overlap with 007:** 008 **forbids** the signal bar being a fresh 4-bar extreme
break; it requires a **prior** pivot interaction and reclaim. 007 **requires** Donchian-20 break.

### 4.5 Invalidation

- Pre-entry: shared guards only; no multi-bar hold of “pending reclaim” beyond the boolean
  at shift 1 (if reclaim is late, miss the trade — no chase).
- Structural invalidation concept for forensics: close beyond slow EMA against trend after
  entry is an anatomy label only; exits remain stop/time/flatten.

### 4.6 Adversarial prior

- EMA pullback/reclaim is one of the most crowded retail objects; net edge may be ≤0 after
  XAU costs.
- Fractal pivots on M5 are noisy; depth gates may still overfit geometry.
- Non-overlap constraint with 007 may leave only mediocre mid-trend chops.
- ICT pivot-dwell family was killed for density/tautology on EURUSD — this object is
  **not** that family, but pivot geometry always carries tautology risk; rules above require
  EMA tag + depth band + non-breakout bar to reduce pure OHLC restate.

### 4.7 Kill gates specific to 008

1. If ≥70% of entries have `depth` in a single 0.2-ATR bin and PF&lt;1 → geometry collapse.
2. If median bars from `p*` to entry ≥ 6 and PF&lt;1 → late reclaim (mature), kill without
   “enter earlier” rescue on same ID.
3. If slow-EMA side filter alone recovers the same trade set as full rule (ablation proxy in
   offline probe later) → information set is side-only; kill as non-causal.

### 4.8 Decision-time telemetry (008)

- `signal_mode=3`, `p*`, pivot price, depth/ATR, EMA20/100, ADX, PDI/MDI  
- distances: `L[p*]-EMA20`, `C[1]-pivot`, 4-bar high/low break flags  
- all subgate PASS/FAIL  

---

## 5. HYP-MZMS-XAU-M5-009 — Volatility compression breakout  
### `InpSignalMode = 4` · `SIGNAL_SQUEEZE_BREAK`

### 5.1 Causal thesis

Predictable M5 expansion follows **abnormally compressed realized volatility**. The
information is the **pre-break squeeze state**, not the oscillator turn after expansion. Entry
is the first closed break of the Bollinger envelope **only if** the prior bars were in a
documented compression regime.

### 5.2 Indicators and fixed parameters

| Name | Spec | Role |
|---|---|---|
| Bollinger | period 20, deviation 2.0, PRICE_CLOSE | Envelope + width |
| ATR | 14 | Compression rank + stop |
| ATR compression rank | ATR[2] vs max ATR over shifts `3..22` (20 values) | Pre-break vol state |
| ADX | 14 | Prefer non-already-trending grind |
| EMA | 34 close | Mild directional tilt after break |

Fixed thresholds:

| Symbol | Value | Meaning |
|---|---:|---|
| `BB_period` | 20 | Standard |
| `BB_dev` | 2.0 | Standard |
| `Width_comp` | `BB_width[2] <= 0.85 * median(BB_width[3..22])` | Compression vs recent median width |
| `ATR_comp` | `ATR[2] <= 0.90 * max(ATR[3..22])` is weak; use percentile proxy: `ATR[2] <= percentile_30(ATR[3..34])` approximated by: ATR[2] ≤ 7th of 32 sorted values (≈ P22–P25). **Implementation freeze:** `Count(ATR[j] <= ATR[2] for j=3..34) <= 8` among 32 bars (ATR[2] in bottom ~25%). |
| `ADX_cap` | 28 on shift 2 | Squeeze should not already be a strong trend |
| `Break_buf` | 0.05 ATR | Close beyond band |
| `EMA_tilt` | 34 | Post-break side |

**Critical sequencing:** compression is measured on **shift 2 and older**; break is on
**shift 1**. This prevents using the expansion bar’s own ATR/BB width as the squeeze proof.

### 5.3 Exact shift-indexed entry rules

```text
BB_width[k] := (BB_upper[k] - BB_lower[k]) / ATR[k]   // ATR-normalized width; ATR[k]>0

SqueezePre :=
    ATR[2] > 0 AND ATR[1] > 0
AND Count_{j=3..34}(ATR[j] <= ATR[2]) <= 8
AND BB_width[2] <= 0.85 * Median(BB_width[3], ..., BB_width[22])
AND ADX[2] <= 28
AND BB_upper[2] > BB_lower[2]

Long_009 :=
    SqueezePre
AND C[1] > BB_upper[1] + 0.05 * ATR[1]
AND Bull[1]
AND C[1] > EMA34[1]
AND C[1] > C[2]
AND not (ADX[1] >= 35)   // reject already vertical expansion maturity
AND Body[1] >= 0.50 * Range[1]

Short_009 :=
    SqueezePre
AND C[1] < BB_lower[1] - 0.05 * ATR[1]
AND Bear[1]
AND C[1] < EMA34[1]
AND C[1] < C[2]
AND not (ADX[1] >= 35)
AND Body[1] >= 0.50 * Range[1]
```

**Material non-overlap:**

- vs 007: 009 **requires** documented multi-bar compression pre-state; 007 does not.
- vs 007: 009 break reference is **BB envelope**, not Donchian-20 high/low.
- vs 008: 009 is expansion-from-coil, not pivot reclaim in trend.

### 5.4 Invalidation

Single-bar consumable signal. If break close occurs without `SqueezePre`, no entry (no
“breakout without squeeze” branch on this ID).

### 5.5 Adversarial prior

- BB squeeze breakouts are heavily arbitraged; false breaks in XAU Asia/London open are common
  (session filter remains shared 08–17 UTC — **not** a post-hoc hour veto of 006).
- Bottom-quartile ATR definition may be regime-sensitive across 2018–2026 vol eras.
- Cap ADX[1]&lt;35 may delete the best expansions.

### 5.6 Kill gates specific to 009

1. If median `BB_width[2]` of entries is not below the median of all bars’ width (probe
   diagnostic) → compression claim fails.
2. If ≥50% of trades reverse through opposite band within 5 bars and PF&lt;1 → false-break
   object; no “wait second close” rescue on same ID.
3. Cadence &lt; 1.0/week with N too small for PF inference → park density failure (not economic
   promotion of rare winners).

### 5.7 Decision-time telemetry (009)

- BB upper/mid/lower [1], [2]; BB_width[2]; median width ref  
- ATR rank count; ADX[1], ADX[2]; EMA34[1]  
- squeeze and break subgates PASS/FAIL  

---

## 6. HYP-MZMS-XAU-M5-010 — Exhaustion / rejection mean reversion  
### `InpSignalMode = 5` · `SIGNAL_EXHAUST_REJECT`

### 6.1 Causal thesis

A subset of XAU M5 extensions ends in **liquidity-grab style rejection**: elongated wick
against a short-horizon run, oscillator extreme, and **ADX rolling over** (strength no longer
increasing). The edge hypothesis is **fade the exhaustion bar**, opposite in economic intent
to HYP-006’s continuation-after-extremum design.

This is deliberately the adversarial complement: if gold M5 microstructure is mean-reverting
at exhaustion, 010 can live while 007–009 die — or vice versa.

### 6.2 Indicators and fixed parameters

| Name | Spec | Role |
|---|---|---|
| RSI | 14 | Extreme |
| ATR | 14 | Extension + stop |
| ADX | 14 | Roll-over / non-acceleration |
| EMA | 50 close | Location of extension vs mean |
| Run length | closed directional closes | Extension context |
| Wick fraction | OHLC | Rejection anatomy |

Fixed thresholds:

| Symbol | Value | Meaning |
|---|---:|---|
| `RSI_hi` | 70 | Overbought extreme |
| `RSI_lo` | 30 | Oversold extreme |
| `Wick_frac` | 0.55 | Dominant rejection wick |
| `Ext_ATR` | 1.20 | Distance of wick extreme from EMA50 |
| `Run_bars` | 3 | Minimum prior directional closes |
| `ADX_roll` | `ADX[1] < ADX[2]` | Strength no longer rising |
| `ADX_floor` | 14 | Some structure existed |
| `Close_reclaim` | close back inside prior bar range | Rejection confirmation |

### 6.3 Exact shift-indexed entry rules

**Short (fade upside exhaustion):**

```text
RunUp :=
    Bull[2] AND Bull[3] AND Bull[4]   // three prior bullish closes (shifts 2..4)

ExtUp :=
    H[1] >= EMA50[1] + 1.20 * ATR[1]
AND RSI[1] >= 70
AND RSI[1] >= RSI[2]

RejectUp :=
    Range[1] > 0
AND (H[1] - MathMax(O[1], C[1])) >= 0.55 * Range[1]   // upper wick dominance
AND C[1] < H[2]                                      // close back through prior high area
AND C[1] <= O[1]                                     // not a strong bull close (bear or doji-down)
AND ADX[1] >= 14
AND ADX[1] < ADX[2]
AND C[1] > EMA50[1] - 0.30 * ATR[1]                  // still extended region; not already collapsed

Short_010 := RunUp AND ExtUp AND RejectUp
```

**Long (fade downside exhaustion):**

```text
RunDown :=
    Bear[2] AND Bear[3] AND Bear[4]

ExtDown :=
    L[1] <= EMA50[1] - 1.20 * ATR[1]
AND RSI[1] <= 30
AND RSI[1] <= RSI[2]

RejectDown :=
    Range[1] > 0
AND (MathMin(O[1], C[1]) - L[1]) >= 0.55 * Range[1]  // lower wick dominance
AND C[1] > L[2]
AND C[1] >= O[1]
AND ADX[1] >= 14
AND ADX[1] < ADX[2]
AND C[1] < EMA50[1] + 0.30 * ATR[1]

Long_010 := RunDown AND ExtDown AND RejectDown
```

**Material non-overlap with HYP-006 and 007–009:**

- No MACD histogram local extremum; RSI is **extreme**, not 42–58 mid-band continuation.
- ADX must be **falling**, opposite of 007’s rising ADX initiation.
- Economic direction **fades** the prior run; 007/009 trade **with** the break.

### 6.4 Stop geometry note (still shared shell)

Stops still use shared farther-of structural/ATR rule. For forensics, expected structural
anchor is the rejection wick extreme (`H[1]` for short, `L[1]` for long) which typically
binds the 5-bar structural stop — this is a consequence of geometry, not a special BE rule.

### 6.5 Adversarial prior

- Mean-reversion fades on XAU during macro impulse days are toxic; ADX roll may lag.
- Wick rules are sensitive to spread/spikes in Model 0.
- Workspace MR families (EURUSD H1) died; this is a different TF/symbol/object but prior is
  adverse for generic MR.
- Cadence may be sparse; sparse + lucky PF is not promotion.

### 6.6 Kill gates specific to 010

1. If median MFE &lt; 0.4R and median MAE &gt; 0.8R with PF&lt;1 → no reversion impulse.
2. If RSI extremes without wick dominance (ablation) match the trade set → wick claim fails.
3. If all positive expectancy concentrates in one calendar year → concentration kill.

### 6.7 Decision-time telemetry (010)

- RSI[1], RSI[2]; upper/lower wick fractions; EMA50 distance in ATR  
- run flags; ADX[1] vs ADX[2]; all subgates  

---

## 7. Cross-mode comparison matrix (non-overlap checklist)

| Dimension | 007 Impulse | 008 Pullback reclaim | 009 Squeeze break | 010 Exhaust fade |
|---|---|---|---|---|
| Primary event | Donchian-20 break | Pivot reclaim after EMA pull | BB break after compression | Rejection wick after run |
| Vol state | Expanding ATR | Normal | Compressed pre-break | Extended location |
| ADX posture | Rising, mid band | ≥20 trend | Cap pre-break; reject extreme | Falling |
| RSI role | None | None | None | Extreme 70/30 |
| MACD role | None | None | None | None |
| EMA role | EMA50 side | EMA20 magnet + EMA100 bias | EMA34 tilt | EMA50 extension anchor |
| Intent | Continuation start | Continuation after dip | Expansion from coil | Mean reversion |
| Anti-006 | No hist extremum | No hist extremum | No hist extremum | Opposite intent + RSI extreme |

---

## 8. MQL5 implementation touchpoints (design only; no edit now)

Target file: `03. EA Developer/EA_MZMS_Scalper/EA_MZMS_Scalper.mq5`  
Tests: package suite under `tests/` (currently 18/18 on HYP-006 surface; will need red-first
extensions per mode).

### 8.1 Required code surface changes (future implementation PR)

1. **Expand `ENUM_SIGNAL_MODE`** with values 2..5; keep 0/1 behavior byte-stable unless an
   explicit engineering note says otherwise.
2. **Generalize `ReadIndicator`** to arbitrary `shift >= 1` via `CopyBuffer(..., shift, 1, ...)`.
3. **Add handles** as needed:
   - `iMA` EMA50, EMA20, EMA100, EMA34 (can share one factory helper),
   - `iBands` for mode 4,
   - ADX buffers 1/2 for +DI/−DI (`CopyBuffer` buffer index 1 and 2).
4. **Split `ClosedBarSignal`** into:
   - `ClosedBarSignalControl`
   - `ClosedBarSignalLegacyMzms` (mode 1)
   - `ClosedBarSignalImpulse007`
   - `ClosedBarSignalPullback008`
   - `ClosedBarSignalSqueeze009`
   - `ClosedBarSignalExhaust010`
   - dispatcher by `InpSignalMode`.
5. **Hypothesis id / magic / RunMeta** must switch with mode (no cross-contamination of
   lifecycle identity).
6. **Rejection counters** extended: e.g. `donchian_rejections`, `squeeze_rejections`,
   `pivot_rejections`, `wick_rejections`, etc., for funnel forensics.
7. **Decision-time telemetry exporter** (preferred): CSV/JSONL row at decision with every
   indicator/gate used by the active mode; required for `decision_asof` charts with parity.
8. **Presets**: four `.set` / AlphaFactory override packets, one per mode, sharing risk shell.
9. **Tests (red-first):**
   - shift≥1 only / no shift 0 reads in signal path  
   - each mode: synthetic series fixtures for fire / no-fire boundary  
   - mutual exclusion smoke: bar that is pure 007 break does not satisfy 008 reclaim  
   - BE remains false path  
   - ownership/cooldown unchanged  
   - news guard false path for XAU campaign  
10. **Non-repaint audit** on exact post-change snapshot before any Model 0.

### 8.2 Unchanged on purpose

- Risk sizing `OrderCalcProfit` path  
- Spread gate 35 / buffer 40  
- Session/flatten/cooldown/max day trades  
- BE off, target 1.6R, hold 15, stop lookback 5 / ATR 1.5  
- Tester-only mutation authority  

### 8.3 Recommended magic map

| Mode | Magic |
|---:|---:|
| 2 | 5600727 |
| 3 | 5600728 |
| 4 | 5600729 |
| 5 | 5600730 |

---

## 9. Execution campaign contract (parent-owned; design binding)

After implementation + tests + compile + non-repaint + prereg/registry (all parent-owned):

1. Serial Model-0 runs only: **one run per mode** (4 total), no optimization, no rerun.
2. Window `2018.01.01--2026.07.22`, XAUUSD M5, Model 0, deposit/leverage/risk as §1.1.
3. Pre-run: confirm data source plan for history ≥99%; if cannot, still may run only as
   **explicit diagnostic** with invalid economic authority declared **before** start.
4. Post-run: lifecycle reconcile, validation packet, then chart sampling (§10).
5. Verdict per ID independently; failure of one does not authorize mutating another.

---

## 10. Pre-view 100-position sampling scheme (per variant)

**Freeze this scheme before any chart is opened.** Applies identically to modes 2..5 after
each run’s lifecycle exists.

### 10.1 Population

- Universe = all **final-closed** positions in that mode’s lifecycle with defined initial risk
  (`initial_risk_account > 0` and `|entry-stop| > 0`).
- If `N < 100`, sample **all** positions and label `SAMPLE_DEGENERATE_N_LT_100`; still render
  both image layers for each.

### 10.2 Stratified sample of 100 (when N ≥ 100)

Use a single frozen seed per mode:

```text
seed_mode = SHA256(hypothesis_id + "|" + run_id + "|FORENSICS_SAMPLE_V1")
           interpreted as uint64 (first 8 bytes)
```

Strata (exact counts; if a stratum lacks volume, spill remainder to next underfilled stratum
by this order: Losers → Winners → Matched → Anomalies → Uniform fill):

| Stratum | Count | Definition |
|---|---:|---|
| Winners | 30 | `net_R > 0` ordered by time; systematic sample |
| Losers | 30 | `net_R < 0` ordered by time; systematic sample |
| Matched pairs | 20 (10 pairs) | For 10 winners, nearest-neighbor loser in decision-time feature space (Mahalanobis on z-scored: ADX, ATR, hour UTC, body/ATR, direction); pair IDs frozen |
| Anomalies | 20 | Union of: top 5 \|net_R\| wins, top 5 \|net_R\| losses, top 5 MAE/R, top 5 hold-time extremes (timeout vs &lt;3 bars), dedup then random fill to 20 |

Total unique position IDs = 100 after dedup; if dedup reduces count, refill from remaining
population by `seed_mode` shuffle.

### 10.3 Image contract — two PNGs per case

For each sampled `position_id`:

1. **`decision_asof`** (outcome-blind)
   - M5 candles with **hard cutoff at entry bar** (no future candles, no exit markers, no net R).
   - Every **active** indicator/gate for that mode drawn (see mode sections).
   - Entry triangle + initial SL/TP planned levels only if they are decision-time known.
   - Title: `hypothesis_id | position_id | decision_asof | mode`.
   - Filename: `{position_id}_decision_asof.png`.

2. **`anatomy`** (outcome layer)
   - Same indicator panel + post-entry path through exit.
   - Markers: entry, initial SL, TP, exit, hold bars, net R, MAE/MFE.
   - Filename: `{position_id}_anatomy.png`.

Renderer requirements:

- Hash-bind source SHA, run id, bar timestamps, renderer version, PNG SHA in manifest.
- Prefer decision-time MT5 telemetry parity; if post-run recompute, label
  `RECOMPUTE_NON_AUTHORITATIVE` and keep parity report.
- Contact sheets do not replace per-case images.

### 10.4 Grok review protocol (operational default)

- **5 cases per job**, global backend concurrency **1**.
- Request artifact + dry-run before actual; exact case/position/image-open validation.
- Logical roles: Grok A timing/context/confluence; Grok B adverse path/risk/execution;
  parent owns QC/verdict.
- Optional large 2×100 profile only if population and budget support; not a hard gate for
  every arm.
- Reviewer output **cannot** patch EA rules or authorize rerun/promotion.

### 10.5 Indicator panel checklist per mode

| Mode | Must show on both images |
|---:|---|
| 2 | EMA50, Donchian 20 (pre-bar), ATR, ADX, +DI/−DI, body median ref, entry/SL/TP (anatomy) |
| 3 | EMA20, EMA100, ATR, ADX, +DI/−DI, pivot marker `p*`, depth annotation |
| 4 | BB(20,2), EMA34, ATR, ADX, width/ATR compression annotations |
| 5 | EMA50, RSI14 (30/70), ATR, ADX, wick fraction annotation, run bars highlight |

---

## 11. Offline probe recommendation (cheap, pre-Model 0)

Doctrine prefers cheap offline falsification before ceremony. Recommended **outcome-blind
density probe** on sealed M5 XAU OHLC (if D-shelf data exists) **before** coding:

For each mode, count signals/elapsed-week on 2018–2022 only (2023+ sealed for probe if
desired) with **no** P&amp;L:

| Mode | Density fail if |
|---:|---|
| 2–5 | challenger signals/week outside **1.5–8.0** pre-cost band (wider than trade band; execution will delete some) |
| 2–5 | &lt; 100 total signals in 2018–2022 → likely Model-0 cadence fail |

Probe plans must be SHA-bound if used as kill authority. This design candidate does **not**
itself execute that probe.

---

## 12. Falsification summary (poster)

| ID | Core claim to kill |
|---|---|
| 007 | Fresh Donchian expansion with rising mid-ADX is **not** positive expectancy on XAU M5 after costs |
| 008 | EMA pullback pivot reclaim in trend is **not** positive expectancy |
| 009 | BB/ATR compression→break is **not** positive expectancy |
| 010 | Exhaustion wick fade is **not** positive expectancy |

Shared meta-kill: history &lt; 99% → engineering invalid; do not launder into strategy truth.

---

## 13. Parent next actions (out of scope for this worker)

1. Owner/parent accepts or amends this design candidate (amendments → new file version, not
   silent edit after outcome).
2. Parent writes four preregs + registry rows (or one multi-arm prereg with four IDs) SHA-bound
   **before** source change if build-first exception is not re-granted.
3. Implementation worker codes modes 2..5 only inside write_set authorized later.
4. Red-first tests → compile → non-repaint → four serial Model-0 runs → sampling → Grok
   forensics → per-ID verdict.
5. No live/paper/promotion path from this document.

---

## 14. Document control

| Field | Value |
|---|---|
| Path | `03. EA Developer/EA_MZMS_Scalper/research/HYP-MZMS-XAU-M5-007-010_GROK_DESIGN_CANDIDATE.md` |
| Write scope | This file only |
| Source edited | No |
| Registry edited | No |
| hot.md edited | No |
| Outcomes read | No new outcomes; only prior HYP-006 invalid diagnostics + forensics synthesis as adverse prior |
| Authority granted | Design candidate only |

**End of design candidate.**
