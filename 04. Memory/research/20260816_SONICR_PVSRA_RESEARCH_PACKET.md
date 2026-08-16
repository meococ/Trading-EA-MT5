# Sonic R + PVSRA research packet

Date: 2026-08-16  
Role: researcher worker (read-only public + local; no EA code, no binaries)  
Status: `DONE`  
Audience: parent agent freezing a **new modular** Sonic R implementation.  
Not an edge claim. Not a registry write. Not a revival of killed Dragon-bounce / ITSM 5-13-34-89 pullback.

Claim tags used throughout:

- `public-source` — fetched public text, quoted or tightly paraphrased
- `reconstructed` — common later reconstruction or local parity code; **not** proven original TAH/Kyaw numbers
- `local-empirical` — workspace backtests, probes, audits
- `hypothesis` — trader inference the parent may freeze only after naming it as a design choice
- `owner-drive` — Owner-recovered Drive notes supplied in the task contract; files were **not** re-downloaded here

---

## 0. How to read this packet

Sonic R is a **discretionary chart method** (price-action waves + Dragon + Trend + S/R + PVSRA), not a finished mechanical EA. Public pages describe objects and habits. They do **not** publish a complete, unique entry FSM.

Two contaminations must stay out of the freeze:

1. **Fratelli / ForexStrategiesResources hybrid** (QQE, CCI 63, 50 SMA, Stealth LCD). That page reuses the Sonic R name and EMA34 H/C/L but is a different system. `public-source`
2. **Local killed mappings** that reduced Sonic R to Dragon bounce, Dragon breakout, ITSM EMA-zone pullback, or Hybrid ICT AND-stack. Those are not the original Classic object. `local-empirical`

Owner instruction for this wave: Classic is core; Scout is parked; PVSRA is analysis, not a standalone trigger. `owner-drive`

---

## 1. What Sonic R is (trader mental model)

### 1.1 Origin

