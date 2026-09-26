# MIGRATION_GATE - written by the Lead only (LEAD_RULINGS R72 s72.2)

A structural engine step may land ONLY if it is listed OPEN below.
Build reads this file before every such landing. A landing without OPEN is reverted and logged "ESCALATE:".
Flagged experiments ordered by a ruling follow the normal keep rule and are not governed by this file.
Every OPEN landing: flag OFF == parent byte-for-byte on the canonical set (R75 s75.6: the 623 cached TUNE windows; objects + cand_log + events), suite of record 72/72, and an EVAL-AUDIT verification before the next step lands.

Updated: 2026-09-23 07:08Z (R75)

| step | status | note |
|---|---|---|
| A0 identity oracle | DONE | extend canonical with score/priority/touches (EVAL-AUDIT, R72 s72.5b) |
| A1 kernel.py | DONE | 623/623 + suite 72/72 |
| A2 ObjectStore | DONE | verified by EVAL-AUDIT 05:37Z (tree 2d497427) |
| A3 FamilyPipe shells | DONE | pickle-recursion fix 06:37Z (tree 2e8a7007) pending EVAL-AUDIT identity check (R75 s75.4) |
| A4 round() split | DONE | verified 05:37Z |
| A5 c.fam shadow | DONE | verified 05:37Z |
| A6 retire family order | CLOSED | not a pure move; may return only as a measured arm |
| B1 shadow views | OPEN | review OK (ARCH_REVIEW_REV2 06:15Z) |
| B5 EventBox relocation | OPEN | review OK; pure move |
| B4 pinned dispatch | OPEN-AFTER-PATCH | land only after the two literal-order patches of REQ s26 are written into the B4 spec |
| B6 typed events | CLOSED | FIX: payload clarifications (veto re-resolve, parent type pin, relabel scan replay) |
| B7 edge board | CLOSED | FIX: one rebuild-boundary rule; stand_aside non-consumer note; _near_structure window bound |
| B2 -> arm C1 | n/a | measured arm, not a gate item |
| B3 -> arm C3 | n/a | measured arm; needs a new ruler-visible metric + canonical tuple extension |
