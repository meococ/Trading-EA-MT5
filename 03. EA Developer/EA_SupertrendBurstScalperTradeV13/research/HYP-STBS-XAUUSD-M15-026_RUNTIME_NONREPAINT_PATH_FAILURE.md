# HYP026 runtime non-repaint path failure

Verdict: `KILL_RUNTIME_NONREPAINT_DERIVED_MANIFEST_PARENT_MISMATCH_NO_ADMISSIBLE_ECONOMIC_VERDICT`

## Exact failure

The sole `STBS026-MODEL0-TRAIN-001` attempt compiled and completed one MT5 run, then stopped at the mandatory run-local non-repaint audit:

`NONREPAINT_AUDIT_ERROR: snapshot_root escapes the run directory`

The adapter wrote `nonrepaint_run_manifest.json` under the run's `analysis` directory. The auditor defines the allowed run directory as `manifest_path.parent`, so the frozen `snapshot_root` at the sibling `run/snapshot` directory correctly failed the containment check. The manifest must be located at the run root for that unchanged snapshot path to be a child.

This is an evidence-harness path error. It does not reject or validate the Supertrend strategy, trades, costs, returns or market edge.

## Immutable identities observed at fail-stop

- Attempt start: `850FA109EF88DD32F6AA365429856C0D95FBD4C40633DDEE6711E68DAFA7F35F`.
- Attempt terminal: `26E45DC012C4B7E5115D5FF027A2930D5DBB366CB40B7F233675D594DBE8C05C`, status FAILED, retry false, run `20260810_073648`.
- Run manifest: `11566CBDED4B7466F3CA809162980C9387E1B0B949FBE1B6E6D15990C371D5BD`.
- Report: `706AE950D20C84DD24364722E613BF5C7C7105C5A2DAB0598E2FE89847E976C5`.
- Journal: `7718C4205A70FEF32157B3286987077D8D35FAC988C94F4EBCA0DEB0D7579A9D`.
- Lifecycle CSV: `0F3B393D7BFB764DD69BC670ABA68E7B8D1E36CBB743BC6D6A1AD33D1A171FDA`.
- RunMeta: `EFF1941719BBA3478680FFC639E87B60506AE237C416429B9EE27947AE46A25D`.
- Source snapshot: `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`.
- Run EX5 snapshot: `94FE593C64E55A276B6C7E912B53D72087644954E09371B13292F9C048FDD45D`.
- Config snapshot: `578B769FCC90A8EE5317213EB324DB745125D670EE7F0B2E59B9E1AEC466C12B`.
- Rejected derived non-repaint manifest: `2A1665289F14248E1A2B650A2456BEA201B03392C01D3AB75596CBC0379FDE04`.
- Run compile log: `224B3AA926D5342A3A205DE7BBEC4F99CE6A3B660D4BD828F73102DE75725279`, exact 0 errors and 0 warnings.

## Evidence boundary

AlphaFactory printed raw report performance before the research runner reached its own non-repaint, verified-cost and unified-acceptance gates. Those values are observable failure-side output only. They are not accepted PF, expectancy, return or economic evidence and may not inform filters, direction, sessions, stops, targets, holding or parameters.

No optimization, OOS, validation, holdout, paper, live or market-edge stage opened. Same-ID retry is forbidden.

## Lawful next revision

The narrowest next lane is a fresh comparator-only child over immutable copies of this completed run. It must claim before reading inherited artifacts, place the captured snapshot and derived manifest beneath one sealed subtree, rerun the unchanged auditor, and only after that engineering PASS invoke the unchanged HYP026 verified-cost and unified-acceptance gates.

No MT5 rerun, compile, new source data, new outcomes or strategy change is authorized. A fresh identity-only MT5 revision is only the fallback if the sealed comparator cannot reproduce the required evidence without weakening a frozen gate.
