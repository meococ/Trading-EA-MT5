# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-007 — source reconciliation plan

Status: frozen before economic/outcome access. No network or spending is authorized.

The Owner's standing sub-USD10 authorization existed in the current task before the
HYP004/005 acquisitions, but a competing governance process operated without the full
thread and quarantined them. Preserve those incident records. This successor may use
only the following independently reverified evidence:

- parent HYP004 manifest SHA-256
  `FD487BAB551F5C9C14002261DDA8B6C3BD7911F608E26C09A0A4DC83D93709FC`;
- child HYP005 manifest SHA-256
  `13693E3E291A5E5F85152FB42264E3BB8879D0595DEB5406C642FCE0AC7F248F`;
- child receipt SHA-256
  `181A64D3DFD1806DB4877FF8559F9857E2020178D0576483FED2564C8A601249`;
- combined source ledger SHA-256
  `4DE647CB8CC39F5CD26D10D844C11F1B5A493DAF7C69F2CB633AB361912326F0`.

For all 319 `COMPLETE` rows, resolve every manifest path under the workspace, rehash
raw and analysis files, and require exact event identity/direction agreement with the
combined ledger. Never inspect or use `.partial` files. Freeze eight ambiguous, two
unavailable and one semantic-invalid event as direction zero. Require 329 ordered
unique IDs, 318 semantic passes, 146 continuation / 172 reversal, and 162 long / 156
short / 11 zero directions.

On pass, emit a minimal reconciled source ledger containing no target prices or returns
and a receipt binding every input/output hash. This permits a separate frozen economic
preregistration; it does not itself authorize MQL5, MT5, validation, paper, promotion,
or live trading.

