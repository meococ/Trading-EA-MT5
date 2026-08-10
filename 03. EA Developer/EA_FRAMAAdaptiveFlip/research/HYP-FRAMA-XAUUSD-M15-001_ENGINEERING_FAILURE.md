# HYP-FRAMA-XAUUSD-M15-001 — engineering failure

Verdict: `KILL_INIT_NATIVE_INDICATOR_CALCULATION_NOT_READY_NO_BASELINE_NO_ECONOMIC_VERDICT`.

The sole attempt `20260810_215853` compiled and launched MT5, but `OnInit` immediately required 16 calculated FRAMA/ATR values. Native indicator calculation was not ready during initialization, so the EA emitted `FRAMA001_FATAL reason=FRAMA_PRELOAD`, returned nonzero, and the tester produced an empty/non-economic report. AlphaFactory then rejected the nonnumeric History Quality field. There were zero bars processed, signals, orders, trades, returns, PF or economics.

This does not reject FRAMA. It rejects only the HYP001 initialization contract that treated transient native-handle warmup as fatal.

Evidence:

- run manifest `8D6AA1C01E97173CFE57B01F5AF5A4DA8E53EBCB37A975D96A577670569767E2`
- report `A2C8384E35A682ADD9C93FAE85A8798234FD9BDF265625D707F0DBD0285E6760`
- journal `65AFCCCDDF3F560FB27853D351DC9B6A1EA7377EDAABE9EF7AF8DD0B693C1C3B`
- executed source `53ABA54A8C989CDB845E32DB1C0E5570B34B3337D5F9D250EF1D619669C35FF7`
- executed EX5 `7767ABAC893780AFFBDE94ECDC973A14319EDBD2709A6B1F0A15E570E4E2ED87`

Same-ID retry is forbidden. A fresh HYP002 may change only package identity and defer native-indicator readiness until ticks while failing the run at deinitialization if readiness never occurs.
