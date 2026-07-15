# Local Research Memo — Lagged COT / TFF Positioning Candidate

Date: 2026-07-13  
Status: `NO_LEGAL_CANDIDATE`  
Authority: Owner override — **skip ChatGPT Deep Research**; local self-research only  
Scope: Inspect acquired CFTC TFF Futures-Only zips; propose **at most one** independent
hypothesis using lagged COT positioning as causal state for EURUSD / GBPUSD / USDJPY
closed-bar trading, **or** return no legal candidate with reasons.

Binding context (do not reopen):

| Artifact | Binding role |
|---|---|
| `readouts/20260713_V8_CARRY_DIFF_OFFLINE_PROBE_READOUT.md` | Weekly cross-sectional carry already `KILL_AT_OFFLINE_PROBE` (13 trades / 0.05 tw/w). **No rescue** via daily/multi-pair/price filters. |
| `readouts/20260713_V8_EXOGENOUS_LOCAL_DEDUP_BASELINE.md` | Bucket B3 allows **investigation** of delayed COT with exact lag; investigation ≠ legal / probe-ready. Locked families A1–A2 remain closed. |
| North-Star `01. GOAL/GOAL.md` | PF > 1.30 after verified cost; **2–5 trades / elapsed calendar week** per split; no weekend scalp holds. |

This memo does **not** authorize offline probe, registry append, prereg, EA source,
compile, or Strategy Tester runs.

---

## 1. COT TFF zip inspection (workspace evidence)

### 1.1 Files on disk

Path: `03. EA Developer/EA_SonicR/research/exogenous_data/v8_public/cot/`

| Zip | Bytes | Member | Uncompressed | SHA256 |
|---|---:|---|---:|---|
| `fut_fin_txt_2023.zip` | 506,931 | `FinFutYY.txt` | 2,173,118 | `43c3dbdd4d01fceefad5e457003751cdc0974c7cf46097b322e26e9e2fe44d7a` |
| `fut_fin_txt_2024.zip` | 563,591 | `FinFutYY.txt` | 2,446,910 | `3f00585741a7cf76c207df640951d644dd91ff22a1106b38ca37a2469c765637` |
| `fut_fin_txt_2025.zip` | 627,068 | `FinFutYY.txt` | 2,852,152 | `2ea0cda6395f7dd6501c27422be3763e1f2f5b41b768cfd36b871f092a07d438` |

Source family: CFTC **Traders in Financial Futures (TFF), Futures Only** yearly compressed
text (`https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm`).

Temporary extract of 2024 only was used for header/row inspection and then removed
(`_inspect_tmp` not retained).

### 1.2 Header (87 columns; key fields)

Date / identity:

- `Market_and_Exchange_Names`
- `As_of_Date_In_Form_YYMMDD` (Tuesday snapshot)
- `Report_Date_as_YYYY-MM-DD` (report as-of calendar date in file; **not** release clock)
- `CFTC_Contract_Market_Code`, `CFTC_Market_Code`, `Open_Interest_All`
- `FutOnly_or_Combined`

Leveraged Money / Asset Manager positions and week-over-week changes (causal surface
candidates under B3):

| Role | Columns |
|---|---|
| Asset Mgr levels | `Asset_Mgr_Positions_{Long,Short,Spread}_All` |
| Lev Money levels | `Lev_Money_Positions_{Long,Short,Spread}_All` |
| Asset Mgr Δ | `Change_in_Asset_Mgr_{Long,Short,Spread}_All` |
| Lev Money Δ | `Change_in_Lev_Money_{Long,Short,Spread}_All` |
| OI share | `Pct_of_OI_Lev_Money_*`, `Pct_of_OI_Asset_Mgr_*` |

Derived net (not a file column; define in any future contract):

```text
LevMoney_Net = Lev_Money_Positions_Long_All - Lev_Money_Positions_Short_All
ΔLevMoney_Net = Change_in_Lev_Money_Long_All - Change_in_Lev_Money_Short_All
```

(Equivalent level-diff vs prior published row must match CFTC change fields when both
exist; fail-closed if mismatch.)

### 1.3 EUR / GBP / JPY FX futures presence (2024 sample)

Use **exact** market names. Substring search double-counts cross-rate contracts
(`EURO FX/BRITISH POUND XRATE`, `EURO FX/JAPANESE YEN XRATE`).

