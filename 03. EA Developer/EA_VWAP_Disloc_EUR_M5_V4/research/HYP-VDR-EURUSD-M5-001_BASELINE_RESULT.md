# Baseline result — HYP-VDR-EURUSD-M5-001

Verdict: `KILL_NEGATIVE_EDGE_OVERTRADING_ACCOUNT_STOP_OUT_NO_OOS`.

AlphaFactory run `20260812_012403`, EURUSD M5 Model 0, HQ100. Engineering passed (`0E/0W`, 13/13 static, non-repaint PASS, no missing tick volume). The account stop-out threshold ended execution on 2018-04-16 at 7% of the requested interval.

515 trades; net `-$10,043.35`; PF `0.7886`; WR `40.6%`; expectancy `-$19.50`; DD `10.9487%`; losing streak 16. Telemetry: 19,195 closed bars, 800 dislocations, 590 confirmed reversions, 515 entries. This exceeds the intended cadence before one design year and has negative price expectancy; no session subgroup can rescue it.

Kill the exact rolling VWAP18 + 1.35 ATR distance + 1.45 volume expansion + six-bar reversal object. No control/OOS/retuning/filtering. Evidence: source `45992E2FBE1C709A47EF4D34ABB391EC7B4F61130F9684FBD67B6C8C3DC8DD47`; EX5 `A4C48F9A3A4D87BE7FC2D43DDBA7EB5BBE87337CE21EE60D56810C9088685740`; report `C9694810042EC9C67ED6E215223045779A5653370D0341F0B0F4D59D7E48694E`; journal `689EB6AB9D40100E345C77E82700A6FC0C55FD44FD948044FCC34EE97ABC21BF`.
