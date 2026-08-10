# HYP-ST-XAUUSD-H1-010 - pre-comparator review

Status: `PASS_PRE_COMPARATOR`

Review the comparator-only HYP010 package before authority. Confirm that it
hash-loads the frozen HYP009 comparator, reads only the sealed HYP009 collection,
verifies receipt row `3BAD69ED...2A70` as a historical row, separately verifies
terminal HYP009 row `75120889...0B70D`, uses fresh `ST010-COMPARATOR-001`, and
opens no collection, MT5, compilation, mutable source, outcome or economics.

Frozen hashes:

- prereg: `1E48827FE6966049DFCCCE0B80172A61BE3B900F1E7AB0C5B58C2BFF765B512C`;
- comparator wrapper: `434D79CEE674FB19F38F9CFBCDE6E5A2EB0A63F947719B4E78F49DAB5A1C6823`;
- comparator tests: `FFE7C5662745CC083D7758256803DA6CF7A88229FFB09685C13EE0213DCB0C1E`;
- frozen HYP009 comparator dependency:
  `A68CB44C72BAC8BB73BC151C21150E9968826764BFD6EB3580640CBBA7E067E1`.

Verification: Python compilation PASS; focused HYP010 tests `16 passed`; full
Supertrend research suite `88 passed`; candidate registry `804 rows / 312
hypotheses` PASS. HYP010 evidence root is absent.

HYP009 read-scope correction is append-only and frozen at
`C85948D1CBF333A3F57517D9E4D8CDA20F17947759CE20113D22239F1FCB1CFA`.
It discloses that the failed pre-claim HYP009 validator hash-read—but did not
parse—the oracle chain. HYP010 moves every artifact hash read after claim.

Independent verdict: `PASS`. No fatal blocker remains. Disclosure binding,
claim ordering, historical/terminal HYP009 lineage, exact MQL run-snapshot path,
fresh ST010 attempt/root and the zero-economic authority boundary are intact.
