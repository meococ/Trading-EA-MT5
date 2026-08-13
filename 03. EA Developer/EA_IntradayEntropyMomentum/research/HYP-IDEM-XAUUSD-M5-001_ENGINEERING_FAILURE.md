# HYP-IDEM-XAUUSD-M5-001 — engineering failure, no economic verdict

Verdict: `KILL_ENGINEERING_JOURNAL_TRUNCATED_CLOSE_RETRY_SPAM_NO_ECONOMIC_VERDICT`

The sole baseline attempt created AlphaFactory run `20260811_134254`, but the
data-quality gate stopped before analysis because the tester journal hit the
frozen 4 MiB raw-delta cap. The manifest reports `files_read=3`,
`bytes_read=4194304`, and `truncated=true`; no AlphaFactory analysis directory
or admissible PF/expectancy result was produced.

The captured tail identifies the bounded implementation defect. Position
`#1028` was still open after the 20:00 UTC flatten boundary while the XAUUSD
market was closed on 2022-01-18. `ManagePosition()` called `PositionClose()` on
every tester tick, repeatedly returning broker retcode `10018` and flooding the
journal before the final `IDEM001_SUMMARY` could be captured.

This does not say whether the entropy signal has edge. The exact attempt is
consumed and may not be retried. `HYP-IDEM-XAUUSD-M5-002` is a fresh engineering
revision that preserves the source-passed signal and all frozen economic
parameters, but retries a required flatten at most once per native M5 bar and
emits direct close-attempt/reject counters.

Bound evidence:

- task SHA256: `8A37AFA4C5B2838E61A1612C8769A3D7D4760B37DF23AEECAAF9A3EC20C0E84C`
- contract receipt SHA256: `31E921C8BBA85B321A6DB7B72547AC747D64EB473C4B0447427F5F6F8E3D2D82`
- run manifest SHA256: `8F2FA2309B557515FD106B89B136F215D08B100A1B89FD730613DF8EC2A43B93`
- source snapshot SHA256: `3B83468B173E11F2BC72EDC26AD6634EE902566BFB81CA92F9CDACBE2DA3DC30`
- journal export SHA256: `5158E36640F9527DEAA37E62552B4272703FC04AB67DED2A86466324BBAB04DC`
- report SHA256: `77F1D591944B9392448FAA48418C631308DEBDDA96699079C0D1740AE215D622`

The report exists only as engineering evidence that MT5 ran; its outcomes are
not opened for research decisions, tuning, or promotion.
