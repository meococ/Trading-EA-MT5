# EA_MZMS_Scalper Logic-to-Code Matrix

| Requirement | Role | Frozen rule / index | Planned source surface | Proof |
|---|---|---|---|---|
| New-bar decision | trigger timing | `iTime(M5,0)` gate only | `OnTick` | contract test + non-repaint audit |
| Mode dispatch | architecture | `InpSignalMode` 0..5 | `ClosedBarSignal` | variants test |
| Hypothesis bind | identity fail-closed | `InpHypothesisId` must match mode map | `ExpectedHypothesisId` / `ValidateInputs` | contract test |
| Magic bind | ownership fail-closed | unique magic per mode | `ExpectedMagic` / `ValidateInputs` | contract test |
| EMA200 bias (mode 0/1) | context | close[1] vs EMA200[1] | `ClosedBarSignalControl` / `LegacyMzms` | source contract |
| MACD histogram (mode 1) | trigger | main-signal at shifts 1/2/3 | `ReadIndicator` / `ClosedBarSignalLegacyMzms` | source contract |
| Local bottom/top (mode 1) | trigger | `h1>h2<h3`, h2<=0; inverse short | `ClosedBarSignalLegacyMzms` | synthetic cluster test |
| Minimum slope delta (mode 1) | qualification | `abs(h1-h2)/ATR[1] >= 0.01` | `ClosedBarSignalLegacyMzms` | boundary tests |
| RSI mid-zone (mode 1) | qualification | 42--58, rising/falling on shifts 1/2 | `ClosedBarSignalLegacyMzms` | boundary tests |
| ADX (mode 1) | regime | iADX main[1] >=18 | `ClosedBarSignalLegacyMzms` | source contract |
| Mode2 Donchian impulse | trigger | Donchian-20 on shifts 2..21 + rising mid ADX + ATR expand + body | `ClosedBarSignalImpulse007` | variants + matrix |
| Mode3 EMA pullback reclaim | trigger | EMA20/100 trend + pivot p* in 3..8 + depth band + reclaim, anti 4-bar break | `ClosedBarSignalPullback008` | variants + matrix |
| Mode4 BB/ATR squeeze break | trigger | squeeze on shift2+older; break on shift1 BB envelope | `ClosedBarSignalSqueeze009` | variants + matrix |
| Mode5 RSI/wick exhaustion fade | trigger | run 2..4 + RSI extreme + wick 0.55 + ADX roll | `ClosedBarSignalExhaust010` | variants + matrix |
| Indicator reads | non-repaint | `shift >= 1` only via `CopyBuffer(...,shift,1,...)` | `ReadIndicator` | contract test |
| Candle direction | qualification | bullish/bearish closed bar 1 | mode evaluators | synthetic test |
| Next-bar entry | execution | first tick after signal bar closes | `OnTick` / `TryOpenTrade` | source contract |
| Cooldown | execution guard | five completed M5 bars after accepted entry | `CooldownAllows` | synthetic/source test |
| Session | context | 08:00--17:00 UTC | `ServerToUtc` / `SessionAllows` | DST tests |
| News | cost/event guard | EUR/USD high impact +/-15m, fail closed outside coverage; XAU campaign OFF | `NewsBlocked` / presets | calendar/source tests |
| Spread | execution guard | `0 < spread <=35` XAU points at entry tick | `SpreadPips` / `TryOpenTrade` | boundary test |
| Stop | invalidation | farther of five-bar extreme+40 pts or 1.5 ATR | `TryOpenTrade` | geometry tests |
| Target | management | fixed 1.6R | `TryOpenTrade` | geometry test |
| Time exit | management | 15 M5 bars | `ManageOwnedPosition` | source contract |
| Break-even | management | default OFF; ValidateInputs rejects BE ON | `InpUseBreakEven` / manager | default-off test |
| Partials / trailing | management | none | absent APIs | contract test |
| Daily flatten | exposure | 18:15 UTC / UTC-date rollover | `ManageOwnedPosition` | source contract |
| Position sizing | risk | 0.01% default using `OrderCalcProfit` | `RiskSizedVolume` | source contract |
| Max entries | risk | 5 per UTC day, one position max | `EntryGuardsAllow` | source contract |
| Lifecycle telemetry | evidence | lifecycle-v3 RunMeta + lifecycle CSV | `OpenTelemetry` / `LogLifecycleDeal` | AlphaFactory sidecar validator |
| State telemetry | decision parity | `${Symbol}_StateTelemetry_${run_id}.csv` accepted-entry snapshot | `WriteStateTelemetryAccepted` | contract + variants |

No hard-gate row is intentionally missing for modes 0..5. Source SHA is bound after compile stabilization.
