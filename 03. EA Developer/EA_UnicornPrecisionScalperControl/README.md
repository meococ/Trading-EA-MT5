# EA_UnicornPrecisionScalperControl

Storage-safe Model-0 control derived from the Unicorn Precision Scalper report.
The signal and risk mechanism is the frozen four-closed-bar sweep control; the
package is isolated from the separate event-anchored challenger in
`EA_UnicornPrecisionScalper`.

- Canonical source: `EA_UnicornPrecisionScalperControl.mq5`
- Active code identity: `HYP-UPSC-XAU-M5-002` (telemetry bookkeeping repair)
- Timeframe/symbol: XAUUSD M5
- Telemetry: lifecycle-v3 in the normal Strategy Tester sandbox, never
  `FILE_COMMON`
- Execution: research-only Model 0 through AlphaFactory
- Promotion: forbidden with the current research-only cost proxy
