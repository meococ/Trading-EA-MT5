"""CPU slots: exactly _N_SLOTS acquisitions succeed, one more is refused,
stale locks are reclaimed, and the process environment is capped."""

import json
import os

import pytest

import pa_slots

# Owner-approved cap (2026-09-21, raised from 2).  Changing it needs the
# Owner's sign-off and a matching edit to charter section 9.
APPROVED_SLOTS = 4


def test_slot_count_is_the_owner_approved_cap():
    assert pa_slots._N_SLOTS == APPROVED_SLOTS


def test_thread_env_caps_set_at_import():
    assert os.environ["OMP_NUM_THREADS"] == "4"
    assert os.environ["MKL_NUM_THREADS"] == "4"
    assert os.environ["OPENBLAS_NUM_THREADS"] == "4"


@pytest.mark.skipif(os.name != "nt", reason="win32 priority class only")
def test_below_normal_priority_actually_set():
    import ctypes

    k32 = ctypes.windll.kernel32
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.GetPriorityClass.argtypes = [ctypes.c_void_p]
    k32.GetPriorityClass.restype = ctypes.c_uint32
    k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k32.SetPriorityClass.restype = ctypes.c_int
    NORMAL, BELOW = 0x20, 0x4000
    k32.SetPriorityClass(k32.GetCurrentProcess(), NORMAL)
    assert pa_slots._set_below_normal() is True
    assert k32.GetPriorityClass(k32.GetCurrentProcess()) == BELOW


def test_all_slots_then_busy_then_dead_pid_reclaimed():
    n = pa_slots._N_SLOTS
    ids = [pa_slots.acquire(f"job{i}") for i in range(n)]
    assert sorted(ids) == list(range(1, n + 1))
    a = ids[0]
    p_a = os.path.join(pa_slots.lock_dir(), f"pa_slot_{a}.lock")
    info = json.loads(open(p_a, encoding="utf-8").read())
    assert info["pid"] == os.getpid() and info["note"] == "job0"

    with pytest.raises(pa_slots.SlotsBusy):
        pa_slots.acquire("one-too-many", timeout=0)
    with pytest.raises(pa_slots.SlotsBusy):
        pa_slots.acquire("one-too-many", timeout=0.3)

    pa_slots.release(a)
    c = pa_slots.acquire("after-release")
    assert c == a
    for sid in ids[1:]:
        pa_slots.release(sid)
    pa_slots.release(c)
    for i in range(1, n + 1):
        assert not os.path.exists(
            os.path.join(pa_slots.lock_dir(), f"pa_slot_{i}.lock"))

    # a lock whose PID is dead must be reclaimed, not honoured
    ghost = os.path.join(pa_slots.lock_dir(), "pa_slot_1.lock")
    with open(ghost, "w", encoding="utf-8") as f:
        json.dump({"pid": 99999999, "started_utc": "2026-09-20T00:00:00Z",
                   "note": "ghost"}, f)
    d = pa_slots.acquire("reclaim")
    assert d == 1
    info = json.loads(open(ghost, encoding="utf-8").read())
    assert info["pid"] == os.getpid() and info["note"] == "reclaim"
    pa_slots.release(d)


def test_context_manager():
    with pa_slots.slot("ctx") as sid:
        assert 1 <= sid <= pa_slots._N_SLOTS
        assert os.path.exists(os.path.join(pa_slots.lock_dir(), f"pa_slot_{sid}.lock"))
    assert not os.path.exists(os.path.join(pa_slots.lock_dir(), f"pa_slot_{sid}.lock"))
