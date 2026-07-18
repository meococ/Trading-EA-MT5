# GLDFlow storage closeout — HYP-GLDFLOW-XAU-M15-002

- Probe runtime: MT5 Python API initialized against
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent\terminal64.exe`
  with portable mode.
- Terminal data path readback:
  `D:\Trading EA MT5\02. AlphaFactory\runtime\mt5-portable-fivepercent`.
- Retained workbook, prereg, script and probe artifact are on `D:`.
- `FILE_COMMON` was not used. `commondata_path` remains on C by MT5 design and
  was treated as protected shared state.
- One D-owned terminal process was stopped after API shutdown; terminal process
  count at closeout: 0.

Protected C-root comparison:

| Root | Files before/after | Bytes before/after | Metadata identical |
|---|---:|---:|---|
| `...\\Terminal\\Common\\Files` | 137 / 137 | 20,008,308 / 20,008,308 | yes |
| `...\\D0E8209F77C8CF37AD8BF550E51FF075\\Tester` | 120 / 120 | 1,260,063,754 / 1,260,063,754 | yes |
| `...\\MetaQuotes\\Tester` | 882 / 882 | 6,847,158,854 / 6,847,158,854 | yes |
| `C:\\ProgramData\\MetaQuotes\\Tester` | 0 / 0 | 0 / 0 | yes |

Snapshot SHA256:

- before: `FB45110EABC78E6C3177E77F9D9DEA6C25A39B69179B4BC5E4D15E6807DC43FD`
- after: `E5ECE8AC6ED59773E917BC9D8E8A59D49DEF4FDFCF714E1D5F22EAA348CF8A7F`

No C file was created, deleted, moved or reclaimed.
