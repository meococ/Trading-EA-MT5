# HYP-RSF-EURUSD-M5-LIQUIDITY-POOL-006 — engineering-invalid closeout

Run `20260807_094914` completed its 105,949,201-tick tester traversal but is not an economic trial.

RunMeta recorded `indicator_ready=0` and `indicator_not_ready=125589`; no structural/context/setup counter was reached. The EA required `ReadClosed1` success for liquidity price buffers 44/45 even when validity buffers 46/47 correctly reported no level. `EMPTY_VALUE` therefore rejected the entire snapshot.

This ID is closed as `PARK_ENGINEERING_INVALID_OPTIONAL_BUFFER_READ`. It makes no performance claim. The fix must use a new hypothesis/source binding: validity flags are mandatory; price fields use optional reads and are inspected only when the matching flag is true. All economic parameters and gates remain frozen.

Artifacts:

- report SHA-256: `19E802C295E23A82F9BAFB5EEE8EAEE05C73DF86BD415180D6862B13CFBC3DBC`
- RunMeta SHA-256: `1A3D884E945D45C30A0D6D39410BF9691471798C838E4B3D5FDA891A5B0C21C1`
- EntryContext SHA-256: `ACE8EFA58DF4C37F19A394E3EB144FE0E5450CD02BCDD45E9CD82D1628E4999B` (0 rows)
- Lifecycle SHA-256: `9D0CC6A7F1986CD3230CE2BA275B0116C7CD2F12AF9D25D7B10C922420CA6EC7` (0 rows)
- source snapshot SHA-256: `202B8D2DB93EC186C5A7535901A02BE947834F8E1D53E4A827999156777BD3C2`
