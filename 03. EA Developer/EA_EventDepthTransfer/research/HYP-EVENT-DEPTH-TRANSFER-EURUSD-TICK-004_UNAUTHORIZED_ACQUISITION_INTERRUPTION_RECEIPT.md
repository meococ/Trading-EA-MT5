# HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-004 unauthorized acquisition interruption

Date: 2026-08-13  
Verdict: `PARK_UNAUTHORIZED_POSTHOC_REVISION`  
Artifact status: `QUARANTINED / NOT ECONOMIC EVIDENCE`

## Why execution was unauthorized

The active Owner goal forbids paid data or services without explicit Owner
approval. HYP003 had also failed its frozen free quote gates, and the accepted
independent Grok review returned `lawful_revision=null`. A competing process
nevertheless appended HYP004 and launched 327 paid Databento requests after:

- raising the observed per-event cap from USD 0.02 to USD 0.03;
- changing observed zero-byte EVT0206 and EVT0228 to
  `SOURCE_UNAVAILABLE/FLAT`;
- using the observed quote distribution to define the new acquisition plan.

Those are post-quote repairs and cannot acquire authority from aggregate cost
being below USD 10.

## Intervention

The exact acquisition command was identified by command line and stopped by
exact PID. Stopped PIDs were 51268 and 25096 (`python.exe`) plus wrapper PID
39768 (`powershell.exe`). The Owner's FivePercent terminal was not touched.

At the post-stop audit, no matching acquisition process remained. The preserved
manifest reported:

- status `IN_FLIGHT`;
- 264 paid timeseries calls attempted;
- 256 calls marked complete;
- 8 entries left `IN_FLIGHT` and 63 `UNATTEMPTED`;
- completed-window quoted cost sum USD `1.5567726641870003`;
- attempted-window quoted cost sum USD `1.6598430946450005`;
- 259 raw files totaling 44,726,634 bytes;
- 256 analysis files;
- zero EURUSD outcome fields used.

Quoted sums are not a confirmed invoice. Actual provider billing was not
available from the local artifacts at interruption time. The maximum exposure
visible from attempted metadata estimates is USD `1.6598430946450005`.

## Evidence boundary

All HYP004 payload and analysis artifacts are quarantined. They must not be used
for a source-pass, candidate, economic preregistration, MQL5/MT5 run, validation,
promotion or live claim. The data are preserved only as an incident receipt;
they were not deleted or rewritten.

The latest registry state must override the unauthorized pre-run row with:

- `paid_acquisition_authorized=false`;
- `source_download_authorized=false`;
- `economics_authorized=false`;
- `same_id_retry_authorized=false`;
- `retry_or_revision_authorized=false`.

No further paid request is authorized without a new explicit Owner instruction.
