# HYP-STBS-XAUUSD-M15-009 — static engineering result

Status: `PASS_STATIC_AND_PRE_PACKET_HARNESS_REVIEWED`

## Frozen artifacts

- Source: `EA_SupertrendBurstScalperTradeV2.mq5`, SHA256 `D950ED04F6940F82354D0D5AF2A2E59C270A71FDFE0A96873C3781849AD959BB`
- EX5: SHA256 `7E6A23689D6E832E841BD7FA2647802FC38D2B2EEF145633A5D6041D40C91A04`
- MetaEditor log: SHA256 `E3C3538DB2215F24735A9B4A22EFCB53B678D52052C3435C94959045102FD241`; `0 errors, 0 warnings`
- Preregistration: SHA256 `869F8C1D5DD5B2C4C75C273CB88DDE85F0059C0B5B50EC59D9DCFC6777830C48`
- Contract test: SHA256 `92F17DB46D729C01951E5DD4014CFFFA720B211A171333A75EA8BB2EF6726856`
- Scenario test: SHA256 `C1619D06C59A6A43BDF80537D073EFCCAA044C4B4CE162FBBB09712E64F235C2`
- EA contract: SHA256 `E15F88FB996D995D34A912714BBDAA4452893C705CE2B1096E6FCC38D96C3980`
- Non-repaint manifest: SHA256 `DE0CA46A873CEC37286AC988DDF69FC1338165B2DDEB9BC582F168AB5714FD7A`
- Non-repaint audit: SHA256 `EBE73F9F28503DC8A29558FE25EA67C681B04975B7455D708703A4A70EE813A6`, status `PASS`, no findings
- Non-repaint tool: SHA256 `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`

Focused/current regression verification: `87 passed + 10 mutation subtests`. The unchanged candidate-registry baseline also passed at `829 rows / 323 hypotheses`.

The audit-governance addendum freezes claim-first packet/run staging, the exact ST003 oracle dependency, single-buffer static compile archives, run-local manifest/config/EX5 validation, dual-axis journal mapping and the zero-economic authority ceiling. Its SHA256 is `518D2B3C7427B7BCF79A11B3F3ADE2376B50271D989F1D11A699B0348AE30D07`.

## Exact source boundary

The canonical HYP007 source remains unchanged at SHA256 `2E0501CC0C19A8FD8418242A0EC64D725EBC14425AD7A1718F9FEB444B977E32`.

The V2 diff is limited to:

- fresh hypothesis/variant/magic identity;
- exact serialized execution-payload caching so unchanged state does not rewrite the dual-slot durable snapshot;
- an audit-only no-send mode using the same signal/ATR/geometry path;
- per-tick owned position/order enumeration followed by a full lifecycle only when inventory/state requires it or at each new native M15 bar;
- immediate fail-closed lifecycle management on clock or inventory failure.
- direct audit-mode guards at every entry, close and cancel `OrderSend` gateway.

Supertrend, event timestamps, M15 ATR, geometry, sizing, entry/exit requests, risk anchors, Friday/weekend behavior, max-hold logic and DESIGN boundaries are unchanged.

## Authority ceiling

This static result authorizes nothing by itself. The only proposed next action is a separately claimed no-trade Model0 engineering audit with `InpAuditOnly=true`, exact `2005–2023` clock, 300-second ceiling, exact signal counts and zero request/deal/economic access. Economic execution remains forbidden until that audit passes and a fresh economic child is reviewed.
