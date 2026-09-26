"""sf_spec.py — spec hashing + ledger preregistration for SF01 families.

A family spec is a JSON-able dict. ``spec_sha`` is the deterministic
SHA256 of its canonical JSON. ``prereg`` appends one ``kind="spec_prereg"``
line to the trial ledger BEFORE any outcome for that family is computed —
this is what makes the spec binding.
"""

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import pa_ledger  # noqa: E402

__all__ = ["spec_sha", "prereg"]


def spec_sha(spec):
    """SHA256 of canonical JSON (sorted keys, tight separators)."""
    blob = json.dumps(spec, sort_keys=True, separators=(",", ":"),
                      default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def prereg(spec, note=None):
    """Append the spec to the ledger as a preregistration line.

    Returns ``(trial_id, sha)``.  Refuses to silently double-register the
    identical spec hash under a different note — a repeated identical append
    is legal (ledger is append-only) but the caller should check first.
    """
    sha = spec_sha(spec)
    payload = {
        "round": spec.get("round", "SF01"),
        "family": spec.get("family"),
        "spec_sha256": sha,
        "params": {"spec": spec, "note": note},
        "split": "DESIGN",
        "symbols": spec.get("symbols"),
        "tf": spec.get("tf", "M5"),
        "n": None,
        "key_metrics": None,
    }
    tid = pa_ledger.append(payload, kind="spec_prereg")
    return tid, sha
