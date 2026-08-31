# Sonic R context quantification — team freeze

Date: 2026-08-16  
Loop: trader → quant → devil → prop, then cross-rebuttal.  
Main Agent freeze. Not an edge claim. Not a registry row. Not a revival of `HYP-SONICR-CLASSIC-EURUSD-M15-001`.

## Consensus

1. Geometry Classic on EURUSD M15 already traded (`20260816_205426`, N=307, PF 0.94). That object is **KILL hẹp**. Do not add context gates on it.
2. “EA better than a pro Sonic trader” is the **wrong KPI**. A pro picks 5 of 50 charts. An EA cannot. The lawful “better” is **discipline**: no daily 5% blow, no add-to-loser, no grid, no weekend, no FOMO second ticket.
3. Context that cannot be measured honestly on FX `tick_volume` must not veto: **build vs run**, “at S/R” as entity activity, climax-as-exhaustion.
4. Labels already failed as gates (`trap_risk` flipped sign; `clean_classic` was a 15-bar color ratio, not a wave). Do not reuse as order filters.
5. Architecture is **three layers**, not one smarter AND-stack.

## Three layers

| Layer | May do | Must not do |
|---|---|---|
| **DisciplineHost** | Always on: 1 position, no add loser, Asia off, Friday flatten, week cap ≤5, daily lock 3–3.5%, DD lock ~8% persist | Choose which 5 setups; read wave quality |
| **ContextScanner** | Closed-bar labels + CSV overlay | `OrderSend` / pending / `{long,short}` |
| **Signal** | One frozen object only | 7-label FSM; Scout; PVSRA-as-entry |

## Scanner vocabulary (log only)

Keep as **measurable** columns (frozen *before* joining any 001 outcome):

- `wave_geom` — L-H-HL / H-L-LH + first close beyond Dragon (`SNR_ClassicWave`)
- `dragon_angle_side` — mid[t] vs mid[t-3] + PA side
- `trend_side` — close vs EMA89
- `sr_runway_whq` — pips to next whole/half (EURUSD 100/50 grid; reconstructed)
- `pva_class` — 10-bar 150/200 reconstructed; **label**, not require
- `session_bucket` — from **signal-bar** London clock

Trader story-labels (`SIDEWAY`, `CLASSIC_ARMING`, `LATE`, `SESSION_DEAD`, `NO_RUNWAY`) may be **derived later** from the six columns. They are not extra inputs.

**Drop from any veto list:** `AT_SR_BUILD`, `trap_risk`, `clean_classic`, `CLASSIC_BREAK_CLEAR` as the only fire rule (that is 001 AND-stack renamed).

## Overlay protocol (before any new Model 0)

1. Freeze schema + formulas + DESIGN window + three negative controls (permute labels, lag-20, random quartile).
2. Emit one closed-bar CSV row per M15; hash schema; **do not** rank features by PF on `20260816_205426`.
3. Score: N, P(+R), mean R vs base rate vs controls, using a **synthetic** pending/SL/TP excursion — not live EA PF.
4. A feature may become **one** pre-registered rare veto only after lift survives controls. New ID. Holdout stays sealed.

If overlay does **not** separate: Sonic stays **scanner + discipline host**, not a trade-EA lane. Open a **different** mechanism. Do not densify Dragon/CONTEXT/ATR-cadence.

## Immediate vs later

- **Now (discipline, no economics):** ISO-week trade cap + persist `dd_locked` on the existing host. Do not retune signal.
- **Now (research):** overlay emitter only.
- **Not now:** Model 0, Scout, PVSRA hard gate, XAU copy, hour/weekday salvage of 001.

## Authority

Team seats: trader `01a00b25-b189…` / `01a00b29-92e3…`; quant `01a00b25-b18b…` / `01a00b29-92e5…`; devil `01a00b25-b191-7e50…` / `01a00b29-92e7…`; prop `01a00b25-b191-7e50-669b…` / `01a00b29-92e8…`.  
Main freeze binds. QC may `BLOCK` an implement that puts scanner labels on `CTrade`.