| Spot map | Exact TFF market name | `CFTC_Contract_Market_Code` | 2024 weekly rows | Unique report dates | Date span |
|---|---|---|---:|---:|---|
| EURUSD | `EURO FX - CHICAGO MERCANTILE EXCHANGE` | `099741` | 53 | 53 | 2024-01-02 … 2024-12-31 |
| GBPUSD | `BRITISH POUND - CHICAGO MERCANTILE EXCHANGE` | `096742` | 53 | 53 | 2024-01-02 … 2024-12-31 |
| USDJPY | `JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE` | `097741` | 53 | 53 | 2024-01-02 … 2024-12-31 |

Sample rows confirm non-empty Lev Money / Asset Mgr long-short and change fields for
all three main CME FX contracts (inspection truncated samples retained in agent
transcript; values are week-specific and not used as thresholds here).

**Coverage gap:** only calendar years **2023–2025** are acquired. A GOAL-aligned
train/holdout (e.g. 2018–2022 / 2023–2025) cannot be frozen from current disk
state without further lawful TFF year pulls (available from CFTC historical index
back to ~2010 for TFF).

---

## 2. Publication lag contract (mandatory; lookahead kill if violated)

Primary sources:

- CFTC COT index / About: data as of **Tuesday**; reports generally released
  **Friday 15:30 Eastern** ([CFTC COT](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)).
- [Release Schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm):
  15:30 ET; holiday delays one or two days (starred dates); must use published
  calendar, not assume every Friday.

Point-in-time join rule (if any later probe were ever authorized):

| Field | Rule |
|---|---|
| `as_of_date` | Tuesday open-interest date from file (`Report_Date_as_YYYY-MM-DD`) |
| `release_datetime_utc` | Scheduled Friday **15:30 America/New_York** converted to UTC for that
  report week; **override** from CFTC release-schedule / special-announcement when
  delayed (e.g. Monday release after holiday) |
| Available-at | First FX **closed** bar with `bar_close_utc >= release_datetime_utc` |
| Forbidden | Using Tuesday as-of on Wed–Fri morning; joining on `as_of_date` alone;
  silent forward-fill across missing/delayed weeks; treating `Report_Date` as
  “known that calendar day at 00:00” |

Practical first decision bar under normal schedule: Friday D1 / late-NY H4 **after**
15:30 ET, or Monday D1 open for books that refuse Friday post-release fills.
Weekend scalp holds remain disallowed under GOAL exposure.

---

## 3. Mechanistic independence check (de-dup)

| Locked / adjacent family | Independent? | Notes |
|---|---|---|
| Weekly G3 rates carry rank (killed offline) | Yes (mechanism) | COT positioning ≠ policy/short-rate differential. **Still forbidden to “rescue”** that kill by swapping labels or adding COT as garnish on the same Friday single-pair rank book. |
| `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` | Yes if not renamed | USD-factor is spot cross-section / pullback architecture. Pure Lev-Money net on mapped CME FX futures is a different causal variable — **only if** the rule is not “rank three pairs by spot and dress with COT.” |
| Fix-fade / post-fix | Yes | No WMR/fix window in COT design space. |
| Impact-per-pressure / tick-volume flow | Yes | Public delayed futures positioning ≠ retail mid-move efficiency. |
| Price-only H4/D1 (V7 stop) | Yes **only if** decision variable is TFF fields under lag | Any EMA/ribbon/compression/momentum gate mined from spot to “create cadence” collapses to A1 duplicate / post-hoc rescue. |

Bucket B3 is therefore **open for investigation**. Independence alone does **not**
clear North-Star cadence, edge, or data-completeness gates.

---

## 4. Primary-source edge assessment (why not to freeze a candidate)

1. **Stale-flow lag:** Lev Money Δ is measured Tuesday and published Friday ~15:30 ET.
   Spot has already traded Wed–Fri before the state is usable. Any “follow the
   just-published Δ” rule trades **after** the information window that generated
   the positioning change.

2. **Causality direction (academic):** Hossfeld & Röthig (Bundesbank Discussion
   Paper 41/2015; *Finance Research Letters* 2016) find contemporaneous
   co-movement between speculative net longs and EURUSD, but predictive tests —
   after multiple-testing control — favor **exchange-rate moves → position
   changes**, not the reverse. That undercuts a clean claim that lagged
   published positioning *changes* are a forward causal driver for closed-bar
   spot entries at GOAL horizons.

3. **Practitioner extreme-positioning folklore** (COT index extremes, 4–12 week
   reversals) is typically a **rare-event / multi-week** sleeve. That family is
   mechanistically closer to “contrarian level extremes” than to weekly Δ, and
   is the wrong shape for 2–5 trades/week without diluting the extreme filter
   into always-on noise.

