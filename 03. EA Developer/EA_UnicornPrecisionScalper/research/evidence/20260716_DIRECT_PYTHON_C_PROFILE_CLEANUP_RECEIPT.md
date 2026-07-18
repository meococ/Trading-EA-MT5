# Direct Python MT5 C-profile cleanup receipt

## Trigger

A read-only Python inventory was started against the D-side FivePercent
terminal without the bridge `portable=True` flag. MT5 reported a non-portable
data path under
`C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\4F957FF7D1BAC510136444153DB1E696`.
The result was rejected immediately and was not used as research evidence.

## Bounded cleanup

- The only `terminal64.exe` process was traced to the D-side AlphaFactory
  executable and stopped before cleanup.
- `origin.txt` matched
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent`.
- Before deletion: 1,137 files / 360,407,524 bytes; metadata SHA256
  `0D26E7D49529792E9CE649EE940995FAE65E6A4CDB9D2776CD0FDA03C3987613`.
- After deletion: the run-created profile did not exist; zero files / zero
  bytes.
- Protected `Terminal\Common\Files` was not deleted or modified. Final state:
  137 files / 20,008,308 bytes; metadata SHA256
  `B4C0D81C79DB307A47B2C94A3CA243E9943B133DB9D97C28A510FC02810E63DC`.
- No terminal process remained after cleanup.

## Evidence

- `20260716_DIRECT_PYTHON_C_PROFILE_BEFORE.json`
- `20260716_DIRECT_PYTHON_C_PROFILE_AFTER.json`
- `20260716_ALERT_FIRST_CASEBOOK_V121_STORAGE_FINAL.json`

Future direct Python bridge calls must set `portable=True` and must verify the
returned `TERMINAL_DATA_PATH` before reading market data. Casebook collection
also fails closed inside the EA unless that path begins on `D:`.
