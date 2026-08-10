# HYP-JCDR-EURUSD-M5-006 pre-baseline review

Verdict: `PASS_ONE_UNTUNED_MODEL0_BASELINE`.

Scope is engineering correctness only. No outcomes, PF or promotion claim were opened during review.

- Source SHA256: `383C582060C0332BD1A73E24316E619C125462D54046FD30CCC0AF56E7B49869`.
- EX5 SHA256: `5824F71DCE89B2FAB5E83BE215A1C6FC9BAF02975DE80AF421B1DAAFC137FB04`.
- Compile log SHA256: `4364E51BEBAA4013B6A82C97AEBE29AAEAEB605DB1979466DC5CB0019A80D28E`; result `0 errors, 0 warnings`.
- Prereg SHA256: `BB718FDE5F3E15BB2A6B84A2D38C8138AA10265635ED8781BD159D44D2488495`.
- Focused test SHA256: `F5D22D526F3F83FC73A1DB3A3066589532E2C6B5776B4B9F94857A87F8FF93C7`; `11 passed`.
- Non-repaint audit SHA256: `E5E84561B6880DDAB079E2C7124F52BF226BF71FC4F1B907F48849FDA0A0C73E`; status `PASS`, zero findings.
- Independent quant reviewer initially rejected a wrong prereg path and the build-safe default `InpResearchAutoMode=false`; after receiving the canonical package path and exact run overrides, it returned `PASS` with no remaining fatal blocker.

Authorized next action is exactly one EURUSD M5 Model-0 baseline over the frozen tester envelope, with no optimization or same-ID retry. A run failure is engineering evidence; a completed admissible report must immediately receive an economic verdict.
