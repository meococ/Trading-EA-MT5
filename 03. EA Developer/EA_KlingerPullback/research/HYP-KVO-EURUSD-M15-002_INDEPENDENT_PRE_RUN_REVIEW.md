# HYP-KVO-EURUSD-M15-002 — Independent pre-run review

Verdict: `PASS_BASELINE`

Independent review initially found one fatal path-dependence defect: `PreloadKvoState` accepted a partial `CopyRates` result. That defect was corrected before any MT5 run or outcome access.

The final reviewed source requires synchronized M15 metadata, exact `Bars==SERIES_BARS_COUNT`, exact `copied==requested`, origin equal to `SERIES_FIRSTDATE`, last completed timestamp equal to native shift 1, and strictly increasing timestamps before any recursive KVO/EMA/FSM state advance. The journal exposes the preload count and boundary values for reconciliation.

The reviewer found no remaining fatal blocker. The no-absolute-value Volume Force formula and equality-to-negative trend convention match the cited TradingView formula; EMA seed/index order, FSM cross boundaries, completed-bar causality, exact-next clock, ATR stop, 1.50R target, 16-bar exit, daily cap and fail-closed order sends are coherent. KVO002 is legally fresh because KVO001 stopped before event or outcome analysis.

Reviewed identities:

- source SHA256 `F9A0EA48EC8EF0CCA95D4AF258E54DC90675EA733166EB8EAFE31EB8996AAFEF`
- prereg SHA256 `D325F8698FB5FF3367C7578C0F729D1068BCADCE5C9CA9FC0FCF44C4CFB01D6B`
- focused test SHA256 `ACC08BA5A2B90B82F13C169131638E58687AFB99715BCE250A1A722B68DEC021` (`7/7 PASS`)
- EX5 SHA256 `D4AEEBFCD580DA379DDADD46DC06882357C3C51F50E4457D451BAF0F4EA0C9F7`
- compile log SHA256 `FF218EB30A0EB11058656B1BBB20CA826AC7DFB36E50DE4F201F8B59D805B8DF` (`0 errors, 0 warnings`)
- non-repaint manifest SHA256 `1B8FD104DF20AA140E7473F70D54CADC7CDD8D797B41A22A1AEC39D0579F9922`
- non-repaint audit SHA256 `8E5D78B8A2192762BD2B73F855FDCE05C6914EFC2E4C6B56315DEA6D2600BF42` (`PASS`, zero findings)

Authority is limited to one untuned EURUSD M15 Model-0 TRAIN baseline. No economic or promotion verdict exists before its engineering and report gates pass.
