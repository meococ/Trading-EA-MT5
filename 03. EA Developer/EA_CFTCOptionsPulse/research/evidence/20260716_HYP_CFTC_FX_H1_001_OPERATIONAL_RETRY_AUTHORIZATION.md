# HYP-CFTC-FX-H1-001 — Operational Retry Authorization

- Initial attempt stopped before the first price bar with MT5 error
  `Terminal: Call failed`; no outcome or metric was produced.
- Initial failure receipt SHA256:
  `780C54A32BBE6707B3C77D07E2B3199CA781E045EAC04A3E004D417CF917DEC9`.
- The four protected C-drive root records remained identical to the pre-attempt
  snapshot.
- The only implementation change is the standard MT5 readiness handshake:
  `timeout=60000`, `symbol_select`, and five bounded history-read retries.
- Frozen signal, split, holdout, release lag, entry/exit, ATR stop, cost proxy,
  matched control and every pass gate are unchanged.
- Corrected probe script SHA256:
  `3EFD7D990C58DEBED34789EA7E24DF8640EC4231C35044780DCD622E37D062FC`.
- Corrected contract test SHA256:
  `AC9E3B82C476EC79314DA1DCA08589B84DD1E56E1C22DAF3E8E6AEF85DE8F2E5`;
  result `PASS 7/7`.

Exactly one economic probe remains authorized because the failed attempt
returned zero bars and consumed zero outcomes.
