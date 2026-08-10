# HYP-STBS-XAUUSD-M15-006 — Independent pre-comparator review

Status: `PASS_PRE_COMPARATOR`

## Frozen package

- Preregistration SHA256: `F9084DC6CFA8DAD0BFF1E0349710FC4A7C1F58CD8751B123E11403D26D5296BD`.
- Comparator SHA256: `AA9FD903ECA54FB2B2EA90B7A9C3B3DEA4CD16F689EA1903D471B755EE777949`.
- Focused tests SHA256: `4412C56A32F5D84FE967CCAC0473F1F0B685A2A2880F55F4459FAD4EFB7F20B4`.
- Focused pytest result: `9 passed`.
- HYP006 evidence root absent during review.

## Independent verdict

`PASS`: no fatal preauthority blocker remains. The observable contract is frozen at point `0.01` and tolerance `6e-9`; finite/positive, strict-sided, point-aligned and stop/target excess bounds are fail-closed. HYP005 and nested HYP004 are executed and receipt-bound from their single captured buffers. The durable HYP006 claim precedes run/oracle/failure/package evidence reads.

The full HYP004 analyzer is replayed with HYP005's exact Unicode Orders parser and only the geometry predicate replaced. Fresh HYP006 output explicitly proves point-bounded telemetry consistency while denying raw-double geometry, runtime tick-size and exact position-sizing proof.

## Boundary

This permits exactly one `STBS006-COMPARATOR-001`. It permits no AlphaFactory, compile, MT5, order, outcome, performance, economics, optimization, validation, holdout, promotion, paper or live action.
