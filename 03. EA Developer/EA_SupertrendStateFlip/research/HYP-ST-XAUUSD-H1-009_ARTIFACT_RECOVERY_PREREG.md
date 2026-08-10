# HYP-ST-XAUUSD-H1-009 - frozen existing-run artifact recovery and parity

Status: `FROZEN_PRE_COLLECTION_REVIEW_REQUIRED`  
Parent: `HYP-ST-XAUUSD-H1-008`  
MT5 run under recovery: `20260809_064257`  
Parity target: `HYP-ST-XAUUSD-H1-003`

## Evidence-driven revision

HYP008 completed its sole MT5 Model 0 correctness run with the exact frozen
summary, but its artifact collector failed because it scanned a whole daily
tester log containing an earlier HYP007 fatal/summary. The current HYP008
run-local journal delta is already hash-bound by its run manifest. It contains
two identical current-run summaries (terminal stream and Core 01 stream), no
current-run fatal, and the exact frozen counts.

HYP009 does not run MT5, compile an EA or change signal logic. It performs one
claim-before-read recovery collection of the already completed HYP008 run and,
only if collection passes, one full-bar oracle comparator. It never uses the
global daily tester log.

## Frozen inputs

- HYP008 run directory: `02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257`.
- Run manifest SHA-256: `AC9CA6A3878E6545A86FD743FE3918F3EE3D913024676F48B54C62DEC771B9F8`.
- Tester report SHA-256: `178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB`.
- Manifest-bound journal delta SHA-256: `3F441837BBF26A89EFFF310659CFB973824C76D3D903B887B98954E322453C2F`.
- Source / EX5 SHA-256: `580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF` /
  `DCE8F2EB93F9FCF6BF827151F576664D21316C5693E76B3886FCC289C499710C`.
- Canonical contemporaneous compile log SHA-256:
  `B766F5FBC26B8BAD7679E6D736E588EFA8462DFA1CDBB3E7D1F23550AD9E170D`.
- FILE_COMMON parity CSV SHA-256 / size:
  `C404DDE7922C757CC0B1B3D7E3AF8F48C7A4E0F219716314A138D1AC4AB61DD3` /
  `5791799` bytes.
- HYP008 MT5 receipt / terminal SHA-256:
  `C10CA25EB8FE6264DD9F1F12EAE0FA44CC53D69C29823D2C694330BCA2AF7CCA` /
  `991AFEB2C0C64A3CD9F0626CCFB56A1EA40A82D698546CA95E66EBB8C0682C5E`.
- HYP008 collector failure start / terminal SHA-256:
  `460E7A0C69CD97539ED95EA957B43329FECFF99B2C25228016ADD2CDDE0AA9E5` /
  `80C9186DD0ACB17600A77A6F8C09EC9D400922FD025692A387D2317C22F636B2`.

Any mismatch fails and consumes the HYP009 collection ID.

## Collection semantics

1. Validate HYP009 registry authority, then create and fsync the exclusive
   `ST009-ARTIFACT-COLLECT-001` marker before opening HYP008 run/common files.
2. Revalidate exact HYP008 run manifest, contract receipt, launcher receipt,
   source, EX5, compile log, report, data-quality gate and CSV identity/counts.
3. Read only the manifest-bound run-local `logs/tester_journal_delta.log`.
   Never scan `Tester/logs/*.log`.
4. Extract all `ST003_SUMMARY|run=ST003-MT5-PARITY-001|...` occurrences. Require
   at least one, require every normalized occurrence byte-identical, require the
   exact frozen counters and `failed=false`, and reject any `ST003_FATAL` in the
   run-local delta. Persist exactly one normalized summary line for comparator
   consumption and record the observed duplicate count.
5. Copy the exact CSV, normalized summary and compile log exclusively into the
   fresh hash-bound HYP009 evidence root. Do not modify the Alpha run directory.
6. Emit a receipt and terminal binding every source and recovered artifact.

Expected CSV counters remain exactly `29460/690/683/7/339/344`. No outcome or
post-event price is read.

## Comparator semantics

After collection PASS, `ST009-COMPARATOR-001` may run once. It must bind the
HYP009 collection receipt/terminal, exact HYP008 Alpha run, HYP003 oracle chain,
HYP008 non-repaint audit, run-local EX5 and compile evidence, normalized summary
and recovered CSV. Full 29,460-row parity and deterministic replay must pass.

The only PASS verdict is
`ENGINEERING_VALID_DIRECT_MQL5_MT5_PARITY_PASS`. It authorizes a fresh economic
child preregistration only; it does not itself authorize economics.

## Prohibitions

- No HYP009 MT5 run, MetaEditor compile, source/data rescan or same-ID retry.
- No trade API, order, deal, outcome price, PnL, PF, cost performance,
  optimization, validation, holdout, paper or live access.
- No use of the global daily tester log and no deletion/overwrite of the common
  CSV or existing HYP008 evidence.