4. **Same structural failure mode as the weekly carry kill:** one exogenous
   update per calendar week. Attractive PF on a sparse sleeve is exactly what
   `KILL_AT_OFFLINE_PROBE` already falsified for public-rates Friday rebalance
   (PF stress-A ~1.75, **0.05 tw/w**, N=13). Cadence/sample floors fail before
   holdout.

---

## 5. Expected cadence math (GOAL 2–5 / elapsed week)

Let \(R \approx 1\) usable TFF release per elapsed calendar week (holiday delays
reduce \(R\) slightly).

| Design sketch | Max structural new entries / week | Realistic after threshold | Verdict vs GOAL |
|---|---|---|---|
| Single-pair Friday rebalance on COT score | \(\approx 1\) | \(\ll 1\) if sticky | **Cannot** sustain 2–5 |
| Independent 3-pair Friday decision, fire only on “extreme” LevMoney z | \(\le 3\) | Often \(\lt 1\) aggregate | **Fails** unless threshold is gutted |
| Independent 3-pair Friday decision, fire on \(\mathrm{sign}(\Delta\)LevMoney_Net\()\) every week | \(\approx 3\) | \(\sim 2\)–\(3\) if almost always nonzero | Hits **count** band only by becoming near-always-on weekly noise after a stale lag — not a credible edge thesis under §4 |
| Intra-week H4/D1 re-entries driven by price while “COT regime” is on | Many | — | **Illegal** under de-dup / non-rescue: exogenous becomes garnish on price-only path |

**Conclusion:** there is **no honest frozen design** that simultaneously (a) keeps
lagged TFF Lev Money / Asset Mgr fields as the decision variable, (b) respects
Friday release lag and no weekend scalp holds, (c) stays independent of killed
families, and (d) has a structural path to **stable 2–5 trades/week** with a
non-diluted mechanism and a priori edge support.

Overlay use (COT as veto on a *different* lawful primary driver) is out of scope
for this memo’s “independent hypothesis” ask and would still require that primary
driver to already clear de-dup — which weekly carry did not.

---

## 6. Verdict

### `NO_LEGAL_CANDIDATE`

**Not** because COT data are missing or unjoinable — the 2023–2025 TFF Futures-Only
zips contain the mapped CME EUR/GBP/JPY markets with Lev Money and Asset Mgr
level/change columns, and the Friday 15:30 ET lag is well specified.

**Because** no single candidate survives the joint filter required by this campaign:

1. **Cadence:** weekly publication cannot support GOAL 2–5 tw/w without either
   sparsity (carry-kill twin) or always-on weekly noise / price-driven re-entry
   (mechanism / de-dup break).
2. **Edge prior:** primary academic evidence weakens lagged published positioning
   *changes* as a forward causal state after the release lag.
3. **Train panel incomplete:** disk holds only 2023–2025; cannot freeze a proper
   pre-2023 train window from current artifacts.
4. **Non-rescue discipline:** constructing a “higher-frequency COT book” via
   daily/multi-pair/price filters after the weekly carry kill is explicitly
   forbidden.

No hypothesis_id is minted. No probe design is frozen. No series thresholds,
SL, or time-stop defaults are proposed as build-ready parameters.

### What would reopen this surface (Owner / coordinator — future only)

- Acquire TFF Futures-Only years covering at least 2018–2022 (plus holiday
  release calendar), hash-bound under the exogenous tree; **and**
- Either a **different** North-Star cadence contract for a true weekly sleeve,
  **or** a new independent primary driver (not COT-alone) where lagged TFF is a
  pre-registered secondary state with its own negative controls; **and**
- Explicit coordinator freeze separate from this memo.

Until then, B3 remains “investigated / closed for candidate freeze,” not
probe-authorized.

---

## 7. Authority footer

| Flag | Value |
|---|---|
| `verdict` | `NO_LEGAL_CANDIDATE` |
| `probe_authorized` | **false** (until coordinator explicitly approves a different freeze) |
| `registry_append_authorized` | false |
| `prereg_authorized` | false |
| `ea_compile_backtest_authorized` | false |
| `chatgpt_deep_research_used` | false (Owner skip override honored) |
| `local_inspection_done` | true (2023–2025 TFF zip members + 2024 EUR/GBP/JPY headers/samples) |
| `next_owner_or_coordinator_gate` | Do not probe COT-alone for GOAL cadence; continue other exogenous surfaces only under separate de-dup memos |

End of memo.
