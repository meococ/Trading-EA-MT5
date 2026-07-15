#!/usr/bin/env python3
"""Wait for QFSI capture 005 to exit, then launch 006 (4h) without killing Real terminal.

Safety: read-only capture only; expected-server FivePercentOnline-Real; no live orders.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
TOOLS = ROOT / "02. AlphaFactory/tools"
EVID = ROOT / "02. AlphaFactory/evidence/execution/FivePercentOnline-Real"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
LOG = PRE / "20260714_QFSI_006_WATCHER_LOG.jsonl"
PREV_PID = 35892
CAPTURE_SCRIPT = TOOLS / "execution_data_qfsi_nolive_capture.py"
DURATION = 14400  # 4 hours
CAPTURE_ID = "20260714_QFSI_REAL_006_ACCUMULATE"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(event: str, **kwargs) -> None:
    row = {"ts": utc_now(), "event": event, **kwargs}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)


def pid_alive(pid: int) -> bool:
    try:
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        # fallback
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select -Expand Id"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (r.stdout or "")


def terminal_alive() -> bool:
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Process terminal64 -ErrorAction SilentlyContinue | Select -Expand Id"],
        capture_output=True,
        text=True,
        check=False,
    )
    return bool((r.stdout or "").strip())


def main() -> int:
    log("watcher_start", prev_pid=PREV_PID, capture_id=CAPTURE_ID, duration_sec=DURATION)
    # wait for 005
    while pid_alive(PREV_PID):
        log("waiting_005", prev_pid=PREV_PID, terminal_alive=terminal_alive())
        time.sleep(30)
    log("005_exited", prev_pid=PREV_PID)

    if not terminal_alive():
        log("abort_no_terminal", reason="terminal64 not running — will not invent login")
        return 2

    # Capture script writes directly into --out-dir (no auto subfolder).
    out_dir = EVID / CAPTURE_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys_executable(),
        str(CAPTURE_SCRIPT),
        "--expected-server",
        "FivePercentOnline-Real",
        # Book-first (RR2/SB/Spark = USDJPY) then contract gate symbols.
        "--symbols",
        "USDJPY",
        "EURUSD",
        "GBPUSD",
        "XAUUSD",
        "--capture-id",
        CAPTURE_ID,
        "--out-dir",
        str(out_dir),
        "--duration-sec",
        str(DURATION),
    ]
    log("launching_006", cmd=cmd)
    # Detach: start without waiting
    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    if hasattr(subprocess, "DETACHED_PROCESS"):
        creationflags |= subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    proc = subprocess.Popen(
        cmd,
        cwd=str(TOOLS),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags or 0,
        close_fds=True,
    )
    log("006_started", pid=proc.pid, capture_id=CAPTURE_ID)
    # write receipt stub
    receipt = {
        "schema_version": "sonic_qfsi_006_launch_receipt.v1",
        "created_at_utc": utc_now(),
        "status": "QFSI_006_LAUNCHED_AFTER_005",
        "prev_capture": "20260714_QFSI_REAL_005_POSTAUTH",
        "prev_pid": PREV_PID,
        "new_capture_id": CAPTURE_ID,
        "new_pid": proc.pid,
        "duration_sec": DURATION,
        "expected_server": "FivePercentOnline-Real",
        "do_not_kill_real": True,
        "mode": "PASSIVE_READ_ONLY_NO_LIVE_ORDERS",
    }
    (PRE / "20260714_QFSI_006_LAUNCH_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


def sys_executable() -> str:
    import sys

    return sys.executable


if __name__ == "__main__":
    raise SystemExit(main())