Sonic R was founded by Kyaw Trader (Sonicdeejay) in 2008 and discussed on Forex Factory thread `t=114792`. TAH (Traderathome) later shipped the widely used indicator/template stack (Control Panel, Filled Dragon, PVA Candles, PVA Volumes). `public-source`  
[sonicr999.blogspot.com/2014/08/sonic-r-system.html](http://sonicr999.blogspot.com/2014/08/sonic-r-system.html)

The method is **Price action (including Waves) + Volume + S&R + EMA**. It is described as a position/swing method on **M15**, not a 5-pip scalp. `public-source`

### 1.2 One-sentence model

Trade **price movement between support and resistance** when a **WAVE** at S/R is confirmed by the **Dragon** (entry geometry) and the **Trend** (direction bias), then manage toward historic S/R. Use **PVSRA** only to decide whether the price-moving entities are bulls or bears and whether they are **building** or **running**. `public-source`

ForexOnSignal (copy of the same TAH/manual language):

> THE SONIC R. SYSTEM IS A METHOD OF TRADING PRICE MOVEMENTS BETWEEN AREAS OF SUPPORT AND RESISTANCE. It trades on the M15 chart. It uses a price activity WAVE at an S&R area to validate a trade setup, and technical indicators called the DRAGON and the TREND. The DRAGON is used for picking the trade entry. The TREND is used to confirm the correct trade direction. Historic S&R is used for picking the trade exit.

`public-source` [forexonsignal.blogspot.com/p/sonic-r-system.html](http://forexonsignal.blogspot.com/p/sonic-r-system.html)

### 1.3 What it is not

- Not “buy the EMA34 channel.” Dragon is a visual value/volatility band for **where** a wave may break, not a bounce oracle. `public-source` + `local-empirical` (S360)
- Not “trade every PVA color.” PVA colors mark **notable volume**. They do not say long or short by themselves. `public-source`
- Not ICT kill-zone + FVG + OB. Later Hybrid ICT-Sonic is a different family and is locally killed. `local-empirical`
- Not ITSM 5/13/34/89 zone pullback. That is a later mechanical reduction. `local-empirical`

### 1.4 Operating rules that are actually written

From Kyaw / TAH public recaps (`public-source`: sonicr999, sgtradingcourses, th3-pro-forex):

1. Do not overtrade. Do not trade the **Asian session**. Best follow-through is **after London opens**. Quality over quantity; “shouldn’t trade more than 5 trades a week.”
2. **Do not add to a losing position.** Scout + PVSRA create that temptation; TAH still forbids it.
3. Stops must be **wide enough to breathe**. Tight stops get tagged even when the idea is right. Public EURUSD example: SL up to **100 pips**, and Classic SL “not more than 100–120 pips from EP.”
4. Higher-timeframe context, lower-timeframe entry (seminar notes). `public-source`

These are **risk/cadence doctrine**, not a signal formula.

---

## 2. Core objects

### 2.1 Dragon

**Definition (public + owner):** Dragon = **EMA 34 of High, Close, and Low**. The band (high–low) is the “body” of the Dragon; close EMA is the mid. TAH’s 2013/2014 stack calls this **Filled Dragon** and includes Trend in the same indicator. `public-source` + `owner-drive`

**How traders use it:**

- Longs: Dragon **angled up**, price action **above** it. `public-source` (th3-pro-forex brief manual)
- Shorts: Dragon **angled down**, price action **below** it. `public-source`
- Classic entry is **not** a mid-band bounce. Entry waits for **WAVE leg #3 to break out of the Dragon**. `public-source`
- “Best if WAVE leg #1 crosses thru the Dragon.” `public-source`

**What is not specified publicly:** slope lookback, minimum angle, ATR-normalized expansion, or whether “break out” is close-beyond vs wick-beyond. Those are `reconstructed` if frozen.

**Local reconstructions (do not treat as original):**

- `EA_SonicR` telemetry: Dragon flat / compressed / expanding / angled from slope and band-width / ATR. `reconstructed`
- `EA_HybridICT_Sonic`: trigger = close beyond outer band **or** mid reclaim. Mid-reclaim is a Hybrid invention, not Classic. `reconstructed` + `local-empirical`
- S360 treated Dragon as a bounce/breakout channel. Failed. `local-empirical`

### 2.2 Trend

**Definition:** Trend = **EMA 89 of close**. `owner-drive` (README-SONIC R.md). Public brief manuals say Trend is a **market-bias** line: “best if PA is above it for longs, below it for shorts.” `public-source`

TAH “Filled Dragon” “still includes the Trend.” `public-source` (sonicr999 2013 upgrade notes)

**Not original Sonic R:** stacking EMA 5 / 13 / 34 / 89 as a “zone” to fade (ITSM). `reconstructed` + `local-empirical`

**Soft vs hard:** public language is “best if,” not “must.” Freezing Trend as a hard AND-gate is a `hypothesis` that previously starved cadence when stacked with other filters. `local-empirical`

### 2.3 Waves

**Public Classic wave (`public-source`, th3-pro-forex “latest Sonic R System Manual in brief”):**

| Side | Pattern | Start location | Quality hint |
|---|---|---|---|
| Long | **L – H – HL** | starting **below** Dragon | bounce or breakthrough at S/R; best if leg #1 crosses through Dragon |
| Short | **H – L – LH** | starting **above** Dragon | same |

Entry clock: wait for **WAVE leg #3 candle to break out of the Dragon**. Place the order **at least several pips beyond** that candle. Prefer no strong S/R immediately beyond the entry. `public-source`

Seminar notes (sgtradingcourses) add a looser Classic list: wave = HH/HL; Dragon EMA34 H/L/C; “high volume at the recent low.” `public-source` — less precise than the L-H-HL / H-L-LH brief.

**Not specified publicly:** pivot strength, minimum leg length, maximum overlap, whether HL must be inside/outside Dragon, or whether leg #3 must be a single closed bar.

**Local reconstructions (do not copy as “source-true”):**

- HybridICT `WaveConfirmLong/Short`: last two swing highs/lows with `InpSwingStrength=2`. Approximate HH/HL only; does **not** require start-below-Dragon or a numbered three-leg path. `reconstructed`
- `EA_SonicR` `source_classic_wave_state`: smoothness from same-side close ratio over 15 bars + 5-bar net range. A **quality proxy**, not a wave parser. `reconstructed`  
  Probe `20260509_235117` / `20260510_000400`: fired trades were `trap_risk` 16 / net −796.74 and `clean_classic_unconfirmed` 2 / net −100.36; `clean_classic_run` = 0. Labels were unsafe as vetoes. `local-empirical`

### 2.4 S/R — whole / half / quarter

**Public PVSRA S/R hierarchy (`public-source`, TAH text on sonicr999 and forexonsignal):**

1. **Whole numbers** first
2. **Half numbers** next
3. **1/4 and 3/4** last
4. Plus **historic swing / consolidation** S/R

TP is chosen at a historic S/R, including whole/half/quarter and the **middle of consolidation**. `public-source`

**Location gap (PVSRA-002):** public text never defines the pip grid (100-pip whole? 00/50/25 on the quote?). Local `EA_SonicR` uses `whole_step = 100 * pip_size`, half = ±50 pips, quarter = ±25/75 pips. That is a **EURUSD-style reconstruction**. It is wrong as a universal XAUUSD map (gold “big figures” are not 100 pips of a 5-digit FX pair). `reconstructed` + `owner-drive` (PVSRA-002)

**Runway:** public rule is qualitative — “better if there is no strong S/R just beyond the entry.” Local `source_sr_runway_pips` is a reconstructed distance feature, previously used as a decision gate and parked. `reconstructed` + `local-empirical`

### 2.5 PVSRA / PVA

**Name:** Price, Volume, Support, Resistance Analysis. Indicators: **PVA Candles** (replaced VSA Candlesticks) and **PVA Volumes** (replaced VSA Histogram). `public-source`

**Volume definition in TAH’s own text:** “Volume (count of trades on the broker server).” That is **broker tick volume**, not exchange real volume. `public-source`

**Colors:** bull/bear coloring for **rising** volume; **climax** coloring on **extreme rising** volume. Exact thresholds are **not** in the public TAH essays. `public-source`

See §4.

### 2.6 Sessions / “kill zones”

**Original written rule:** do **not** trade Asia; **prefer London open and after**. Trades may be closed anytime. EURUSD preferred because of spread, range, and “better volume.” `public-source`

**Not original wording:** “London/NY kill zone” as a fixed hour box. That phrase is later retail/ICT language glued onto Sonic. `reconstructed`

**Later reconstructions (do not freeze as original):**

| Source | Window | Tag |
|---|---|---|
| FSR Fratelli page | 01:00–04:00 EST “UK”, 07:00–11:00 EST “US” | contaminated hybrid, not Sonic R |
| ITSM / S506+ | London h9–12 + NY h15–18 (broker/server hours) | reconstructed KZ + killed family |
| HybridICT | 07:00–20:00 UTC wall | reconstructed session box |
| Owner README | run-for-profits vs position-building more important than a clock | owner-drive |

**Hypothesis for a modular EA:** Asia hard-off is the only session rule that is public-source. London-preferred is public-source. NY continuation is optional and must be a **named design choice**, not smuggled in as “Sonic kill zone.”

---

## 3. Setups: Classic, Re-entry, Scout

### 3.1 Classic (core — the only setup Owner wants automated first)

**Mental picture:** a three-leg wave forms at S/R. Leg 1 often crosses the Dragon. Legs 2–3 create HL (long) or LH (short). Leg 3 **breaks out of the Dragon** in the Trend direction. Buy/sell **beyond** that candle, not inside the band.

| Item | Public rule | Tag | Freeze note |
|---|---|---|---|
| Chart | M15 | public-source | Decision TF. M5 may refine fill only if the **signal bar is a completed M15**. |
| Wave long | L-H-HL starting below Dragon | public-source | Needs a frozen swing definition (see §6). |
| Wave short | H-L-LH starting above Dragon | public-source | Mirror. |
| Dragon | Angled with PA on the correct side | public-source | Slope/angle = reconstructed. |
| Trend | PA above Trend for longs / below for shorts (“best if”) | public-source | Soft bias unless parent hardens it. |
| S/R context | Wave at S/R; bounce or breakthrough | public-source | WHQ + swing S/R. Location grid = reconstructed. |
| Trigger | Wave **leg #3** candle breaks out of Dragon | public-source | Close-beyond outer EMA34 is the conservative closed-bar reading. Wick-beyond is looser (`hypothesis`). |
| Entry | Pending **several pips beyond** the signal candle | public-source | Offset is pair-specific; do not copy 5–7 pips from the Fratelli page. |
| Invalidation / SL | Beyond H/L of the recent **large-scale** swing; EURUSD cap 100–120 pips | public-source | “Large-scale” is discretionary. Cap does not port to XAU. |
| TP | Historic S/R (WHQ or mid-consolidation) | public-source | Not a fixed R-multiple in the original method. |
| Add rule | Never add to a loser | public-source | Hard. |
| Cadence doctrine | ≤5 trades/week, quality | public-source | Scanner/risk cap, not a PF proof. |

Seminar-only extras (sgtradingcourses): Classic also listed “high volume at the recent low”; Scout SL “near last swing or not more than 100 pips”; Classic SL “no SL but not more than 250 pips for EURJPY” and “until strong opposite candle on weekly TE.” Those conflict with the 100–120 pip EURUSD brief. Treat seminar SL as **informal / pair-specific**, not a second law. `public-source` (conflict)

### 3.2 Re-entry

After a Classic is already on:

> It is best to let PA clear the most recent high, or low, and if there is no strong S/R area just beyond this re-entry.

`public-source` (forexonsignal, th3-pro-forex, sonicr999)

Seminar: “Re-enter after a bullish candle for long Classic.” SL near last swing or ≤100 pips. `public-source`

**Constraints:**

- Re-entry is **add-on after a working Classic**, not a first entry.
- TAH: **do not add to a loser**, even if PVSRA looks good. `public-source`
- Therefore a modular EA may have a Re-entry **scanner**, but execution should require: parent Classic in profit (or at least not underwater), new HL/LH, clear of prior extreme, runway beyond. That last clause is `hypothesis`.

**Do not automate first.** Owner: Classic is core. `owner-drive`

### 3.3 Scout (parked)

TAH:

> There are at times early in a price reversal that a Classic setup has not yet formed but price action alone suggests an entry opportunity. Such an early entry to a reversal is called a “Scout” entry, and two examples of pure price action that support a Scout entry are: 1) a suitable pattern of H/Ls, and 2) a break out from a consolidation area.

