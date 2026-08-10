# HYP-ST-XAUUSD-H1-007 — terminal MT5 prehistory failure

Verdict: `KILL_MT5_PREHISTORY_UNAVAILABLE_AND_LOCALIZED_HQ_PARSE`

The sole `ST007-MT5-001` compiled and launched MT5. The zero-trade audit then
failed in `OnInit` before opening FILE_COMMON: although the terminal reports
server history from 2004-06-11, the tester cache for a 2018 start exposed only
H1 bars from 2017-01-03. The frozen formula requires inception state from
2004-06-11 07:00, so it correctly emitted
`ST003_FATAL|prehistory_unavailable|copied=5860|first=2017.01.03 01:00:00`
and returned nonzero.

AlphaFactory subsequently encountered the localized report token
`0% số ticks that`; its strict generic numeric parser could not parse the
localized suffix. This is secondary: zero ticks and the fatal journal already
prove the run did not reach the parity scan.

Evidence:

- attempt start/stdout/stderr/terminal SHA-256:
  `2CFFF47409753AC108BDCCCEF36DCA630404701FA2CA6794570F32D15528B473` /
  `FCC8A66C6AC9C3266E6171499DB5CC6EF316FC0F5DC7F46816E3B6583D0C54B0` /
  `422A431B8A79DBE2F0BAD5815E7254B9D35D7BE1E14C0DCF97022D82BF045A5C` /
  `6003410F92D94B31695D322777A7896B4B75C3F6D7828A8C7AE09C31CBCBFFB8`.
- Alpha run: `20260809_060651`; manifest/report/journal SHA-256:
  `BDD1C9A983532425C196F48C033BCFB30BE11FDC562D824CF88C8D9947666D35` /
  `C9A33DB3EFF771FF705FD41EEC316DF28FBD933C66F1C333BFA3945BFEFB4781` /
  `2A2380BA881FDBA5066A7A5E32A2F076E7882AA1E85D0240C908D26331A7AF68`.
- run source / run EX5 SHA-256:
  `C8C222487769439DC8FB9272C049BE30928FED5315A64DD1CAD440B500A13D02` /
  `E8C94485B5FFDBC638182BEBCAF3D312B4C3DA5DAB35FD96D15AB596E6F35F48`.

No CSV, persisted parity row, order, deal, outcome or economic metric exists.
Same-ID retry, collection and comparator are forbidden. This run also proves
that separately compiled EX5 bytes are not a stable equality surface even for
the same source; future correctness must bind source snapshot, compile 0E/0W,
run manifest and run-local EX5, not demand equality with an earlier EX5.

A fresh revision may start the tester early enough to expose the exact 2004
inception history, carry state continuously, and persist rows only from the
frozen 2018 design start. It must also parse only an anchored leading percentage
from localized History Quality text while preserving the strict `>97` gate.

