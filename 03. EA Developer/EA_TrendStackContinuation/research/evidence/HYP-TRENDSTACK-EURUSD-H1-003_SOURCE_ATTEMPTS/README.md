# HYP-003 source attempts

This directory is the immutable parent for the single HYP-003 production
source-attempt evidence root.

Each child name must equal the packet-bound `source_attempt_id`. The supervisor
creates the child and `attempt_started.json` with create-new semantics before
the first raw-source open. A child or marker must never be deleted, overwritten,
resumed, or reused. Its existence means that attempt ID is consumed even when
terminal evidence is absent because of a crash.

This parent contains no price, economic, validation, holdout, or MT5 authority.
