# HYP-ST-XAUUSD-H1-011 - post-failure review

Status: `PASS_KILL_HYP011`

Review the exact physical-versus-logical Orders header mismatch. Confirm ST011
consumed before full parity and whether fresh HYP012 may accept only the frozen
11-cell header with colspan vector `[1,1,1,1,2,1,1,1,2,1,1]` plus one empty
spacer and no other row. Do not execute comparator, oracle/audit, MT5, compile
or economics during review.

Independent verdict: exact HYP011 kill is warranted; comparator consumed once,
with only start/failed-terminal artifacts and no full-row parity/economics.
Fresh HYP012 is legal after terminal HYP011.

HYP012 must retain td attributes, default absent `colspan` to 1, require exact
physical vector `[1,1,1,1,2,1,1,1,2,1,1]` with logical sum 13, all 11 header
cells bold, exactly one empty spacer td and exactly two section rows. Every
malformed/extra cell or row must fail; funding/report/analyzer/sealed-chain and
zero-authority contracts remain unchanged.
