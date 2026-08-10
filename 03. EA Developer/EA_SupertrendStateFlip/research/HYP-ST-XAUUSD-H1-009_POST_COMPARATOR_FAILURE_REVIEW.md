# HYP-ST-XAUUSD-H1-009 - post-comparator-failure review

Status: `PASS_KILL_HYP009`

Review the exact authority-binding failure, confirm that no comparator attempt
was claimed, and decide whether terminal HYP009 plus a fresh comparator-only
HYP010 is the narrowest lawful continuation. No MT5, collection, oracle,
per-bar comparison or economics may be executed during this review.

Independent verdict: exact HYP009 kill is warranted. Collection consumed once;
the comparator failed before claim, so comparator consumption remains zero.
Fresh comparator-only HYP010 is the narrowest continuation.

HYP010 must validate the collection receipt against historical HYP009 authority
row SHA256
`3BAD69ED145D3133AA806792DAD836243F08B9264C2BBB44627F9ACB99882A70`,
then separately bind the terminal HYP009 row. Comparing that receipt with the
latest HYP009 row after terminalization would be incorrect. HYP010 must use a
fresh comparator ID/root and cannot repeat collection, MT5 or compilation.
