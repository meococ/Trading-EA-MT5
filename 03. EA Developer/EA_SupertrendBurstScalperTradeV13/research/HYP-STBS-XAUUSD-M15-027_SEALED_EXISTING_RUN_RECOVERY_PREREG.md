# HYP-STBS-XAUUSD-M15-027 — sealed existing-run economic recovery

Status: `FROZEN_PRE_AUTHORITY`

## Purpose

HYP027 is a fresh comparator-only child of terminal HYP026. It does not compile
MQL5, launch MT5, read source market data, create new fills, or change the EA.
It exists only to finish the mandatory engineering and economic gates over the
already completed, hash-bound HYP026 run `20260810_073648`.

HYP026 failed because its derived non-repaint manifest was written below
`run/analysis`, while the unchanged auditor treats the manifest parent as the
containment root. The valid `run/snapshot` tree was therefore a sibling. HYP027
changes only evidence topology: it captures the sealed run once, places the
captured snapshot and derived manifest beneath one attempt-local sealed root,
reruns the unchanged auditor, and proceeds to the unchanged cost and unified
gates only after non-repaint PASS.

The strategy, signal, ATR, entry, exit, 0.25% sizing, margin contract, costs,
2018.01.02–2022.12.30 inclusive scoring window, and all acceptance thresholds
remain exactly frozen. Raw HYP026 report performance was not used to design
this recovery and may not be used to tune it.

## Immutable parent and run evidence

- Terminal HYP026 registry row SHA256:
  `4BDE6051399987ACC4ABE96768B507741276952DBA34290BE002FB413D69D91F`.
- Model0 start: `850FA109EF88DD32F6AA365429856C0D95FBD4C40633DDEE6711E68DAFA7F35F`.
- Model0 FAILED terminal: `26E45DC012C4B7E5115D5FF027A2930D5DBB366CB40B7F233675D594DBE8C05C`.
- Run manifest: `11566CBDED4B7466F3CA809162980C9387E1B0B949FBE1B6E6D15990C371D5BD`.
- Report: `706AE950D20C84DD24364722E613BF5C7C7105C5A2DAB0598E2FE89847E976C5`.
- Journal: `7718C4205A70FEF32157B3286987077D8D35FAC988C94F4EBCA0DEB0D7579A9D`.
- Lifecycle: `0F3B393D7BFB764DD69BC670ABA68E7B8D1E36CBB743BC6D6A1AD33D1A171FDA`.
- RunMeta: `EFF1941719BBA3478680FFC639E87B60506AE237C416429B9EE27947AE46A25D`.
- Source snapshot: `F60A9469D1A6FE2D62F5E83DECB953862C68AF9E3D154EA0AE488C072B4A4DA4`.
- EX5 snapshot: `94FE593C64E55A276B6C7E912B53D72087644954E09371B13292F9C048FDD45D`.
- Config snapshot: `578B769FCC90A8EE5317213EB324DB745125D670EE7F0B2E59B9E1AEC466C12B`.
- Run compile log: `224B3AA926D5342A3A205DE7BBEC4F99CE6A3B660D4BD828F73102DE75725279`,
  exactly one zero-error/zero-warning Result line.
- HYP026 research cost manifest:
  `5C9E00C6405D82D3756DF2E913E69B1E2E34E2405B8E76DFB7EBCDECF602C513`.
- AlphaFactory execution receipt:
  `4BF162519C150FDF6D8D03EB09024FD2ED0C74AB5319793EBEC7EAD8AC329E87`.
- Pre-outcome HYP013 data task:
  `DE25AE28B29087901514B1ABA067A00B8DF05F7F4288CF93D79188A730255DE9`.
- Cost evidence sources: historical spread
  `6FBDB039300E571E30939F0149B504D53173836D0B0DDEA5772B33EA48AD0579`,
  tester commission `5076439080F46F759AF3734E19749CC71584A9CB7F05C11E84DE7A9EAE6498C4`,
  latency proxy `515619377D67EADAC3B4A55AFCEE49FC2C5A7EE3D39BBE07B54316D9B9A4836E`,
  lineage receipt `55508F8F246A5524A8EA43A6118A0C2C47BFE06039A7EDDBC2C257068508A607`,
  and raw-tick failure receipt
  `E43B91092B587D420FFDB28FAFB29F53ECB4175CCE0054A2C9252B7C366C8570`.
- HYP026 failure packet:
  `05D78766789969098D14C74B561CD7C44A0F00CFD683F71C3F63045946CB7FDA`.
- Independent HYP026 failure review:
  `0F1E97017F9A0200B67734D793A457998DFD82BB5CAF8697E38CF9DF8012EB50`.

The original run and cost manifests remain immutable and are never overwritten. The
attempt-local derivative may change only filesystem location fields needed to
point at the captured report/snapshot/config, and may add the exact frozen
nondecision CopyTime provenance object already reviewed by HYP026. All identity,
data-quality, cost, sidecar, source, binary, report and account fields remain
unchanged. The derived cost manifest changes only reference paths to the captured
pre-outcome task and captured cost-source files; every declared source hash and
all cost semantics remain exact.

## Frozen engineering gates

1. The sole attempt `STBS027-COMPARATOR-001` creates an exclusive fsynced claim
   before reading the registry or any inherited file. Success and failure both
   produce an exclusive terminal; crash residue consumes the attempt.
2. Registry bytes are read once with duplicate-key and nonfinite rejection.
   The latest HYP026 row must be the exact killed row above. The latest HYP027
   row must authorize only this comparator and bind all reviewed inputs.
3. Every inherited artifact is read once after claim, hash-checked, copied with
   exclusive create+fsync, and rehashed before terminalization.
4. The unchanged auditor SHA256
   `366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360`
   must PASS the captured V13 source with zero findings and exactly one allowed
   `collection_first_date_copytime` / `CopyTime` record at line 678.
5. The original manifest, derived manifest, auditor and audit output are
   rehashed after the audit. Any mismatch fails before cost or PF access.
6. Only after gate 4 may the unchanged cost builder SHA256
   `617AF7E526E7D30DBB7C6BBEF7B6DB3740552ABA31BFBFB0F6C42A4C1F8BB3AD`
   build the HYP026 report-bound research-proxy artifact.
7. Only after verified cost may the unchanged unified validator SHA256
   `E9C26801D020298AE6BADD1737ECE5B77778EA34951B99EB3A0B81F47D5E9DE2`
   evaluate the frozen baseline. Exit 0 or the expected economic-falsification
   exit 1 is admissible; operational errors are not.
8. The cost and unified pipeline is replayed from the same captured bytes and
   its normalized economic result must match deterministically.

## Frozen economic gates

- completed trades at least 500;
- each direction at least 30%;
- no calendar year above 30% of trades;
- cadence 2–5 trades per inclusive calendar week;
- PF at least 1.30 after x1 research-proxy cost;
- positive mean net-R at x1 and in every calendar year;
- PF at x1.5 at least 1.25;
- PF at x2 at least 1.00;
- tester drawdown no more than 8%;
- no promotion claim because the cost tier is research proxy.

If the full engineering chain passes but any economic gate fails, HYP027 is an
economic FAIL for this exact strategy mapping and a materially new mechanism
must be preregistered. No filter, session, direction, stop, target, holding,
sizing or threshold rescue is allowed.

## Authority boundary

The comparator may read the sealed HYP026 outcomes and compute exactly one
frozen baseline economic verdict. MT5, compilation, source-data acquisition,
new orders/fills, optimization, WFA, OOS, holdout, paper, live and deployment
remain unauthorized. Same-ID retry and registry mutation are false.
