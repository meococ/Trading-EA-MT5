#!/usr/bin/env python3
"""STUB — Structural V6 probe script relocated / stem protected.

The original V6 board (impulse halfback / EUR double-inside / D1 gap fade)
was overwritten by a multi-symbol batch that briefly reused this stem.
That multi-symbol board is now **V7**:

  preflight/20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V7.py

V6 JSON at this stem is a RESTORED_ARCHIVE_POINTER (metrics from registry).
Do not re-run a probe writer into this path.
"""

from __future__ import annotations


def main() -> int:
    raise SystemExit(
        "REFUSE: V6 stem is archive-protected after collision. "
        "Use 20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V7.py for multi-sym board, "
        "or a new V8+ stem for fresh probes."
    )


if __name__ == "__main__":
    raise SystemExit(main())
