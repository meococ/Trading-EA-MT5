# EA_SonicR_PVSRA

Modular Classic Sonic R host with a reconstructed PVSRA qualifier.
Tester-only. No edge, PF, or live claim.

Hypothesis: `HYP-SONICR-PVSRA-CLASSIC-XAUUSD-M15-001`
Symbol / TF: XAUUSD M15. Entry is market at the next bar open after a closed signal bar.
Scout is compiled off. PVSRA cannot open a trade alone.

## Modules

| File | Role |
|---|---|
| `Include/SNR_Types.mqh` | Shared structs, copy helpers, fail-closed primitives |
| `Include/SNR_Dragon.mqh` | EMA34 high/close/low band + mid slope in ATR |
| `Include/SNR_Trend.mqh` | EMA89 close, slope, side |
| `Include/SNR_Wave.mqh` | Closed-bar swing pullback into Dragon; overlap/choppy reject |
| `Include/SNR_PVSRA.mqh` | Tick-volume vs prior average; rising/climax support or veto |
| `Include/SNR_SRLevels.mqh` | Whole / half / quarter round numbers + directional runway |
| `Include/SNR_Session.mqh` | London / NY kill zones via `TimeGMT` + UK DST; Friday flatten |
| `Include/SNR_Signal.mqh` | Classic AND of wave + Dragon angle + Trend side + PVSRA |
| `Include/SNR_Risk.mqh` | Percent risk, lot normalize, SL >= N×spread, daily/DD locks |
| `Include/SNR_Execution.mqh` | `CTrade`, symbol+magic ownership, no foreign tickets |
| `Include/SNR_Telemetry.mqh` | Counters + optional decision CSV |

The EA computes from native `iMA` / `iATR`. Chart indicators are overlays only.

## Attach indicators

Compile each file in MetaEditor, then attach to the same XAUUSD M15 chart as the EA:

1. `Indicators/SNR_Dragon.mq5` — Dragon band
2. `Indicators/SNR_Trend.mq5` — EMA89, color by slope
3. `Indicators/SNR_PVSRA.mq5` — tick-volume histogram (separate window)
4. `Indicators/SNR_SRLevels.mq5` — whole / half / quarter lines

Match EA inputs: Dragon 34, Trend 89, PVSRA rising 1.5× / climax 2.0× (reconstructed), whole step 10 on gold.

## Compile

```powershell
powershell -NoProfile -File .\02. AlphaFactory\alpha.ps1 compile EA_SonicR_PVSRA
```

Do not compile from `00. Old File/`.
