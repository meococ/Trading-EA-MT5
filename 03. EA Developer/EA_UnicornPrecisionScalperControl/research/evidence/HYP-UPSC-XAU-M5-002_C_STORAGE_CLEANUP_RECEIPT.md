# C-drive storage cleanup receipt

- Scope: Unicorn Model-0 session on 2026-07-16.
- Portable terminal/history/tester root:
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent`.
- HYP-UPSC runs created no lifecycle, Tester or Agent payload on `C:`.
- Two legacy HYP-003-invalid `FILE_COMMON` sidecars were found on `C:`. They
  were hash-verified into
  `research/evidence/c_common_archive/20260716_HYP_UPS_003_INVALID/` before
  deletion from Common Files.

| File | Bytes | SHA256 |
|---|---:|---|
| `XAUUSD_RunMeta_HYP-UPS-XAU-M5-002_54728593.json` | 213 | `57FDA2B7030C493AE27C4E157B434E798B48B00C28B10878111E0A78F8BF8F65` |
| `XAUUSD_LifecycleTrades_HYP-UPS-XAU-M5-002_54728593.csv` | 47,033 | `E8D63E91C845A057E60CD7BD2357D9AA4D66D143B40623A1BDE99AD48B8E3D0D` |

Deletion is limited to those two exact Common Files paths. Shared terminal
profiles, accounts, history and unrelated run data remain untouched.

## Verified result

- Both exact source paths are absent after deletion.
- The two archived copies remain SHA256-identical to the table above.
- `C:\Users\ADMIN\AppData\Roaming\MetaQuotes` changed from 6,304 files /
  30,718,808,711 bytes to 6,302 files / 30,718,761,465 bytes: exactly two
  files and 47,246 bytes removed, matching this receipt.
- `C:\Users\ADMIN\AppData\Local\MetaQuotes` remained absent.
- The portable FivePercent runtime grew only on `D:` during the Model-0
  session. Its total is observational because other research lanes shared the
  workspace concurrently.
- Before snapshot: `HYP-UPSC-XAU-M5-001_STORAGE_BEFORE.json`.
- After snapshot: `HYP-UPSC-XAU-M5-002_STORAGE_AFTER.json`.
