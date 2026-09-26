"""pa_slots — CPU slot governor for PA-PRO heavy python processes.

Rule (charter section 9): at most 4 of OUR heavy python processes at a time
(raised from 2 on 2026-09-21, Owner-approved).
Processes owned by other agents (Dukascopy downloads, ``lines1_run.py``,
``ops.live.run_paper``, ...) are NOT ours: this module never inspects, counts
or touches them.

Design
------
- Slot files ``PA_Pro/locks/pa_slot_<i>.lock`` (i = 1.._N_SLOTS) hold JSON
  ``{"pid": int, "started_utc": iso, "note": str}``.
- ``acquire`` creates a slot file atomically (``O_CREAT | O_EXCL``) inside a
  critical section guarded by an OS file lock on ``locks/.pa_slots_guard`` so
  two processes cannot both reclaim the same stale slot.
- Stale = PID not alive, or ``started_utc`` older than 6 hours, or the JSON is
  unreadable.  A stale slot is reclaimed (unlinked) and re-created.
- Import side effects (before numpy where possible): ``OMP_NUM_THREADS``,
  ``MKL_NUM_THREADS``, ``OPENBLAS_NUM_THREADS`` = 4, and the current process
  priority set to BelowNormal on Windows (no-op elsewhere).
"""

import json
import os
import time
from datetime import datetime, timezone

__all__ = ["SlotsBusy", "acquire", "release", "slot", "set_lock_dir", "lock_dir"]

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                      # 03. EA Developer/PA_Pro
_LOCK_DIR = os.path.join(_ROOT, "locks")
_N_SLOTS = 4
_STALE_SECONDS = 6 * 3600
_GUARD_NAME = ".pa_slots_guard"
_HELD = {}                                          # slot_id -> path (this proc)

# ---- thread caps + priority: do this at import, before numpy loads ----------
for _k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_k] = "4"


def _set_below_normal():
    if os.name != "nt":
        return False
    try:
        import ctypes

        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        k32 = ctypes.windll.kernel32
        # explicit prototypes: without them the 64-bit pseudo-handle is
        # truncated and the call fails silently on 64-bit Python
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k32.SetPriorityClass.restype = ctypes.c_int
        return bool(k32.SetPriorityClass(k32.GetCurrentProcess(),
                                         BELOW_NORMAL_PRIORITY_CLASS))
    except Exception:
        return False


_set_below_normal()


class SlotsBusy(RuntimeError):
    """All PA-PRO heavy slots are taken."""


def lock_dir():
    return _LOCK_DIR


def set_lock_dir(path):
    """Redirect the lock directory (tests).  Returns the previous path."""
    global _LOCK_DIR
    old = _LOCK_DIR
    _LOCK_DIR = os.path.abspath(path)
    os.makedirs(_LOCK_DIR, exist_ok=True)
    return old


def _slot_path(i):
    return os.path.join(_LOCK_DIR, f"pa_slot_{i}.lock")


def _guard():
    """Cross-process critical section for slot creation/reclaim."""
    os.makedirs(_LOCK_DIR, exist_ok=True)
    path = os.path.join(_LOCK_DIR, _GUARD_NAME)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    if os.name == "nt":
        import msvcrt

        deadline = time.time() + 30.0
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.time() > deadline:
                    os.close(fd)
                    raise SlotsBusy("pa_slots guard lock timeout")
                time.sleep(0.05)
    else:
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _unguard(fd):
    try:
        if os.name == "nt":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                return False
            code = ctypes.c_ulong(0)
            ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
            k32.CloseHandle(h)
            STILL_ACTIVE = 259
            return bool(ok) and code.value == STILL_ACTIVE
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_slot(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _is_stale(info):
    if not isinstance(info, dict):
        return True
    if not _pid_alive(info.get("pid")):
        return True
    try:
        started = datetime.fromisoformat(str(info.get("started_utc")))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - started).total_seconds()
        if age > _STALE_SECONDS:
            return True
    except Exception:
        return True
    return False


def _iso_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def acquire(note="", timeout=0.0):
    """Take one slot.  Returns the slot id (1.._N_SLOTS).  Raises :class:`SlotsBusy`
    when all slots are held by live processes and ``timeout`` seconds pass.
    ``timeout <= 0`` means a single non-blocking attempt."""
    os.makedirs(_LOCK_DIR, exist_ok=True)
    deadline = time.time() + max(0.0, float(timeout))
    while True:
        guard_fd = _guard()
        try:
            for i in range(1, _N_SLOTS + 1):
                path = _slot_path(i)
                if os.path.exists(path):
                    info = _read_slot(path)
                    if not _is_stale(info):
                        continue
                    try:
                        os.unlink(path)
                    except OSError:
                        continue
                try:
                    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                except FileExistsError:
                    continue
                payload = {"pid": os.getpid(), "started_utc": _iso_now(), "note": str(note)}
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f, sort_keys=True)
                _HELD[i] = path
                return i
        finally:
            _unguard(guard_fd)
        if time.time() >= deadline:
            raise SlotsBusy(
                f"all {_N_SLOTS} PA-PRO slots busy (note={note!r}); "
                f"holders: {[_read_slot(_slot_path(i)) for i in range(1, _N_SLOTS + 1)]}"
            )
        time.sleep(0.1)


def release(slot_id):
    """Release a slot we hold.  Deleting someone else's slot is a no-op unless
    the slot is stale (defensive: never delete a live foreign process)."""
    path = _slot_path(int(slot_id))
    guard_fd = _guard()
    try:
        info = _read_slot(path)
        owner = info.get("pid") if isinstance(info, dict) else None
        if owner == os.getpid() or _is_stale(info):
            try:
                os.unlink(path)
            except OSError:
                pass
        _HELD.pop(int(slot_id), None)
    finally:
        _unguard(guard_fd)


class slot:
    """Context manager: ``with pa_slots.slot("note"): ...``."""

    def __init__(self, note="", timeout=0.0):
        self.note = note
        self.timeout = timeout
        self.id = None

    def __enter__(self):
        self.id = acquire(self.note, timeout=self.timeout)
        return self.id

    def __exit__(self, exc_type, exc, tb):
        if self.id is not None:
            release(self.id)
        return False
