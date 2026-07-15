#!/usr/bin/env python3
"""Breakaway bootstrap for QFSI 007 long watcher — survives parent shell exit."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
DETACHED_PROCESS = 0x00000008

PY = r"C:\Program Files\Python312\python.exe"
WATCHER = r"d:\Trading EA MT5\02. AlphaFactory\tools\qfsi_007_long_accumulate_watcher.py"
OUT = Path(
    r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\preflight\20260715_QFSI_007_WATCHER_STDOUT.txt"
)
ERR = Path(
    r"d:\Trading EA MT5\03. EA Developer\EA_SonicR\research\preflight\20260715_QFSI_007_WATCHER_STDERR.txt"
)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stdout = open(OUT, "a", encoding="utf-8")
    stderr = open(ERR, "a", encoding="utf-8")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stdout.write(f"\n=== RELAUNCH_BOOTSTRAP {stamp} ===\n")
    stdout.flush()
    flags = CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB | DETACHED_PROCESS
    proc = subprocess.Popen(
        [PY, WATCHER],
        cwd=r"d:\Trading EA MT5\02. AlphaFactory\tools",
        stdout=stdout,
        stderr=stderr,
        creationflags=flags,
        close_fds=False,
    )
    print(proc.pid)


if __name__ == "__main__":
    main()
