# Treasury TIC announcement mechanism terminal reconciliation

Date: 2026-08-13 (Asia/Saigon)

Scope: outcome-blind primary-source and mechanism review only. No FX/XAU price,
return, backtest, EA, purchase, trial or vendor contact was opened.

## Verdict

`KILL_TIC_ANNOUNCEMENT_MECHANISM_NO_MODERN_PREREGISTRABLE_TRANSFORM`

The source archive remains useful and first-vintage reconstruction is possible,
but the 2014+ 16:00 Eastern publication object cannot be converted into a legal
EURUSD/major-FX hypothesis. The first fatal gate is transform identity: no
primary source defines a sign-preserving month-on-month percentage transform
for a signed net-flow series when the prior value is negative, changes sign or
is zero.

This supersedes the earlier scoped verdict
`REOPEN_SOURCE_ONLY_BUT_HOLD_MECHANISM`. It closes only the TIC announcement
mechanism; the overall EA goal remains `ACTIVE / UNMET`.

## Primary evidence

### Treasury clock, lag and revision contract

U.S. Treasury's release-date page states that monthly TIC releases changed from
normally 09:00 Washington time to 16:00 Eastern beginning 2014-09-16. Since the
2021-03-15 release, the data have a 1.5-month lag. January, April, July and
October releases revise the past year; the other months revise the prior three
months.

Source:
https://home.treasury.gov/data/treasury-international-capital-tic-system/release-dates-of-tic-data

This establishes the clock and revision risk, not an economic sign or horizon.

### BIS result is old-regime and algebra-incomplete

BIS 75th Annual Report, chapter V, Table V.2 covers January 2002 through April
2005. It describes the TIC regressor as a month-on-month percentage change in
net foreign purchases of U.S. securities and reports that higher total
purchases were associated with USD appreciation while higher official
purchases had the opposite sign.

Source:
https://www.bis.org/publ/arpdf/ar2005e5.pdf

The paper does not define the denominator treatment for negative, sign-changing
or zero prior net purchases. It also belongs to the former 09:00 release regime
and reports daily changes, not a closed-bar 16:00 entry/exit window.

### The available Federal Reserve normalization is a different object

Federal Reserve IFDP 2014-1103 discusses bilateral equity "net-net" flows
normalized by the trailing 12-month average absolute change in foreign stock
ownership. It explicitly treats contemporaneous within-month flow/FX
correlation and says the timing cannot disentangle return chasing from price
pressure.

Source:
https://www.federalreserve.gov/pubs/ifdp/2014/1103/ifdp1103.htm

That transform is not the aggregate first-vintage TIC announcement field and
cannot be transplanted to repair the BIS formula after source intake.

### February-2023 methodology break cannot be pooled away

Federal Reserve FEDS Note dated 2025-10-15 states that legacy holdings and TIC S
transactions were difficult to reconcile. Its recommended consistent
transactions series uses Bertaut-Judson estimates through January 2023 and new
measured expanded-SLT transactions thereafter. The expanded SLT changed the
collection, fields and sign conventions and began publishing the new data in
2023.

Source:
https://www.federalreserve.gov/econres/notes/feds-notes/measuring-u-s-cross-border-securities-flows-out-with-the-old-in-with-the-new-20251015.html

This is a research reconstruction, not a first-vintage release transform and
not authority to pool legacy Form S with expanded SLT for an announcement EA.

## Why no legal revision remains

1. Choosing difference, absolute denominator, signed-log, threshold, surprise
   proxy or no-trade rule now would invent the transform after source review.
2. No official expectations series exists in the inspected source, so the raw
   release cannot be converted into a preregistered surprise object.
3. The primary sign evidence is tied to the old 09:00 regime and a daily return;
   it does not define a 16:00 closed-bar entry or a Friday-flat exit.
4. Pooling across the 2023 field break violates the first-vintage data contract;
   splitting the already-small monthly sample leaves no evidence-backed modern
   horizon.

No threshold, denominator, session, symbol, direction or holding-period child
is authorized from this lane.

## Grok Build review

Grok received only the primary-source facts above and was explicitly forbidden
from accessing market outcomes, writing code/files, backtesting, purchasing or
inventing thresholds. It returned:

`TIC_MECHANISM_TERMINAL: gate 1 — no primary algebra defines MoM % on first-vintage npr_history.csv column[3] (or the post-2023 SLT field) when the prior net is zero or sign-changing; BIS AR 2005 Table V.2 names that percent-change input but gives no safe formula and is 09:00-era only, while FEDS Note 2025-10-15 authorizes a Bertaut-Judson→SLT reconstruction rather than a first-vintage transform or S/SLT pool, so TRANSFORM_UNRESOLVED cannot be lawfully revised.`

Lead accepts this as advisory corroboration. The primary sources and local
field/clock receipt remain the authority.

## Registry boundary

No terminal row was appended because the live candidate registry identity is
currently in a fail-closed restoration hold. This receipt is the authoritative
source-mechanism verdict until the canonical registry is recovered and a
deliberate append can be reviewed. See:
`04. Memory/research/20260813_CANDIDATE_REGISTRY_CONCURRENT_DRIFT_HOLD.md`.

