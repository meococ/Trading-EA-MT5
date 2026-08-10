# HYP-STBS-XAUUSD-M15-024 — Pre-MT5 authority failure

## Verdict

`KILL_PRE_MT5_MISSING_PRE_EXECUTION_HARNESS_ADDENDUM_BINDING_NO_ATTEMPT_NO_ECONOMIC_VERDICT`

The valid HYP024 screened registry row has raw-row SHA-256 `20B7285DFF78E85019B73E626C5850D637FBABDC947F377CC383B9D14D02DC4D`. It binds the exact packet `F95F4CD94EE4E4A4AC7B56637E472909D51F0300C9B78DB42A976B2F2F2F51AC`, packet start `C76198AE2F71AFB2A543F63685248A92D784233216CC16080A3FB698293A74FB`, packet terminal `BC5C7B00554E953DAE868AB5F2F3D45E117C8496FE208279BA2C9E9020B040CD`, runner `5EFEA594E1A8D7625DE4F8F746B955CD3692ADFF91C8C6B46988B94EACA9A64B`, and the independent post-packet review `3184DF18155E17F8C727B304D575FF407E32ECC6701EE090988EAB6666139858`.

The exact non-executing runner invocation returned exit code zero but reported `DRY RUN. EXECUTION BLOCKED by 1 contract issue(s).` The sole blocker was:

`Model0 economic authority does not bind the current pre-execution harness addendum bytes.`

HYP024 does bind the journal-budget addendum `C0AD425D1F368A41FE740E3EC22D1CF823F088005848BF14789C6EFFDD3AEF21`, but it does not bind the separate generic fields `validation.pre_execution_harness_addendum_path` and `validation.pre_execution_harness_addendum_sha256` required by the hash-bound runner. The current append-only validator permits no lawful `screened -> screened` transition that adds those fields: HYP024 already has the one-shot harness version, and the receipt-correction exception may add only its exact correction path/SHA pair. Changing the already-bound runner or broadening the validator after authority would weaken the evidence boundary and is forbidden.

The Model0 attempt root `02. AlphaFactory/runtime/model0_economic_attempts/HYP-STBS-XAUUSD-M15-024/STBS024-MODEL0-TRAIN-001` is absent. The dry-run did not claim an attempt and did not invoke Alpha compile, MT5, market data, orders, deals, outcomes, returns, PF, costs, validation or holdout. Packet build consumed one attempt; MT5 and run-compile consumed zero.

This failure radius is only HYP024 prelaunch authority completeness. It does not reject the V11 strategy, telemetry revision, four-MiB journal contract, or market edge. The integrity-preserving continuation is a fresh outer governance child that reuses the unchanged V11 source/package and explicitly freezes the missing pre-execution harness addendum before its first authority row. Same-ID retry, in-place row mutation and a post-authority runner patch are forbidden.