`public-source` (sonicr999)

Least-risk use: determine bull/bear via PVSRA, then take Classics **and** Scouts only in that direction. `public-source`

Seminar “Sonic Entry” is even vaguer: “high stopping volume” + “enter a strong candle of intended direction.” `public-source`

**Owner: Scout parked.** `owner-drive`

Scout is **not** Model-0 material. “Suitable pattern of H/Ls” and “consolidation break” have no public quantitative test. Any automation would be a new, named discretionary-proxy family — and would collide with already-killed range-break / Asian-manip / CONTEXT_FAIL work. `local-empirical`

### 3.4 Management (as sources allow)

Public management is **structural**, not R-multiple:

- SL beyond the large swing, with a pair pip cap.
- TP at the next historic S/R.
- Wide enough to breathe; do not scalp the stop.
- Do not average losers.
- Prefer not to open in Asia.

No public rule for break-even, trailing, partials, or time-stop. Those are `hypothesis` if added. Local EAs that bolted BE@50 pips, RR 1.2–2.5, or Dragon±40 pip floors **changed the method** and mostly died on cadence or economics. `local-empirical`

---

## 4. PVSRA deep dive

### 4.1 What TAH actually wrote

Quoted from the 2013/2014 TAH notes republished on sonicr999 and forexonsignal (`public-source`):

- **Price** = individual candle shape **and** the flow of PA.
- **Volume** = notable increase vs **immediately preceding** volumes (broker trade count).
- **S/R** = WHQ first, then swing S/R.
- **Habit of price-moving entities:**
  - Bulls like to **buy below** key S/R.
  - Bears like to **sell above** key S/R.
- Therefore: locate **where** (above vs below key S/R) most of the **notable** volume is printing → infer bull or bear.
- Then ask **mode**:
  - **Position building:** bulls buying below S/R while **price is still generally falling**; bears selling above S/R while **price is still generally rising**.
  - **Run for profits:** bulls still buying below S/R **on pullbacks** while **price is generally rising**; bears still selling above S/R on pullbacks while **price is generally falling**.
- **Trade the run, not the build.** You cannot know when building ends. Waiting for the run is how you avoid getting trapped.
- PVA colors “denote when notable increases in volume occur to **help you conduct** PVSRA.” They are **not** the trade.

This is **analysis**. Owner restates the same: PVSRA is not a standalone entry. `owner-drive`

### 4.2 Volume classes — public vs reconstructed

| Class | Public TAH words | Common reconstruction | Tag |
|---|---|---|---|
| Normal | (implied: not notable) | volume < 150% of prior-10 average | reconstructed |
| Rising / “volume rising above average” | “bull/bear coloring for rising volume” | volume ≥ **150%** of average of **previous 10** bars | reconstructed |
| Climax / extreme rising | “climax coloring to extreme rising volume”; VSA Histogram had a “Climax” alert | volume ≥ **200%** of prior-10 average **OR** `spread × volume` ≥ max of that product over prior 10 | reconstructed |

