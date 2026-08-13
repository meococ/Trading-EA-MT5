# HYP-GC-OFI-INNOV-XAU-M5-001 — acquisition engineering closeout

Status: `PARK_ACQUISITION_ENGINEERING_FAILURE_DEFINITION_STREAM_TRUNCATED`.

This is not a source-quality or economic verdict. No XAUUSD price, return,
forward bar, PnL, MQL5, MT5, optimization, validation, paper or live surface was
opened.

## Exact execution

- Acquisition ID: `GCOFI001-Q1-2019-SOURCE-PILOT-001`.
- Fresh quote: USD `8.955708209425`, `343488960` billable bytes.
- Completed paid payload: `tbbo`, `107311267` file bytes, `4292841` records,
  SHA-256 `6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB`.
- The TBBO DBNv3 metadata binds `GLBX.MDP3 / tbbo` and maps `GC.v.0` to raw
  instrument IDs `32257`, `14651`, and `142620` over the frozen Q1 window.
- Second attempted request: `definition`. Databento emitted reduced-quality
  warnings for at least `2019-01-15`, `2019-02-22`, and `2019-03-13`, then the
  SDK raised `BentoError`.
- Preserved partial: `135` bytes, SHA-256
  `E254836C3F3E4CCB840F7D68956BFF2C79905FB6390C2C448393C46B597EFB13`.
  Local DBNv3 decode fails `UnexpectedEof while decoding metadata`; it is not a
  valid source payload.
- `status` was never requested. Completed paid calls: `1`; paid attempts: `2`.

## Frozen evidence

- Live acquisition plan SHA-256:
  `EC9A22A43EFFD58809378C6E8798C894E71759873861CA70D17438D310495231`.
- Stopped manifest SHA-256:
  `5919A7B2A8240EA7E755C69A16500FF9659A95C6898E6D9C9A1E58EB442EA21E`.
- No `paid_acquisition_receipt.json` exists because the three-schema source
  contract did not complete.

## Boundary and successor

The same hypothesis/acquisition ID must never make another remote call. The
valid TBBO payload is reusable by hash only. A fresh successor may use the
outcome-blind continuous-symbol mapping already embedded in the TBBO metadata,
quote `definition` and `status` for those three raw instrument IDs, and acquire
only the missing reference schemas under a separately frozen plan. It must not
download TBBO again or open target outcomes.
