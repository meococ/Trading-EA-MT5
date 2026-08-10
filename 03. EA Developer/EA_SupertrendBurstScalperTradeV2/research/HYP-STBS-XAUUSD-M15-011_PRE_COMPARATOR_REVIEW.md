# HYP011 pre-comparator independent review

Verdict: `PASS_PRE_COMPARATOR`

Independent review found no fatal blocker on the final pre-authority package:

- preregistration SHA256 `8DBBFD6670F53CE4D4B353F8B5947E747B0B3996A4EC335383C22CDE5F0C15C5`;
- comparator SHA256 `F2EF57E25D049450FD887D7E6F3B6D0FAE51CC99E5FBAD2762D0B32187CE35D8`;
- focused/golden-path test SHA256 `E7C221F86333D955AC0352A92C8430C5F0DA1149568FCEEA72821340CBA99A7B`;
- `.gitignore` SHA256 `F2A63B60F52702630A3B71E697666C3D970F7585043D552FEE76A9E05AC7EEAA`;
- terminal HYP010 raw-row SHA256 `D951D4D552BD8BFE4CE197047647FCDD99DA825FA605001B81727634EF26AD74`.

The exact summary adapter requires the canonical hash-bound path, exactly one leading UTF-8 BOM, no second/interior BOM, strict UTF-8 and one JSON document. Its `Path.read_text` hook is exact-path scoped and restored in `finally`; the frozen parent callable is captured before monkeypatch, preventing recursion.

The comparator claims before registry/dependency/run reads, imports the complete HYP010/HYP009 runner/packet-receipt/oracle/run-artifact surface into its receipt, de-duplicates resolved paths, rejects conflicts, performs deterministic dual replay and final-rehashes every input. Success/failure terminals are durable and same-ID retry is false.

Only `artifact_collection_authorized` and `comparator_execution_authorized` may be true. MT5, compilation, trades, outcomes, performance, economics, optimization, validation, holdout, promotion, paper/live, network/paid, retry and registry mutation remain false.

This authorizes exactly one `STBS011-COMPARATOR-001` engineering comparison. It does not authorize or imply PF, expectancy, cost validity or deployment.
