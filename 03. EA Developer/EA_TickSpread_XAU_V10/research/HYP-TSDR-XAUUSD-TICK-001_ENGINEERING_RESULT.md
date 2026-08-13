# Engineering result - HYP-TSDR-XAUUSD-TICK-001

Verdict: `INVALID_D0_PROOF_SCHEMA_NO_DATA_AUTHORITY`.

Run `20260812_023104` reached MT5 and emitted the frozen fidelity counters, but AlphaFactory rejected the journal because the source printed an M1-shaped D0 series proof while the validator requires its canonical `m5_*` proof schema. The report and provisional counters are not authoritative and no economic metrics are permitted.

Fresh runtime identity `HYP-TSDR-XAUUSD-TICK-002` / `EA_TickSpread_XAU_V10R1` preserves every fidelity counter and gate and changes only the D0 proof schema plus identity/log prefix.

