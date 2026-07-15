# Sonic R Control-Plane Restore

Date: 2026-07-10

## Scope

The lean local sync intentionally omitted the historical Sonic R research tree,
but it also omitted the seven control-plane files required by `AGENTS.md`.
This restore copied only those seven files from the read-only Google Drive
backup. No run, casebook, label packet, source, or outcome artifact was copied.

Source root:

`G:\Drive của tôi\META TRADING\Advisors\03. EA Developer\EA_SonicR\research`

Destination root:

`D:\Trading EA MT5\03. EA Developer\EA_SonicR\research`

## Restore-Time Hash Receipt

| File | SHA256 immediately after copy |
|---|---|
| `CANDIDATE_REGISTRY.jsonl` | `EB149032E60464480923D28A54110755BD3F98DAE34A285323430B4F9CCB678C` |
| `CANDIDATE_REGISTRY.schema.json` | `60ACAF873796975A8A983428E7D738BB4539D813629DA7A22D74C15AEE484FC7` |
| `PREREG_TEMPLATE.md` | `BC139336E1D8B2591B8EB3C4D2CC0CDE51B927C3ED314DDB31A9DF715F3E5BB6` |
| `READOUT_TEMPLATE.md` | `74330DEB544B8DCFAC6A99536DFEB00C298A62F3AF224661DE07A599ECF3F0A2` |
| `SONIC_SOURCE_INVENTORY.md` | `689D00C1B292C10B8B55984E5BDD1A8CAF02C9E2C601B4787250C0D1145F787A` |
| `SONIC_RULES_MATRIX.md` | `E9511EC3F03D189A10C976EEC2B963A47FCBC091696813DAE2350A87BECDEADA` |
| `SONIC_PARITY_SPEC.md` | `0663F8C8060559F240E9A1422A54B788BC7E7286563367222BFB8F68FE20A14A` |

Every destination hash matched its source hash immediately after the copy. The
entire table is a restore-time receipt, not a table of current working hashes.

After the restore, one schema-valid append-only `idea` row was added for
`HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`. The current registry has `52` rows
and normalized-LF SHA256
`0B4E96137BFBC672E28A2E822EF6E10C7083A7E050A32EA9DDA63E15F025EA13`.
`.gitattributes` pins the registry and preregistration evidence to LF so these
hashes remain stable across Windows checkouts.

Post-restore changes also hardened the cadence contract, corrected the current
unsuffixed symbol namespace, and froze executable bid/ask outcome semantics for
the new hypothesis. Their current normalized-LF hashes are:

| Current file | Current SHA256 |
|---|---|
| `CANDIDATE_REGISTRY.jsonl` | `0B4E96137BFBC672E28A2E822EF6E10C7083A7E050A32EA9DDA63E15F025EA13` |
| `CANDIDATE_REGISTRY.schema.json` | `E4AB41AA56273D143B8B16CCD63CB56BB72917FBCEC16BA08EC3AD356F2CF4B6` |
| `READOUT_TEMPLATE.md` | `9F65017E6BF6009E68F26A93A9AD79375F6AE1E1AA5AF8ADF23C49D20379BC85` |
| `SONIC_RULES_MATRIX.md` | `954F8E9F7A7A8A0E7FC77E6FD599AE6EBE1E558DF5E46A4BCC0556BCBFC03A50` |
| `preregs/20260711_H_FX_CROSS_SECTIONAL_USD_FACTOR_001_PREREG.md` | `836098FAB7F50E855EC72A74416A29AD1517B32ABF97BECE873769A415B5ABF2` |

## Registry Health

- Restored baseline rows: `51`; current rows after the new append: `52`
- Restored baseline: `23` distinct hypothesis IDs plus one registry-meta row
- Current ledger: `24` distinct hypothesis IDs plus one registry-meta row
- Restored latest candidate states: `killed=15`, `parked=8`, active/confirmed=`0`
- Current append: one `idea`, no `confirmed` candidate
- JSON parse errors: `0`
- Whole-ledger schema-validation errors: `0`

The source-of-truth registry now also separates physical availability: `56`
locally present paths, `88` hash-pinned `backup-only` paths, and `15`
`unavailable-unresolved` historical index rows. Run
`python "04. Project Control/ai/validate_source_of_truth.py"` to verify local
paths, backup SHA256 values, and JSON/Markdown parity.

The schema now recognizes the nine frozen `candidate_result` rows through a
separate non-promotable legacy contract without rewriting the append-only
ledger. Current `candidate` rows use the stricter state machine; `confirmed`
and `portfolio-sleeve` rows cannot validate with null cadence/cost fields or a
trades-per-week value outside `2-5`.

## Authority

The restored root registry is the current doctrine-canonical ledger. The older
`research/registry/CANDIDATE_REGISTRY.jsonl` in the Drive backup is a historical
alternate and must not be used to revive its stale `confirmed` rows.