**Do not invent these as original TAH numbers.** The 2013 public notes say only “notable” and “extreme.” Exact 1.5× / 2.0× / 10-bar / spread×volume rules appear in later public **reconstructions** of the PVA/PVSRA candle logic:

- Traders Reality Main (TradingView, open-source, cites the MT4 suite): Green/Red = vol ≥ 200% of last-10 average **or** spread×vol highest of last 10; Blue/Violet = vol ≥ 150% of last-10 average. `reconstructed` (widely cloned)  
  [tradingview.com/script/Etj1ixAs-Traders-Reality-Main](https://www.tradingview.com/script/Etj1ixAs-Traders-Reality-Main/)
- Same 150/200/10-bar wording on later TV clones (SNIPERS CANDLES, Compass, HTF PVSRA, FTB). `reconstructed`
- Local `SNR_CalcSourcePvaParity`: `rising_150 = vol >= avg_10 * 1.50`; `climax_200_or_highest_sv = vol >= avg_10 * 2.00 OR spread_volume >= max prior-10`. Matches the Traders Reality reconstruction. Flagged in-code as “Source-auth PVA 10-bar rising/climax parity” and **default-off**. `reconstructed`
- Local `candidate_pva_*` uses a **20-bar** average instead of 10. That is a second, weaker reconstruction. `reconstructed`
- HybridICT `PvsraClimax`: `tick_volume[0] >= avg_20 * 1.5` (default). Mixes rising threshold with climax name and 20-bar window. **Do not reuse.** `reconstructed` + `local-empirical`

**Owner provenance memo:** climax/rising thresholds are **not exact** in public doctrine (PVSRA-003 sibling gap). `owner-drive`

### 4.3 Effort / result

Public TAH does **not** use Wyckoff “effort vs result” as a formula. The closest public idea is: notable volume **located** above or below S/R, read against whether price is generally rising or falling. `public-source`

A mechanical `high volume + small range = absorption` or `high volume + large range = climax trend` rule is **Wyckoff/VSA reconstruction**, not a published Sonic number. `hypothesis`

Local Hybrid/Sonic “tick climax AND-gate” treated volume as a **yes/no trigger**. That is the opposite of TAH’s use. It also used broker tick volume as if it were participation. `local-empirical`

### 4.4 Activity above / below S/R

This is the actual PVSRA question, and it is **the hard part**:

1. Mark key S/R (WHQ + swings).
2. On bars with **rising or climax** PVA, ask whether the **trade activity** occurred above or below that S/R.
3. Aggregate recent notable bars → bull or bear **bias**.
4. Compare that bias to the **slope of price** → build vs run.

Public text never says: use the candle close, the wick, the body, or a volume-at-price profile. Retail FX has **no public volume-at-price** on MT5 tick volume. So “where they are doing most of their trading” is **visual**: did the high-volume bar’s range sit mostly above or below the level?

**PVSRA-002 (S/R location gap)** remains open: without a frozen level definition, “above/below” is not computable. `owner-drive`

Any EA field that scores `pva_below_sr` from “low wick crossed a 100-pip whole” is a **proxy**, not TAH. `reconstructed`

### 4.5 Build vs run (PVSRA-003)

Public 2×2 (`public-source`):

| Entities | Price generally | Notable activity location | Mode |
|---|---|---|---|
| Bulls | Falling | Below S/R and other lows | **Build** (buying inventory) |
| Bulls | Rising | Below S/R on pullbacks | **Run** (trade longs) |
| Bears | Rising | Above S/R and other highs | **Build** |
| Bears | Falling | Above S/R on pullbacks | **Run** |

Unresolved for automation (`owner-drive` PVSRA-003 + this fetch):

- How many bars define “generally rising/falling”?
- How to weight climax vs rising?
- What if both sides print climax at the same WHQ?
- Tick volume on FX/CFD is quote activity; it can spike on spread widening without “entities buying below.” `local-empirical` (STRATEGY_LOG already recorded tick-volume-as-profile failure on CFDs)

**Rule for the new modules:** PVSRA outputs `bias ∈ {bull, bear, unknown}` and `mode ∈ {build, run, unknown}`. **Never** `{long, short}` as an order. Classic may **optionally** refuse `mode=build` or `bias` conflict as a **soft scanner flag**, not as the first Model-0 hard gate.

### 4.6 Data contract (mandatory if PVSRA is coded at all)

- Native MT5 `tick_volume` is the only honest public Sonic volume. TAH said “count of trades on the broker server.” `public-source`
- It is **not** exchange volume, aggressor flow, or real volume. FivePercent `tick_volume` is quote-update activity. `local-empirical` (20260812 Classic pre-source design)
- `real_volume` on FX symbols is usually 0. Fail closed if a module claims real volume and the series is empty. `hypothesis` / engineering
- Do not import crypto INDEX:BTCUSD override tricks from Traders Reality into XAU/FX. That is a different market. `reconstructed`

---

## 5. What is automatable vs discretionary

| Object | Automatable now (closed-bar) | Scanner / discretionary only | Why |
|---|---|---|---|
| Dragon EMA34 H/C/L | Yes | — | Unique public definition. |
| Trend EMA89 close | Yes | — | Unique public definition. |
| WHQ levels (pair-specific grid) | Yes, **if** the grid is frozen per symbol | Which level is “the” S/R of the wave | Grid is reconstructed; choice of level is visual. |
| Swing S/R / mid-consolidation | Weak proxy | Yes | “Middle of consolidation” is discretionary. |
| Wave L-H-HL / H-L-LH | Partial, with frozen pivots | Wave *quality*, “at S/R”, “leg 1 through Dragon” | Public pattern exists; quality does not. |
| Classic trigger (leg 3 close beyond Dragon) | Yes | Whether S/R sits just beyond EP | Trigger is the most mechanical public rule. |
| Pending several pips beyond signal | Yes, frozen offset + stops level | Exact “several” | Offset is a design input. |
| SL beyond large swing + pip cap | Partial | What is “large-scale” | Need a frozen swing rank or ATR cap **as a named proxy**. |
| TP at next WHQ | Yes as first structural target | Skipping a nearby WHQ / aiming at mid-range | Discretion. |
| Session: Asia off | Yes | — | Public. |
| Session: London preferred | Yes as a window | NY as equivalent KZ | NY box is reconstructed. |
| PVA 150/200 colors | Yes as **labels** | Using color as entry | Reconstruction + not a trigger. |
| PVSRA bull/bear + build/run | Labels only | The actual read | PVSRA-002/003 open. |
| Re-entry | Scanner | Execution | Requires live parent trade + “clear of recent H/L.” |
| Scout | No | Parked | Public examples are non-unique. |
| “≤5 trades/week” | Risk cap | Which 5 | Discretionary selection. |
| Multi-TF “weekly TE opposite candle” | — | Yes | Seminar-only, undefined. |

**Hard recommendation:** automate **one** object — Classic trigger geometry + risk box. Keep PVSRA, Scout, Re-entry, and wave-quality as **telemetry / chart scanner**. That matches TAH, Owner README, and the local failure ledger.

---

## 6. Frozen Classic module spec (for parent to implement later)

This is a **research freeze**, not an authorized hypothesis ID and not a compile order.

### 6.1 Identity

- **Module name:** `ClassicWaveLeg3DragonBreak`
- **Family:** new modular Sonic R (not `EA_SonicR` archive routes, not ITSM, not HybridICT, not Grok v10)
- **Mechanism (one only):** completed M15 three-leg wave at reconstructed WHQ/swing S/R, Trend-aligned, **leg-3 close breaks the Dragon**, pending stop beyond the signal extreme
- **Not in this module:** Scout, Re-entry adds, PVSRA hard gate, EMA 5-13-34-89 pullback, Dragon mid-reclaim, H4 FVG/OB/BOS, ADX/MACD/RSI, hour-mined NY box

### 6.2 Decision clock

- Symbol first cell: **EURUSD** (public preferred pair). XAUUSD only after the EURUSD object is specified with a **different** WHQ/SL scale. `public-source` + `hypothesis`
- Signal TF: **M15**
- All Dragon / Trend / wave / WHQ / volume labels from **closed bars, `shift >= 1`**
- Bar 0 is a **new-bar clock only**
- Act no earlier than first tick of `t+1` after signal bar `t` closes
- Fail closed if `CopyRates` / `CopyBuffer` short, spread missing, or HTF/M15 misaligned
- No fail-open “true if buffer empty” (Grok v10 defect). `local-empirical`

### 6.3 Fields (closed-bar)

```
dragon_high[t]   = EMA34(high)   shift>=1
dragon_mid[t]    = EMA34(close)  shift>=1
dragon_low[t]    = EMA34(low)    shift>=1
trend[t]         = EMA89(close)  shift>=1
atr14[t]         = Wilder ATR14  shift>=1   # risk geometry only
```

Wave (reconstructed parser — must be named as such):

- Swing high/low: closed fractal, **strength = 2** M15 bars each side (same numeric default as Hybrid, **different use**: here it must number three legs, not merely “HH and HL exist”). `reconstructed`
- Long candidate: oldest-to-newest **Low0, High1, HigherLow2** with Low0 **below** `dragon_low` at that time (or Low0 wick through Dragon — parent must pick one; recommend **Low0 low < dragon_low[Low0]**).
- Short: mirror **High0, Low1, LowerHigh2** with High0 **above** `dragon_high`.
- Optional quality flag (not a hard gate in Model-0): leg 1 crosses through Dragon (`public-source` “best if”).
- Trigger bar `t` **is** the closed bar that **completes or extends leg 3** and **closes beyond** the Dragon outer band:
  - Long: `close[t] > dragon_high[t]` and `close[t] > open[t]`
  - Short: `close[t] < dragon_low[t]` and `close[t] < open[t]`
- Trend soft-bias (Model-0 **on**, because public “best if” and it is cheap):
  - Long: `close[t] > trend[t]` and `dragon_mid[t] >= dragon_mid[t-3]` (angle proxy)
  - Short: mirror  
  Angle lookback 3 is `reconstructed`. Do not add EMA144/169 (that was the rejected 2026-08-12 draft).

S/R context (telemetry + one cheap hard filter):

- EURUSD WHQ grid: whole = 100 pips, half = 50, quarter = 25/75. `reconstructed`
- `sr_near_beyond` = a WHQ sits within `k` pips **beyond** the pending price in the trade direction. Model-0: **log it; do not hard-veto** until a source-count shows cadence still lives. Public rule is “better if,” not “must not.”
- Wave “at S/R”: at least one of Low0/High0 (the start of the wave) is within `w` pips of a WHQ or a swing level. Freeze `w` a priori (suggestion: `0.25 * ATR14` or 8 pips on EURUSD). `reconstructed`

PVSRA (labels only):

- `pva_rising` / `pva_climax` using the **10-bar 150/200 + spread×vol** reconstruction, computed on **closed** `tick_volume`. `reconstructed`
- Do **not** require PVA on bar `t` for Model-0. Public Classic does not require it; seminar “high volume at recent low” is a quality hint.

### 6.4 Entry / invalidation / management (Model-0)

- **Entry:** stop order at `signal_extreme ± offset`. EURUSD offset freeze suggestion: **3 pips** beyond high (long) / low (short) of bar `t`, plus broker stop-level. “Several pips” is public; 3 is `reconstructed`. Do **not** use Fratelli 5–7 pips + 50 SMA stop.
- **Cancel:** if not filled by close of `t+4` (4 M15 bars). `hypothesis` (TTL not public)
- **SL:** beyond the wave’s **leg-1 extreme** (Low0 for long / High0 for short) minus/plus `0.10 * ATR14`. Cap: **120 pips** on EURUSD (public cap). If computed SL > cap, **skip** (fail closed) — do not shrink the stop. `public-source` + `reconstructed` buffer
- **TP:** first WHQ at least `min_runway` pips beyond entry (suggestion 15 pips) **or** 1.5R if no WHQ exists in range. Dual target is `hypothesis`; prefer WHQ-only for method fidelity and skip if runway < min.
- **No** BE, trail, partial, pyramid, Scout, or add-to-loser.
- **Session:** trade only if signal bar `t` open is inside **London** (freeze one TZ: Europe/London 08:00–16:00, DST-aware). Asia veto implicit. NY not in Model-0. `public-source` + `reconstructed` clock
- **One position.** Max 5 new signals/week as a **cap**, not a target. `public-source`
- **Friday/weekend:** flatten before weekend (workspace invariant; not original Sonic). `local-empirical` / repo rule
- **Cost:** broker spread + commission + slippage from AlphaFactory; no zero-commission fantasy.

### 6.5 Inputs (minimal)

| Input | Default | Notes |
|---|---|---|
| `InpEnabled` | true | |
| `InpMagic` | new | Do not reuse Hybrid/archive magics |
| `InpDragonPeriod` | 34 | Frozen |
| `InpTrendPeriod` | 89 | Frozen |
| `InpSwingStrength` | 2 | Reconstructed; do not sweep |
| `InpAngleLookback` | 3 | Reconstructed |
| `InpOffsetPips` | 3.0 | EURUSD |
| `InpPendingTtlBars` | 4 | |
| `InpSlAtrBuffer` | 0.10 | |
| `InpSlCapPips` | 120 | EURUSD only |
| `InpMinTpRunwayPips` | 15 | |
| `InpSessionTZ` | Europe/London | |
| `InpSessionStart` | 08:00 | |
| `InpSessionEnd` | 16:00 | |
| `InpUseTrendBias` | true | Soft public “best if” |
| `InpUsePvaLabel` | true | Telemetry only |
| `InpRequirePva` | **false** | Hard rule of this freeze |
| `InpUseScout` | **false** | Parked |
| `InpUseReentry` | **false** | Later module |
| `InpMaxTradesPerWeek` | 5 | Doctrine cap |

Forbidden inputs on this module: ADX, MACD, RSI, H4 FVG, Dragon SL floor ±40, EMA5/13, chase cooldown copied from Grok v10, 20-bar climax-as-entry.

### 6.6 Fail-closed list

- Any series read at shift 0 for a decision value
- HTF/M15 copy failure → no trade (not “allow”)
- `atr14 <= 0`, empty tick_volume if PVA label is on
- SL would exceed cap or sit **inside** the signal bar
- Spread > frozen max (set from broker evidence before run, not from a hope)
- Conflict long+short on same bar
- Existing position or pending
- Off-session, Friday flatten window, kill switch
- Reusing archive `InpUseAutoSleeveConfig` / missing `SNR_FX_EVENTS.csv` path — **do not attach the old host**

### 6.7 What this spec deliberately is not

It is **not** the 2026-08-12 `Dragon/Trend/PVA pullback-break` draft (rejected pre-source). That object required PVA on the trigger, EMA144/169 stack, and a pullback-into-Dragon story. Original Classic is **wave-at-S/R then leg-3 Dragon break**, PVA optional. `public-source` vs `reconstructed`

---

## 7. Known local failures — do not copy

Radius is the **tested object**, not “all Sonic forever.” Owner has ordered a **new modular** method implementation; that is allowed only if the information object is the **public Classic**, not a retune of the rows below.

### 7.1 S360 — Dragon bounce / breakout (`EA_SonicR` v1.1)

- Object: M15 Dragon channel bounce/breakout with Trend, London/NY. `local-empirical`
- Best EURUSD bounce PF **0.98**; breakout **0.58**; USDJPY **0.27**; GBPUSD **0.45**; XAU almost no trades.
- Lesson: Dragon proximity does **not** predict next bar. Channel is a visual aid.
- **Do not revive** bounce/breakout-without-wave.

### 7.2 ITSM — EMA 5/13/34/89 zone pullback

- S506–S508: GBP/EUR/XAU fail (PF 0.62–0.99). `local-empirical`
- S509/S510–S543: USDJPY-only selected children looked better after confluence sweeps; 2026-08-12 revival audit = **`KILL_NO_REVIVAL`**. Unselected 2021–2025 siblings PF 1.12–1.22 **before** real commission; T10/skip-H17 is post-sweep, under-cadence, decaying. `local-empirical`  
  `04. Memory/research/20260812_ITSM_SONIC_USDJPY_REVIVAL_AUDIT.md`
- S701/S702: same mechanism dead on EURUSD (PF 0.895) and XAU (PF 0.84).
- **Do not revive** 5-13-34-89 pullback, including “just on USDJPY again.”

### 7.3 Archive `EA_SonicR` Classic XAU / density / London Classic

- Portfolio row: best short seed PF~1.40 / ~1.23 tpw; longer route PF~1.15; equity REJECT; 2024–25 pocket — **not a survivor**. `local-empirical`  
  `04. Memory/do_not_repeat_failures.md`
- EUR London Classic V1: 49,558 signals / 0 trades (route-scope bug), then 2 trades / 2 years (killed by prereg).
- Density recovery: M5 T1 PF 0.505; M15 no-PVSRA 2 trades; M15 source-core 14 trades PF 1.28 — cadence/edge fail; `trap_risk` labels were net **positive**, so do not veto from them.
- Source Classic Wave/Dragon probe: `trap_risk` and `clean_classic_unconfirmed` lost; `clean_classic_run` never fired.
- XAU S1 Dragon–Trend distance veto 2.20 ATR: removed impulse winners (control PF 1.30 → 1.03).
- GBP London value-drift to EMA89: runway too small vs cost.
- EUR Asian manip / CONTEXT_FAIL anatomy: killed as densify of the same fields.
- **Do not** patch Asian-range / CONTEXT / Dragon-Trend distance / ATR-delete-cadence on the same fields.

### 7.4 Hybrid ICT-Sonic

- AND-stack H4 BOS/FVG/liq + M15 wave + Dragon + tick climax + session: **N=0** for years; DIAG with Dragon±40 floor off still **1505/1508** SL-cap fails, N=3 toy. Terminal `HYP-HIS-SL-SIGATR-M15-EUR-001` PF 0.98, ~0.22/week. `local-empirical`
- Lesson: **do not AND** ICT levels + PVSRA climax + Dragon floor.

### 7.5 Grok SonicR v10

- H1 yfinance, fail-open HTF, Dragon buffer OOB, unscoped deals. Verdict `NOT_A_CANDIDATE_ENGINEERING_DONOR_ONLY`. `local-empirical`  
  `04. Memory/research/20260812_GROK_SONICR_V10_LOCAL_AUDIT.md`
- Do not import ADX / hour-block / chase / cooldown / yfinance PF.

### 7.6 2026-08-12 Classic-wave PVA pullback draft

- `REJECT_PRE_SOURCE_DEDUP_FAIL`. Same Dragon/Trend/PVA family, tick_volume ≠ real volume, ambiguous indexing. `local-empirical`  
  `04. Memory/research/20260812_SONICR_CLASSIC_WAVE_PRE_SOURCE_DESIGN.md`
- Do not rescue by lowering PVA or adding EMA144/169.

### 7.7 Doctrine already on disk

Archive note `00. Old File/EA_Archive/EA_SonicR/sonic_research_doctrine_note_20260718.md`: current Sonic work is **reconstructed parity**, not confirmed origin parity; Classic = PA wave + Dragon angle then Trend/HTF/session/S/R; PVSRA is context; sideway is a first-class regime. `local-empirical`

---

## 8. Open gaps and recommended first Model-0 object

### 8.1 Open gaps

1. **FF thread 114792** live page is **login-walled** (not a 403 body; content not readable without an account). Wayback toolbar loaded; thread body did not. No bypass attempted. Original post #1 examples remain incompletely verified.
2. **PVA exact thresholds** are not in TAH essays. 150/200/10-bar is a community reconstruction.
3. **PVSRA-002:** S/R location/grid not unique (esp. XAU).
4. **PVSRA-003:** build vs run has no public bar-count.
5. **Wave parser:** L-H-HL is public; pivot strength is not.
6. **“Large-scale swing” SL** is public language without a rank.
7. **Owner Drive** `README-SONIC R.md` and `20260426_SONIC_PUBLIC_PVSRA_PROVENANCE_GATE.md` were used as contract summaries only; not re-fetched.
8. Broker **tick_volume ≠ entities**. Any PVSRA label on FivePercent is a quote-activity proxy.
9. Historical `EA_SonicR` host is **not** a clean Classic module (regime router, XAU sleeves, news CSV hard-bind). Do not extend it.

### 8.2 Recommended first Model-0 object (one mechanism)

**`ClassicWaveLeg3DragonBreak` on EURUSD M15, London only, PVSRA labels off the order path.**

Why this and not another:

- It is the **only** setup with a public trigger sentence (“WAVE leg #3 candle to break out of the Dragon”).
- It is **not** S360 bounce, **not** ITSM pullback, **not** Hybrid AND-stack, **not** the rejected PVA-pullback draft.
- Cadence risk is real (original doctrine wants few trades). The first gate is **source-count / feasibility**, not PF.
- PVSRA stays a sidecar so a failed volume proxy cannot zero or fake the object.

Falsify cheaply, outcome-blind first:

- Closed-bar event cadence on DESIGN years only
- Both directions present
- Median SL ≤ 120 pips and TP WHQ runway ≥ 15 pips
- If weekly cap=5 is applied after the fact for a **diagnostic**, do not select the “best 5” from outcomes

If source cadence is far below ~1/week, the honest conclusion is: **Classic is a discretionary scanner**, and the EA should ship as an **alert module**, not a trade module. That would still be a successful freeze.

---

## 9. Source list and fetch status

| # | URL / artifact | Status | Use |
|---|---|---|---|
| 1 | http://sonicr999.blogspot.com/2014/08/sonic-r-system.html | **OK** (2026-08-16) | Primary TAH 2013/14 notes: Classic/Scout/re-entry, PVSRA build/run, PVA description, Asia/London rules, 100-pip SL example |
| 2 | http://forexonsignal.blogspot.com/p/sonic-r-system.html | **OK** | Same TAH manual: WAVE/Dragon/Trend, EP/re-entry/TP/SL 100–120, PVSRA essay |
| 3 | https://www.forexstrategiesresources.com/metatrader-trading-system-ii/286-sonic-r-system-full-version/ | **OK — CONTAMINATED** | Fratelli hybrid (QQE/CCI/50SMA/LCD). **Do not freeze.** Offers paid zips/EAs — not retrieved |
| 4 | https://www.forexfactory.com/thread/114792-sonic-r-system | **LOGIN WALL** | Live FF requires account. Recorded blocked; no bypass |
| 5 | https://www.forexfactory.com/showthread.php?t=114792 | **LOGIN WALL** | Same thread, old URL |
| 6 | https://web.archive.org/web/20141222120650/http://www.forexfactory.com/showthread.php?t=114792 | **TOOLBAR ONLY** | Capture exists; body not extracted by fetch |
| 7 | https://web.archive.org/web/20150311034322/http://www.forexfactory.com/showthread.php?t=114792 | **TOOLBAR ONLY** | Same |
| 8 | https://sgtradingcourses.blogspot.com/2013/11/sonic-r-system-kyaw-trader.html | **OK** | Seminar: Sonic/Classic/Re-entry/Scout SL notes; EMA34 Dragon + PVA |
| 9 | http://th3-pro-forex.blogspot.com/2013/03/sonic-r-system-2013.html | **OK** | Best public **Classic wave** spec (L-H-HL / H-L-LH, leg #3, Dragon/Trend/timing) + TAH indicator history |
| 10 | https://www.investorshack.com/sonic-r-trading-system/ | **FAIL** (request error) | Linked from sonicr999 comments; not used |
| 11 | https://www.tradingview.com/scripts/pvsra/ | **OK** | Community 150/200 reconstructions |
| 12 | https://www.tradingview.com/script/Etj1ixAs-Traders-Reality-Main/ | **OK** | Explicit 10-bar 150/200 + spread×vol reconstruction of PVA colors |
| 13 | https://github.com/search?q=PVA+candles+climax+1.5+2.0+volume | **LOGIN WALL** | Code search not used |
| 14 | Owner Drive README-SONIC R.md | **Contract summary only** | Classic core; Scout parked; PVSRA analysis; Dragon EMA34 H/C/L; Trend EMA89; WHQ; run vs build |
| 15 | Owner Drive 20260426_SONIC_PUBLIC_PVSRA_PROVENANCE_GATE.md | **Contract summary only** | PVSRA-002 S/R gap; PVSRA-003 run-vs-build; thresholds not exact |
| 16 | `00. Old File/EA_Archive/EA_SonicR/sonic_research_doctrine_note_20260718.md` | **OK local** | Reconstructed-parity doctrine |
| 17 | `04. Memory/research/20260812_GROK_SONICR_V10_LOCAL_AUDIT.md` | **OK local** | v10 not a candidate |
| 18 | `04. Memory/research/20260812_ITSM_SONIC_USDJPY_REVIVAL_AUDIT.md` | **OK local** | ITSM no revival |
| 19 | `04. Memory/research/20260812_SONICR_CLASSIC_WAVE_PRE_SOURCE_DESIGN.md` | **OK local** | Rejected PVA-pullback mapping |
| 20 | `04. Memory/research/20260812_SONICR_POST_ITSM_FRONTIER_CLOSEOUT.md` | **OK local** | Post-ITSM frontier (other families) |
| 21 | `04. Memory/research/20260813_SONIC_SOURCE_RECOVERY_AND_PRIMARY_RESEARCH_FRONTIER.md` | **OK local** | Archive source recovery; trend-fail draft rejected |
| 22 | `02. AlphaFactory/STRATEGY_LOG.md` S360, S506–S543, S701–S702 | **OK local** | Dragon bounce / ITSM economics |
| 23 | `04. Memory/do_not_repeat_failures.md` EA_SonicR / EA_ITSM rows | **OK local** | Family kill radii |
| 24 | `03. EA Developer/EA_HybridICT_Sonic/*` | **OK local read** | AND-stack + 20-bar 1.5 climax + Dragon±40 — do not copy |
| 25 | `03. EA Developer/EA_SonicR/Include/SNR_Context.mqh` PVA/WHQ/classic labels | **OK local read** | Reconstructed 10-bar 150/200 and 100-pip WHQ |

No zip, rar, exe, or ex5 was downloaded. No paid page was purchased.

---

## 10. Parent handoff

- **Research status:** `DONE`
- **Packet path:** `04. Memory/research/20260816_SONICR_PVSRA_RESEARCH_PACKET.md`
- **First freeze object:** `ClassicWaveLeg3DragonBreak` (§6), EURUSD M15 London, PVSRA sidecar only
- **Do not implement in this worker turn** (research contract)

### Executive summary (15 lines)

1. Sonic R is a discretionary M15 swing method: WAVE at S/R + Dragon entry + Trend bias + historic S/R exits, with PVSRA as context. `public-source`
2. Classic is the only public setup with a trigger sentence: L-H-HL / H-L-LH, then **leg-3 breaks the Dragon**; pending several pips beyond. `public-source`
3. Scout is early PA (H/L pattern or range break) and is **parked**. Re-entry only after a live Classic, never into a loser. `public-source` + `owner-drive`
4. Dragon = EMA34 H/C/L; Trend = EMA89 close. Neither is an ITSM 5-13-34-89 band. `public-source` + `owner-drive`
5. S/R priority is whole > half > quarter, then swings. The pip grid is **not** public (PVSRA-002). `public-source` + `owner-drive`
6. PVSRA asks where notable volume sits vs S/R and whether entities are building or running; trade the **run**. `public-source`
7. Exact PVA 150%/200%/10-bar/spread×vol numbers are **reconstructed** (Traders Reality + local parity), not TAH essays. Do not treat them as original law.
8. Broker tick volume is what TAH described; it is still a poor “entity” proxy on retail FX. `public-source` + `local-empirical`
9. ForexStrategiesResources “full version” is a **different** Fratelli system. Ignore it.
10. Forex Factory t=114792 is **login-walled**; recorded blocked.
11. Local kills to not revive: S360 Dragon bounce/break; ITSM pullback; Hybrid AND-stack; archive Classic patches; Grok v10; 08-12 PVA-pullback draft. `local-empirical`
12. Automatable: Dragon/Trend math, closed-bar leg-3 break, London/Asia clock, pending+SL cap, WHQ TP. Discretionary: Scout, build/run, wave quality, “S/R just beyond.”
13. First Model-0 should be **Classic only**, EURUSD M15, London, `InpRequirePva=false`.
14. If that object has no lawful cadence, ship a scanner, do not force trades.
15. A new modular EA is allowed; retuning killed Dragon-bounce / ITSM / Hybrid stacks is not.
