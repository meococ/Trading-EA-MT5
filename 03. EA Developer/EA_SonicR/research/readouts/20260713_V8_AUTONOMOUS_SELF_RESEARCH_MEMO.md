# V8 Autonomous Self-Research Memo — 2026-07-13 (~23:40 UTC+7)

Status: `SELF_RESEARCH_AUTHORITY / GPT_WAIVED / PROBE_FIRST / NO_FAKE_EVIDENCE`

## Process authority

Owner decision NOW: skip ChatGPT / GPT Deep Research entirely. No Browser
login wait. No chatgpt.com submit. Autonomous local/agent research is the
authority path. Evidence quality remains 1A fail-closed. Sub-agent model:
`cursor-grok-4.5-high-fast`.

## Binding local surfaces

| Surface | State |
|---|---|
| G3 rates panel | Mostly ready; lag contract draft; hashes in readiness receipt |
| Carry weekly / daily / rate-event probes | All `KILL_AT_OFFLINE_PROBE` (cadence/sample) |
| COT TFF 2022–2025 | On disk under `v8_exogenous/raw/` + extracted TXT |
| Carry×vol join contract | Frozen for one offline probe |
| COT TFF probe contract | Frozen for one offline probe |
| QFSI Real cost | Still `STOP_DATA_FRONTIER` (Demo ≠ Real) |
| Price-only H4/D1 (V7) | Frontier stop — closed |

## De-dup baseline (must not reopen)

Locked: V2–V7 fix/benchmark, round-number, impact-pressure proxy, tick-volume
flow, news-without-surprise, H4 ribbon, D1 compression, ACF regime, RV-gated
trend, multi-pair consensus, price lead-lag, COMEX basis without venue data,
Asian-range reclaim, Dragon/EMA vetoes, ICT renames, indicator mining,
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` rename. Also: do not rescue the
three killed public-rates carry books by retuning deadband / rebalance clock /
price garnish.

## Mechanism shortlist

### C1. Sticky G3 short-rate cross-sectional carry (weekly / daily / event)

- Thesis: point-in-time policy/MM differentials rank EURUSD/GBPUSD/USDJPY.
- Data: G3 panel + Demo D1.
- Result: **KILLED** — PF can look strong; cadence/sample fail (13 / 68 / 24
  train trades). Closed family for this campaign.
- Cost sensitivity: high PF after 1.5–3.0 pip stress on sparse sleeves is
  meaningless vs GOAL 2–5 trades/week.

### C2. Menkhoff-style carry × global FX vol innovation (H4)

- Thesis: carry exposure is compensated risk; positive innovations to global
  FX vol should flatten; hold carry only when vol innovations ≤ 0
  (Menkhoff et al. 2012 transfer). Direction from rates; gate from closed-bar
  FX vol residual — not a price-direction signal.
- Data contract: frozen in
  `preflight/v8_exogenous/20260713_V8_CARRY_VOL_JOIN_CONTRACT_V1.md`.
- Independence: not hold-until-flip D1 rank; uses H4 + time-stop + weekend
  flat + vol gate. Still rates-causal for direction.
- Falsifiers: fails train PF/cadence; loses to momentum-sign control; year
  concentration; collapses if vol gate never fires or always flats.
- Expected cost: H4 ATR stops + 1.5/2.5 pip stress; denser than D1 sticky
  carry if time-stops recycle entries.
- Status: **PROBE AUTHORIZED** (one frozen offline probe).

### C3. CFTC TFF speculative net-positioning change (weekly, lagged)

- Thesis: after Friday release of Tuesday as-of TFF, Asset Mgr + Leveraged
  Money net change (scaled by OI) predicts subsequent spot FX drift until the
  next release / Friday flat.
- Data contract: frozen in
  `preflight/v8_exogenous/20260713_V8_COT_TFF_PROBE_CONTRACT_V1.md`.
- Independence: causal variable is delayed public positioning, not rates and
  not spot-return rank (control uses return sign on same calendar).
- De-dup: not S618 consensus (spot agreement); not USD-factor; not carry
  rescue. V8 rates-only packet forbade COT; Owner unlimited-GOAL + GPT waiver
  + structural death of rates-only cadence reopen B3 positioning surface.
- Falsifiers: cadence < 0.5/week; PF < 1.05 stress-A; lose to return control;
  missing market weeks fail-closed.
- Expected cost: D1 ATR stops + 1.5/3.0 pip stress; weekly event density
  capped ~3 sleeves × ~52 weeks/year.
- Status: **PROBE AUTHORIZED** (one frozen offline probe).

### C4. Calendar-only / surprise-less rate-event FX scalp

- Kill at intake: V3 news/event clock without reconstructable surprise is
  closed; rate-event carry probe already killed on cadence.

### C5. Equity/bond risk-on differential without new archive

- Kill at intake for now: no hash-bound equity/bond panel frozen with lag;
  high risk of collapsing to killed S619-style catch-up. Reopen only after
  acquisition + lag contract, not from memory.

### C6. H4 fixed-horizon pure carry (no vol gate)

- Kill at intake as **frequency rescue** of the killed D1 daily book unless a
  distinct causal claim exists. Carry×vol (C2) already supplies the lawful
  higher-frequency rates design with an independent vol state.

## Probe execution order

1. `V8_COT_TFF_SPEC_NET_CHG_V1` (C3) — **KILL_AT_OFFLINE_PROBE**
   (cadence OK ~1.95–2.2/wk; fails beat return control and/or year
   concentration). Readout:
   `readouts/20260713_V8_COT_TFF_OFFLINE_PROBE_READOUT.md`.
2. `CARRY_VOL_REGIME_V1` / `V8_CARRY_VOL_REGIME_V1` (C2) —
   **KILL_AT_OFFLINE_PROBE** (423 trades / 2.71/wk but stress-A PF 0.947,
   negative expectancy). Readout:
   `readouts/20260713_V8_CARRY_VOL_REGIME_OFFLINE_PROBE_READOUT.md`.

## Campaign verdict (2026-07-13 ~23:45 UTC+7)

`NO_LEGAL_SURVIVOR / FAIL_CLOSED / NO_EA_BUILD / NO_MODEL_0`

Five independent offline probes on reconstructable local exogenous surfaces
are all killed (3× G3 carry cadence books + COT TFF + carry×vol). No registry
row, frozen prereg, or Model 0 is authorized from this campaign. Scaffold
`EA_CarryPublicRates` compile SUCCESS remains engineering-only.

### Next state change required (not a rescue)

Reopen only after a **new** reconstructable surface with lag contract, e.g.:

1. Hash-bound public equity-index / bond-yield differential panel (B4) with
   session alignment — not yet frozen locally; or
2. True forward-points / OIS archive with point-in-time availability; or
3. Owner QFSI login to `FivePercentOnline-Real` (cost provenance for later
   Model 0 — does not by itself create a survivor).

Do not retune killed thresholds. Do not submit ChatGPT Deep Research (Owner
waived). Do not invent compile.

## Authority hygiene

This memo grants research + offline-probe authority only. After the kills
above, it grants **no** confirmed edge, registry, prereg, EA build, or Model 0.
