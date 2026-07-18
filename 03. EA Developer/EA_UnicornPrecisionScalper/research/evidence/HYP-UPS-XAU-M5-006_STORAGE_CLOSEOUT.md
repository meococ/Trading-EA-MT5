# Storage closeout — HYP-UPS-XAU-M5-006

- Valid run: `20260716_141244`.
- MT5 install, data and tester roots were under the portable `D:` runtime.
- The EA used its Tester file sandbox; `FILE_COMMON` was not used.
- Protected C root checked:
  `C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files`.

Before and after were byte-for-byte metadata-identical:

| Field | Before | After |
|---|---:|---:|
| File count | 137 | 137 |
| Total bytes | 20,008,308 | 20,008,308 |
| Latest write UTC | 2026-07-15T01:21:07.3928996Z | 2026-07-15T01:21:07.3928996Z |
| Metadata SHA256 | `B4C0D81C79DB307A47B2C94A3CA243E9943B133DB9D97C28A510FC02810E63DC` | `B4C0D81C79DB307A47B2C94A3CA243E9943B133DB9D97C28A510FC02810E63DC` |

No C-side file was created or modified, so deletion count is zero. Shared
terminal/account/history data was not touched. The valid evidence run is
1,556,885 bytes, the rejected include-closure attempt is 966,414 bytes, and
the portable Tester tree is 12,114,003 bytes; all are on `D:`.

Evidence hashes:

- Before snapshot SHA256:
  `0F522EDB77F60A20632451154F727762644E6EF666F2F94BE997CABFC7CFCBF1`.
- After snapshot SHA256:
  `48EC6F58D9CA164D9AA5C4C40331D7D4E2783D8EFD9A1A67A81F2631C43291E1`.
