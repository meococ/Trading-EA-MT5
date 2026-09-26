"""CPU slots: two acquisitions succeed, the third is refused, stale locks are
reclaimed, and the process environment is capped."""

import json
import os

import pytest

import pa_slots


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


def test_two_slots_then_busy_then_dead_pid_reclaimed():
    a = pa_slots.acquire("first")
    b = pa_slots.acquire("second")
    assert a in (1, 2) and b in (1, 2) and a != b
    p_a = os.path.join(pa_slots.lock_dir(), f"pa_slot_{a}.lock")
    info = json.loads(open(p_a, encoding="utf-8").read())
    assert info["pid"] == os.getpid() and info["note"] == "first"

    with pytest.raises(pa_slots.SlotsBusy):
        pa_slots.acquire("third", timeout=0)
    with pytest.raises(pa_slots.SlotsBusy):
        pa_slots.acquire("third", timeout=0.3)

    pa_slots.release(a)
    c = pa_slots.acquire("third-after-release")
    assert c == a
    pa_slots.release(b)
    pa_slots.release(c)
    assert not os.path.exists(p_a)

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
        assert sid in (1, 2)
        assert os.path.exists(os.path.join(pa_slots.lock_dir(), f"pa_slot_{sid}.lock"))
    assert not os.path.exists(os.path.join(pa_slots.lock_dir(), f"pa_slot_{sid}.lock"))
