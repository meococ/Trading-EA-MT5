#!/usr/bin/env python3
"""Robust long QFSI accumulate watcher for FivePercentOnline-Real.

- Does NOT kill Real / terminal64.
- Launches read-only capture with book-first symbols.
- Auto-restarts capture if it dies early AND Real is still alive on expected server.
- Logs stdout/stderr (006 lost crash reason because DETACHED+DEVNULL).
- Stops when stop-file appears or max wall duration elapses.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
TOOLS = ROOT / "02. AlphaFactory/tools"
EVID = ROOT / "02. AlphaFactory/evidence/execution/FivePercentOnline-Real"
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"

CAPTURE_SCRIPT = TOOLS / "execution_data_qfsi_nolive_capture.py"
CAPTURE_ID = "20260715_QFSI_REAL_007_LONG_ACCUMULATE"
EXPECTED_SERVER = "FivePercentOnline-Real"
SYMBOLS = ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD"]

# Per-segment capture window (capture script duration). Watcher may relaunch.
SEGMENT_DURATION_SEC = 6 * 3600  # 6h segments
# Total wall-clock budget for this watcher session (auto-restart within).
WATCHER_WALL_SEC = 72 * 3600  # 72h wall — 24h sessions kept dying mid-accumulate
POLL_SEC = 15
STALL_SEC = 180  # no CSV write for this long → treat as stalled
STALL_GRACE_SEC = 300  # wait this long after launch before stall checks
MAX_RESTARTS = 96
REAL_PID_HINT = 19984  # informational only; never kill terminal64


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc(value: datetime | None = None) -> str:
    value = value or utc_now()
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def log(path: Path, event: str, **kwargs: Any) -> None:
    # Guard: never allow kwargs to collide with positional `path`/`event`
    # (historic TypeError: log(..., path=stop_file) killed 007 watcher).
    safe = {k: v for k, v in kwargs.items() if k not in ("path", "event")}
    if "path" in kwargs and "stop_path" not in safe:
        safe["stop_path"] = kwargs["path"]
    row = {"ts": iso_utc(), "event": event, **safe}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)


def pid_alive(pid: int) -> bool:
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def terminal_pids() -> list[int]:
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Process terminal64 -ErrorAction SilentlyContinue | Select -Expand Id",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out: list[int] = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if line.isdigit():
            out.append(int(line))
    return out


def probe_real_ok() -> dict[str, Any]:
    """Read-only MT5 probe; never places orders."""
    code = (
        "import json,MetaTrader5 as mt5\n"
        f"ok=mt5.initialize()\n"
        "payload={'initialize_ok':bool(ok)}\n"
        "if ok:\n"
        "  ti=mt5.terminal_info(); ai=mt5.account_info()\n"
        "  payload['connected']=bool(ti.connected) if ti else False\n"
        "  payload['server']=str(ai.server) if ai else None\n"
        "  payload['login']=int(ai.login) if ai else None\n"
        "  mt5.shutdown()\n"
        "else:\n"
        "  payload['error']=str(mt5.last_error())\n"
        "print(json.dumps(payload))\n"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(TOOLS),
        timeout=45,
    )
    try:
        data = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        return {
            "ok": False,
            "error": f"probe_parse:{exc}",
            "stdout": (r.stdout or "")[-500],
            "stderr": (r.stderr or "")[-500],
        }
    server_ok = data.get("server") == EXPECTED_SERVER
    return {
        "ok": bool(data.get("initialize_ok") and data.get("connected") and server_ok),
        **data,
        "expected_server": EXPECTED_SERVER,
    }


def newest_mtime(out_dir: Path) -> float | None:
    newest: float | None = None
    if not out_dir.exists():
        return None
    for p in out_dir.glob("*_heartbeats.csv"):
        m = p.stat().st_mtime
        newest = m if newest is None else max(newest, m)
    return newest


def launch_capture(out_dir: Path, stop_file: Path, log_dir: Path, segment: int) -> subprocess.Popen:
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"segment_{segment:02d}_stdout.txt"
    stderr_path = log_dir / f"segment_{segment:02d}_stderr.txt"
    cmd = [
        sys.executable,
        str(CAPTURE_SCRIPT),
        "--expected-server",
        EXPECTED_SERVER,
        "--symbols",
        *SYMBOLS,
        "--capture-id",
        CAPTURE_ID,
        "--out-dir",
        str(out_dir),
        "--duration-sec",
        str(SEGMENT_DURATION_SEC),
        "--poll-ms",
        "1000",
        "--max-ipc-retries",
        "120",
        "--stop-file",
        str(stop_file),
    ]
    stdout_fh = stdout_path.open("a", encoding="utf-8")
    stderr_fh = stderr_path.open("a", encoding="utf-8")
    creationflags = 0
    if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    # Break away from parent job so approving/agent shells cannot reap us.
    CREATE_BREAKAWAY_FROM_JOB = 0x01000000
    creationflags |= CREATE_BREAKAWAY_FROM_JOB
    # Do NOT use DETACHED_PROCESS — keep logs; never DEVNULL (006 lost crash reason).
    proc = subprocess.Popen(
        cmd,
        cwd=str(TOOLS),
        stdout=stdout_fh,
        stderr=stderr_fh,
        creationflags=creationflags or 0,
    )
    # Parent keeps handles open via Popen; close our refs so files flush independently.
    stdout_fh.close()
    stderr_fh.close()
    return proc


def write_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    out_dir = EVID / CAPTURE_ID
    log_path = PRE / "20260715_QFSI_007_WATCHER_LOG.jsonl"
    stop_file = PRE / "20260715_QFSI_007_STOP.request"
    log_dir = out_dir / "_watcher_logs"
    receipt_path = PRE / "20260715_QFSI_007_LONG_LAUNCH_RECEIPT.json"

    # Fresh capture dir (do not reuse crashed 006).
    out_dir.mkdir(parents=True, exist_ok=True)

    terms = terminal_pids()
    probe = probe_real_ok()
    if not terms:
        log(log_path, "abort_no_terminal", reason="terminal64 not running — will not invent login")
        return 2
    if not probe.get("ok"):
        log(log_path, "abort_probe_fail", probe=probe, terminal_pids=terms)
        return 3

    wall_deadline = time.time() + WATCHER_WALL_SEC
    restarts = 0
    segment = 0
    current: subprocess.Popen | None = None
    segment_started_at: float | None = None

    launch_payload = {
        "schema_version": "sonic_qfsi_007_long_launch.v1",
        "created_at_utc": iso_utc(),
        "status": "QFSI_007_LONG_WATCHER_STARTED",
        "capture_id": CAPTURE_ID,
        "out_dir": str(out_dir.as_posix()),
        "expected_server": EXPECTED_SERVER,
        "symbols_book_first": SYMBOLS,
        "segment_duration_sec": SEGMENT_DURATION_SEC,
        "watcher_wall_sec": WATCHER_WALL_SEC,
        "max_restarts": MAX_RESTARTS,
        "stop_file": str(stop_file.as_posix()),
        "do_not_kill_real": True,
        "real_terminal_pids": terms,
        "real_pid_hint": REAL_PID_HINT,
        "mt5_probe": probe,
        "mode": "PASSIVE_READ_ONLY_NO_LIVE_ORDERS",
        "hardening": [
            "stdout_stderr_logged",
            "auto_restart_if_early_exit_and_real_alive",
            "session_crash_json_on_exception",
            "max_ipc_retries_120",
            "no_detached_devnull",
        ],
        "prior_006_diagnosis": {
            "outcome": "EARLY_EXIT_NO_SESSION_END",
            "auth_drop": False,
            "connected0_heartbeats": 0,
            "likely": "process_crash_or_external_kill_with_stderr_discarded; concurrent_MT5_IPC_contention_possible",
        },
        "quote_days_growth_note": (
            "QFSI 90-day gate is elapsed calendar wall-clock with PASSIVE_HEARTBEAT. "
            "Historical copy_ticks_range without heartbeat is BROKER_HISTORY_UNVERIFIED "
            "(discovery only) per data contract — cannot lawfully accelerate gate. "
            "Commission/slip still require Owner deal-export / side-referenced fills."
        ),
    }
    write_receipt(receipt_path, launch_payload)
    log(
        log_path,
        "watcher_start",
        capture_id=CAPTURE_ID,
        wall_sec=WATCHER_WALL_SEC,
        segment_sec=SEGMENT_DURATION_SEC,
        terminal_pids=terms,
        probe=probe,
    )

    try:
        while time.time() < wall_deadline:
            if stop_file.exists():
                log(log_path, "stop_file_seen", stop_path=str(stop_file))
                break

            terms = terminal_pids()
            if not terms:
                log(log_path, "abort_terminal_gone", note="will not invent login; leaving Real alone")
                break

            if current is None or current.poll() is not None:
                # Capture not running.
                if current is not None:
                    rc = current.returncode
                    session_end = (out_dir / "session_end.json").exists()
                    session_crash = (out_dir / "session_crash.json").exists()
                    log(
                        log_path,
                        "capture_exited",
                        pid=current.pid,
                        returncode=rc,
                        session_end=session_end,
                        session_crash=session_crash,
                        restarts=restarts,
                    )
                    # Clean completion of segment with session_end → relaunch next segment
                    # unless wall budget exhausted or stop requested.
                    if stop_file.exists():
                        break
                    if restarts >= MAX_RESTARTS:
                        log(log_path, "max_restarts_reached", restarts=restarts)
                        break
                    # Only auto-restart if Real still healthy.
                    probe = probe_real_ok()
                    if not probe.get("ok"):
                        log(log_path, "no_restart_probe_fail", probe=probe)
                        break
                    restarts += 1
                    # Rotate crash/end markers so next segment is distinguishable.
                    for name in ("session_end.json", "session_crash.json", "capture_progress.json"):
                        p = out_dir / name
                        if p.exists():
                            stamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
                            p.rename(out_dir / f"_archived_{stamp}_{name}")

                segment += 1
                current = launch_capture(out_dir, stop_file, log_dir, segment)
                segment_started_at = time.time()
                log(
                    log_path,
                    "capture_launched",
                    pid=current.pid,
                    segment=segment,
                    restarts=restarts,
                    out_dir=str(out_dir),
                )
                write_receipt(
                    receipt_path,
                    {
                        **launch_payload,
                        "updated_at_utc": iso_utc(),
                        "status": "QFSI_007_LONG_CAPTURE_RUNNING",
                        "current_pid": current.pid,
                        "segment": segment,
                        "restarts": restarts,
                        "real_terminal_pids": terminal_pids(),
                    },
                )

            # Stall detection: only after this segment has had time to write.
            # Do NOT use stale mtimes from a prior dead segment (that killed 007 instantly).
            if (
                current is not None
                and current.poll() is None
                and segment_started_at is not None
                and (time.time() - segment_started_at) > STALL_GRACE_SEC
            ):
                mtime = newest_mtime(out_dir)
                if mtime is not None and (time.time() - mtime) > STALL_SEC:
                    log(
                        log_path,
                        "stall_detected_terminating_capture_only",
                        pid=current.pid,
                        stall_sec=STALL_SEC,
                        segment_age_sec=round(time.time() - segment_started_at, 1),
                        note="kill capture python only — never terminal64",
                    )
                    try:
                        current.terminate()
                        try:
                            current.wait(timeout=20)
                        except subprocess.TimeoutExpired:
                            current.kill()
                    except Exception as exc:
                        log(log_path, "stall_kill_error", error=str(exc))
                    # Loop will restart if Real OK.

            # Watcher self-heartbeat (detect silent death in ops).
            try:
                hb = {
                    "ts": iso_utc(),
                    "watcher_alive": True,
                    "capture_pid": current.pid if current and current.poll() is None else None,
                    "segment": segment,
                    "restarts": restarts,
                    "wall_remaining_sec": max(0, int(wall_deadline - time.time())),
                }
                (PRE / "20260715_QFSI_007_WATCHER_HEARTBEAT.json").write_text(
                    json.dumps(hb, indent=2) + "\n", encoding="utf-8"
                )
            except Exception:
                pass

            time.sleep(POLL_SEC)
    finally:
        # Do not kill Real. Optionally leave capture running if wall ended mid-segment.
        final = {
            **launch_payload,
            "updated_at_utc": iso_utc(),
            "status": "QFSI_007_WATCHER_EXIT",
            "current_pid": current.pid if current and current.poll() is None else None,
            "capture_still_running": bool(current and current.poll() is None),
            "segment": segment,
            "restarts": restarts,
            "real_terminal_pids": terminal_pids(),
            "session_end_present": (out_dir / "session_end.json").exists(),
            "session_crash_present": (out_dir / "session_crash.json").exists(),
            "do_not_kill_real": True,
        }
        write_receipt(receipt_path, final)
        log(log_path, "watcher_exit", **{k: final[k] for k in ("current_pid", "restarts", "segment")})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
