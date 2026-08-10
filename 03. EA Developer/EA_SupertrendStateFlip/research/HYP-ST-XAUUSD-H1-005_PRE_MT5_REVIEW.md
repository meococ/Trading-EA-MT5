# HYP-ST-XAUUSD-H1-005 — Independent pre-MT5 review

Status: `PASS_PRE_MT5`  
Scope: static/read-only; no MT5 execution and no source Parquet access.

## Verdict

No fatal blocker remains for the fresh HYP005 initial authority row or its
single correctness-only Model-4 attempt. HYP004 is terminally parked as static
compile evidence; HYP005 is the first legal Model-4 execution identity.

## Required registry shape

- hypothesis `HYP-ST-XAUUSD-H1-005`, parent HYP004, initial state `screened`,
  model 4, verdict `FROZEN_ST005_MT5_PARITY_RUN_AUTHORIZED`;
- `evidence_contract_kind=data_acquisition`, no economic acceptance object,
  fixed-window XAUUSD data acceptance with History Quality `>97`, no-skip,
  journal bounds and D0 series proof;
- authority `DATA_ACQUISITION_ONLY_NO_PERFORMANCE`, Model-4 acquisition true,
  Model-4 performance false;
- only `ST005-MT5-001`, `ST005-ARTIFACT-COLLECT-001`, and
  `ST005-COMPARATOR-001` authorized, each limit one and unconsumed;
- target HYP003 and inner identity `ST003-MT5-PARITY-001` /
  `ST003_MQL5_PARITY_001.csv` remain frozen;
- every order, outcome, post-event OHLC, return, economic, optimization,
  validation, holdout, promotion, paper, live and market-edge permission false.

## Verified HYP005 bindings

- prereg/source: `8941EAD74FB185B946FD54B3BAB24E9A325BED15EED9C40BADFA493CAD8FD346` /
  `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02`;
- builder/packet/receipt/registry snapshot:
  `D130BC6786735887FFBA0111C849E7C08345B397A12BBF22DB11E86D150F82FF` /
  `D1EA1EE439A8BB36C7D8D5E2D714239C3561DD60D9944D964B65AE40E1368351` /
  `38C70CBDDD1958D0B928ADC95C75C5F02C76C7D84ECEEDF8286794655A95F109` /
  `B8D92071C6372D4AB258ACCD27F26881AE4C17C4AF854C8D8610BFC05CCC3E4D`;
- non-repaint manifest/audit:
  `0F562B35318AB2DB1477CBDD3FE7A70C0D82275850B6881E4CBFB57C222410EE` /
  `D1582FD2B009380AC0B3EC91B679540A2CD6F536C6E288A8747A20656E16AA0C`;
- launcher/collector/comparator:
  `A643B1DD53A2B7DD082B1FB8D6F85B8D60E1B2149CF83D02CC3B9C6578976467` /
  `B74EF6ED502BE4532AC72ED5E8F3ABBAF76044A0708BB3DD033BFCBB497D54DA` /
  `3D7879D7A6D89E097C329837492FEC226C4E88CE392425283EF62BE93CE861A2`;
- HYP005/HYP003 tests:
  `724D7B39C55A52F570F864A7E99EFF9FB535632EA0FA3A7192FB5D1C087BCC87` /
  `22F0F1F25F0886402B2EF098017EFCC1D6C01111C5142E90E5752BDD4B27C590`;
- cost manifest / `.gitignore`:
  `0C16BDE5DA31243AF0AD4758244071AEBE0FEE7143942472897077BB95A0E97E` /
  `BC581FE4158654B225CADCCE2B9CC5C746CD2EECA713B884F873D2A6430AAB67`;
- signed Git status:
  `F137243CBBEE6FA4F5046A29EFC9C8CC5B40574D35747A2A44C044A4CC85C80E`.

The receipt reconciles all 20 evidence items. The collection-aware
non-repaint audit passes with no findings and exactly one permitted provenance
`CopyTime` at archived source line 86. The full package suite passes 48 tests.
At review, the common CSV and HYP005 MT5 attempt root are absent.

## Parent evidence

HYP005 inherits HYP004's exact compile start/receipt/terminal and byte-identical
source/EX5/log. It also binds the sealed HYP003 oracle start/oracle/report/
receipt/terminal. It does not authorize another standalone static compile.
