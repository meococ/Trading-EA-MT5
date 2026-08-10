# HYP-STBS-XAUUSD-M15-006 — Independent post-comparator review

Status: `PASS_CLOSE_ENGINEERING`

The evidence root contains exactly four immutable artifacts. All 30 receipt bindings rehash exactly; authority raw SHA256 is `92DE6216EDA39F24578C0A93B0E7014D4A6A0478373D29D8DE8AF172AFBDC0E8`. Chronology and the start-to-receipt-to-terminal chain are consistent, and deterministic replay is `PASS`.

Metrics independently reconcile to raw `690`, executable `683`, gaps `7`, LONG `339`, SHORT `344`, ATR-ready `683`, geometry-ready `683`, physical journal records `1380` with multiplicity `2`, and zero clock/direction/exact-next mismatches. Orders are empty and trades are zero.

The exact evidence verdict is `ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_POINT_BOUNDED_GEOMETRY_AUDIT_PASS`. Point-bounded consistency is true at point `0.01` and tolerance `6e-9`; exact raw-double geometry, runtime tick-size and exact sizing proof are false. Performance/economics authority is false.

HYP006 may close parked as engineering-valid/no-economics. This does not close trade-enabled production engineering or establish economic validity.
