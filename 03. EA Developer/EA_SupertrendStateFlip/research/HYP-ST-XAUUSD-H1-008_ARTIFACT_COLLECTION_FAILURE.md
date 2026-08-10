# HYP-ST-XAUUSD-H1-008 - artifact collection failure

Status: `KILL_EXACT_ARTIFACT_COLLECTOR_JOURNAL_SELECTION`

## What passed

The sole `ST008-MT5-001` AlphaFactory run completed successfully at
`02. AlphaFactory/runs/EA_SupertrendStateFlip/20260809_064257` under Model 0,
with no trade or economic authority.

- History Quality: 98%, above the frozen strict `>97` gate.
- Broker history: `2004.06.11` through `2026.07.30`.
- Exact data-provenance proof passed for XAUUSD M5/M1.
- MQL summary: `rows=29460`, `raw=690`, `executable=683`, `gaps=7`,
  `long=339`, `short=344`, `failed=false`.
- Source snapshot SHA-256: `580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF`.
- Run EX5 SHA-256: `DCE8F2EB93F9FCF6BF827151F576664D21316C5693E76B3886FCC289C499710C`.
- MetaEditor compile log SHA-256: `B766F5FBC26B8BAD7679E6D736E588EFA8462DFA1CDBB3E7D1F23550AD9E170D`,
  with `0 errors, 0 warnings`.
- Common parity CSV SHA-256: `C404DDE7922C757CC0B1B3D7E3AF8F48C7A4E0F219716314A138D1AC4AB61DD3`,
  5,791,799 bytes, created and last modified inside the ST008 run interval.

Sealed run/launcher evidence:

- Alpha run manifest `AC9CA6A3878E6545A86FD743FE3918F3EE3D913024676F48B54C62DEC771B9F8`.
- Tester report `178901C855F050FA18217762509F791870D8CB2A2903CEF08C0436E8A7EE79EB`.
- Run-local journal delta `3F441837BBF26A89EFFF310659CFB973824C76D3D903B887B98954E322453C2F`.
- MT5 attempt start `F5BEDC1AAEACB27F6C8014C41B86511DF79BBCACF0AFE3A9241A453A3535A0E2`.
- Launcher stdout/stderr `30DFF63C6025AF3D16E160CA7E772B918DF23F3BEACD4BDB4A8528EBADCD2FFD` /
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`.
- MT5 receipt `C10CA25EB8FE6264DD9F1F12EAE0FA44CC53D69C29823D2C694330BCA2AF7CCA`.
- MT5 terminal `991AFEB2C0C64A3CD9F0626CCFB56A1EA40A82D698546CA95E66EBB8C0682C5E`.

## Exact failure

The sole `ST008-ARTIFACT-COLLECT-001` attempt claimed durably, then failed in
`locate_tester_journal`. It scanned the mutable daily tester log
`Tester/logs/20260809.log` and demanded exactly one ST003 summary and no ST003
fatal anywhere in the whole file. That daily log legitimately contains the
earlier terminal HYP007 fatal/summary and the current HYP008 summary. Therefore
the collector rejected valid current-run evidence.

The hash-bound HYP008 run-local journal delta contains two byte-equivalent
current summaries: one terminal stream copy and one Core 01 copy. It contains
no HYP008 fatal. The duplication is provenance aggregation, not two MT5 runs.

- Collector attempt start SHA-256: `460E7A0C69CD97539ED95EA957B43329FECFF99B2C25228016ADD2CDDE0AA9E5`.
- Disclosed failure terminal SHA-256: `80C9186DD0ACB17600A77A6F8C09EC9D400922FD025692A387D2317C22F636B2`.
- The failed collector did not create a receipt and did not modify the Alpha
  run directory before failing.

## Failure radius and next legal revision

This KILL applies only to the ST008 collector's global daily-journal selection
rule. It does not reject the completed MT5 run, MQL implementation, source
formula, parity CSV or economic edge; economics were never opened.

A fresh HYP009 may collect the already completed HYP008 run without another
MT5 execution. It must claim under new collection/comparator IDs, require the
exact HYP008 run/manifest/CSV/compile hashes above, use only the manifest-bound
run-local journal delta, accept multiple occurrences only when all normalized
ST003 summaries are identical and equal to the frozen counters, reject any
current-run `ST003_FATAL`, and seal the CSV/journal/compile log before parity.
HYP009 must authorize no MT5 rerun and no performance/economics.
