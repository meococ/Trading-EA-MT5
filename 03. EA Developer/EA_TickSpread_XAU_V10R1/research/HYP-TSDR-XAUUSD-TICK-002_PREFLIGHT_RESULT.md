# Tick-fidelity preflight result - HYP-TSDR-XAUUSD-TICK-002

Verdict: `DATA_FRONTIER_BLOCKED_SYNTHETIC_SPREAD_RUNS_NO_ECONOMICS`.

AlphaFactory run `20260812_023529`, XAUUSD M1 Model 0, HQ100, no-trade authority. Engineering passed: fresh compile `0 errors, 0 warnings`, static contract `15/15`, canonical D0 proof, zero orders, final balance unchanged, and bounded journal.

The frozen five-broker-day preflight collected 644,759 observations. Bid/ask validity was 100%; decreasing `time_msc` 0%; equal-`time_msc` 0%; median raw spread `0.37`, p95 `0.40`, p99 `0.42`; spread-change rate `0.6801%`; no histogram overflow. These gates passed.

The terminal explicitly reported `every tick generating`. More importantly, 629,685 ticks belonged to constant-spread runs of at least 40 ticks: `97.662072%` versus the frozen maximum `40%`. This single hard failure blocks the quote-flow frontier on this tester. Populated `last`/`volume` fields do not rescue the result because the decisive bid/ask spread path is synthetic-like by the preregistered gate.

No V10 entry logic, matched control, performance backtest, OOS, or optimization is authorized. Do not relax the constant-spread-run gate, reinterpret generated ticks as native quote flow, or build spread-shock economics from this stream.

Evidence hashes: source `6A82046FB21C4AEFA8DA8A0B1E953D4CC164FEBABA202D3C4C12787D93A5D823`; EX5 `D50D6BFDE075EE51CC2D6CA994FFB05092818AD7513D64CE7910F2DA4E9D4662`; report `C0ABCA4306C856CA065CCD4411169C880DAFBD538DDA0CA660AB725E34330976`; journal `40D116C5084D22DA6BE30747EE6B410AF138D1D576A4E5C94AC68CAB1683427B`; manifest `FCB3E1988CEB6082351DE6BB94C0546566D713BEE29EBA4BF2764AAAE7FFC65D`.

