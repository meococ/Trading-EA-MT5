# HYP-STBS-XAUUSD-M15-015 — independent post-failure review

## Review verdict

`PASS_KILL_ENGINEERING_EVIDENCE_AND_ACCOUNT_CONTRACT_ONLY`

The independent campaign reviewer rehashed the HYP015 attempt chain and found no artifact mismatch. The sole run created exactly one directory, compiled 0 errors / 0 warnings, produced a report with no trade/order rows and one funding-balance deal, then failed because its two-source tester journal hit the 1,048,576 raw-byte cap and had no terminal summary. No economic inference is valid.

The initial reviewer recommendation was an outer-only journal-cap child. Lead review rejected that as insufficient after inspecting the captured signal rows: all 161 observed exact signals had `margin_ready=false`, and the audit generated 1,498 per-candidate margin checks plus 160 margin rejects before truncation. The frozen USD 10,000 deposit is below this account's USD 92,000 money-mode margin-call threshold, while the V4 rule demanded USD 115,000 free margin. A larger journal would only reveal the already-deterministic margin-readiness failure.

## Correct successor radius

A fresh HYP016/V5 engineering child may change only:

1. tester deposit from USD 10,000 to the established FivePercent USD 100,000 account class;
2. money-mode margin capacity to preserve `max(call, stop)` plus `max(20% of remaining equity headroom, 1% of equity)`, reducing volume only;
3. audit-only log volume by suppressing per-candidate margin prints and emitting the minimal signal fields required for count/readiness identity.

It must preserve the H1 Supertrend 10x3 state, closed-bar mapping, M15 ATR14, 1.00 ATR stop, 1.50R target, eight-bar hold, Friday rules, maximum requested risk 0.25%, lifecycle FSM and all zero-send audit gates. It needs a fresh source/package, compile, non-repaint audit, preregistration, registry authority and one fresh attempt. It may not read PF, tune a signal filter or reopen HYP015.

## Evidence binding

- failure record SHA-256: `ECAD74BA4068B4BD581ABE87D62D992966F6FAA94D5000B86070D4775D1D9751`
- HYP015 authority raw SHA-256: `E65477328CC81051D1F183A8336F57961D2AB28C0BB8EC01228689530C3C5BD7`
- attempt terminal SHA-256: `1E4C0180BE333E1CBCB7C2156AF78BD6BF67931341BF369F62BE96484086CB88`
- run manifest/report/journal SHA-256: `40EB0F78C32AAAEF6521FC9685F7DCE61D29520FCFF7F246EF705CC19C646F08` / `6BBCC900C6F8C198A604C5EC17D5341DBCC99C0FC4FEC9A4E660690F6D9168D8` / `1D2A55F682B646D919551E7F9E536095E2223D3A96A1360EA4228F4E808F5781`.

