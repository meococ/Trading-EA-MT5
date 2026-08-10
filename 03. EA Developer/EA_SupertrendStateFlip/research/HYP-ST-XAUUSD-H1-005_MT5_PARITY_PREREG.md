# HYP-ST-XAUUSD-H1-005 — Frozen AlphaFactory MT5 full-bar parity audit

Status: `FROZEN_PRE_MT5_DATA_ACQUISITION_ONLY`  
Parent: `HYP-ST-XAUUSD-H1-004` (`PARK_ENGINEERING_VALID_STATIC_COMPILE_ONLY_HANDOFF_TO_HYP005_NO_MT5`)  
Parity target: `HYP-ST-XAUUSD-H1-003`

## Objective and identities

Prove that the already compiled direct MQL5 Supertrend 10/3 implementation
reproduces the sealed HYP003 source oracle on every comparable completed H1 bar
when scheduled by MT5 Strategy Tester.

HYP005 is a fresh execution/provenance child because HYP004 froze `model=null`
before its static compile and therefore could not legally become a Model-4
registry execution state. HYP004 performed no MT5 attempt. HYP005 starts with
the correct Model-4 data-acquisition contract and uses fresh outer attempt IDs.

Two identities are intentional and must not be conflated:

- AlphaFactory/registry/evidence identity: `HYP-ST-XAUUSD-H1-005` with outer
  attempts `ST005-MT5-001`, `ST005-ARTIFACT-COLLECT-001`, and
  `ST005-COMPARATOR-001`;
- frozen formula/parity payload identity: `HYP-ST-XAUUSD-H1-003`, audit run
  `ST003-MT5-PARITY-001`, common CSV `ST003_MQL5_PARITY_001.csv`.

The inner identity is retained because HYP005 tests the exact HYP003 formula and
oracle; it is not a reused outer attempt.

## Frozen implementation and parents

- Canonical and immutable snapshot source SHA-256:
  `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`.
- HYP004 compile start/receipt/terminal SHA-256:
  `E366CF138994CF1C289EFDC0D55BC6277F637108C9E23CFEBCE415D5BA767578` /
  `E45D5459FAF76923D99800A7F1BED4FFDABEAE00ECD6A47C8E26753D82DC4B7A` /
  `A0F7AA7717CCC0EC57E55D6893FEF5331112FDC36314252B8AAD4F8FEAADEEFD`.
- Inherited static EX5/log SHA-256:
  `0C68520D3C3B073939B8A4FF403575687E93739E1A9844B6B051E85011F84982` /
  `3CF9A7A8B8C8CC39709EDFAAF9FEB2F4A8B7AAB1273D5CB7B4547A9D8675AEF6`
  (`0 errors, 0 warnings`).
- HYP003 oracle start/oracle/report/receipt/terminal SHA-256:
  `54ED6C2FF92C9B98C7AF447F2C44672723193E9182B59DEC3BC8A26FB2F4A01E` /
  `63E93022794C6DD50EBFB4464DD521D4B1757C5797B158121467F18FF2F13096` /
  `53D23C61A6CC2005B0587834A500F47860EF2104912BD7D61FDA05C52242CFC9` /
  `56DC6CBD39721002F892AE9981A47FF397455F57B744277C2C9A3F13EF0C621B` /
  `7CCB8FE8C33F3369522C93E78B6B12CBAD79FEB408B399827041E6F2EF650396`.
- Packet builder / launcher / collector / comparator SHA-256:
  `D130BC6786735887FFBA0111C849E7C08345B397A12BBF22DB11E86D150F82FF` /
  `A643B1DD53A2B7DD082B1FB8D6F85B8D60E1B2149CF83D02CC3B9C6578976467` /
  `B74EF6ED502BE4532AC72ED5E8F3ABBAF76044A0708BB3DD033BFCBB497D54DA` /
  `3D7879D7A6D89E097C329837492FEC226C4E88CE392425283EF62BE93CE861A2`.
- HYP005/HYP003 test SHA-256:
  `724D7B39C55A52F570F864A7E99EFF9FB535632EA0FA3A7192FB5D1C087BCC87` /
  `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`.
- AlphaFactory / quant analyzer / non-repaint auditor SHA-256:
  `758D0185A862E023309F7D1A9DFF5970072D71F310975AFCE526CD6E5965F93F` /
  `A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B` /
  `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`.
- Collection-only cost manifest SHA-256:
  `0C16BDE5DA31243AF0AD4758244071AEBE0FEE7143942472897077BB95A0E97E`.
- Exact launch-path `.gitignore` SHA-256:
  `BC581FE4158654B225CADCCE2B9CC5C746CD2EECA713B884F873D2A6430AAB67`.

The direct formula, initial `DOWN` state, TR/SMA10/Wilder-RMA operation order,
strict band comparisons, upper-first coincident-band identity, flat-bar
acceptance, no rounding and chronological gap handling remain unchanged.

## Exact AlphaFactory contract

- EA / symbol / timeframe: `EA_SupertrendStateFlip` / `XAUUSD` / `H1`.
- Window: `2018.01.01` through `2023.01.01`.
- Model / execution / delay: `4 / 0 / 0`.
- Role / telemetry: `control / none / off`.
- Deposit / leverage / spread: `10000 / 100 / current`.
- Timeout: `1800` seconds.
- Sidecars and indicator dependencies: empty.
- Overrides, byte-for-byte:
  `InpAuditOnly=true;InpAuditRunId=ST003-MT5-PARITY-001;InpEnableTelemetry=false;InpParityFileName=ST003_MQL5_PARITY_001.csv`.
- Receipt authority: `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`.
- Data acceptance: fixed window, History Quality `>97`, XAUUSD mandatory,
  no-skip, tester-journal bounds and D0 M5/M1 series proof required.

The HYP004 static EX5 is the reviewed reference. AlphaFactory's normal backtest
compile must reproduce it byte-for-byte; any difference fails correctness.
There is no additional standalone static-compile attempt.

## One-shot workflow

1. Park HYP004 with compile-only evidence and zero MT5 exposure.
2. Build the HYP005 packet, execution receipt, registry snapshot and
   collection-aware non-repaint audit before any HYP005 registry authority.
3. Obtain independent review; then append HYP005 once as initial
   `state=screened`, `model=4`, data-acquisition-only authority binding all exact
   hashes.
4. Confirm the frozen FILE_COMMON target and `ST005-MT5-001` evidence root are
   absent. Never delete or overwrite either to create a retry.
5. Execute each outer stage exactly once. A crash or failure consumes that
   stage ID and same-ID retry is forbidden.

The first HYP005 packet seal failed before registry authority because the new
non-repaint manifest path had not been pre-created before the Git snapshot.
No AlphaFactory or MT5 process was invoked. Its V1 preflight directory is
superseded evidence only. The corrected builder pre-creates every status-visible
output and seals the usable packet under `preflight/HYP-ST-XAUUSD-H1-005/V2/`.

The exact HYP005 attempt directory is Git-ignored only so its fsynced pre-Alpha
marker cannot invalidate the already-signed Git status. Its marker, receipt and
terminal remain independently hash-bound and will be force-added at closeout.

## Acceptance and prohibition

Correctness PASS requires compile `0E/0W`, no fatal journal line, exactly one
clean ST003 summary with `rows=29460`, `raw=690`, `executable=683`, `gaps=7`,
`long=339`, `short=344`, exact full-bar oracle parity and zero orders/deals.

This hypothesis authorizes no outcome price, post-event OHLC, return, PnL, PF,
drawdown, cost inference, optimization, validation, holdout, paper, live or
market-edge claim. An economic child may open only after correctness PASS and a
fresh cost/entry/exit/risk preregistration.
