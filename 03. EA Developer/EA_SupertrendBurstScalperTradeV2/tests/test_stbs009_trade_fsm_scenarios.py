from __future__ import annotations

from dataclasses import dataclass, field


DESIGN_START = 1514764800
DESIGN_END = 1672531200
VISIBILITY_TIMEOUT = 60


@dataclass
class LifecycleModel:
    state: str = "FLAT"
    exit_intent: str = "NONE"
    positions: int = 0
    orders: int = 0
    expected: bool = False
    pending_request: bool = False
    request_age: int = 0
    runtime_failed: bool = False
    entry_clock_known: bool = True
    counted_identifiers: set[int] = field(default_factory=set)
    entry_count: int = 0
    entry_block_until: int = 0
    actions: list[str] = field(default_factory=list)

    def accepted_entry(self, retcode: str, persist_before: bool = True, persist_after: bool = True) -> None:
        assert retcode in {"DONE", "DONE_PARTIAL", "PLACED"}
        if not persist_before:
            self.runtime_failed = True
            self.state = "MANAGE_ONLY"
            self.actions.append("NO_SEND_PERSIST_FAIL")
            return
        self.expected = True
        self.pending_request = True
        self.state = "ENTRY_PENDING"
        self.actions.append(f"SEND_{retcode}")
        if not persist_after:
            self.runtime_failed = True
            self.exit_intent = "RUNTIME_FAULT"
            self.state = "MANAGE_ONLY"

    def reconcile(self, *, read_ok: bool = True, position_identifier: int = 0) -> None:
        if not read_ok:
            self.runtime_failed = True
            self.exit_intent = "RUNTIME_FAULT"
            self.state = "MANAGE_ONLY"
            return
        if self.positions > 1 or self.orders > 1:
            self.runtime_failed = True
            self.exit_intent = "RUNTIME_FAULT"
            self.state = "MANAGE_ONLY"
            return
        if self.positions == 0 and self.orders == 0 and self.pending_request:
            if self.request_age <= VISIBILITY_TIMEOUT:
                self.state = "ENTRY_PENDING"
                return
            self.runtime_failed = True
            self.exit_intent = "RUNTIME_FAULT"
            self.state = "MANAGE_ONLY"
            return
        if self.positions == 1 and self.orders == 1:
            self.exit_intent = "PROTECTION_INVALID"
            self.state = "EXIT_PENDING"
            return
        if self.positions == 1:
            if not self.expected:
                self.exit_intent = "PROTECTION_INVALID"
                self.state = "MANAGE_ONLY"
                return
            if not self.entry_clock_known:
                self.exit_intent = "ENTRY_CLOCK_UNKNOWN"
                self.state = "MANAGE_ONLY"
                return
            self.pending_request = False
            self.state = "OPEN"
            if position_identifier and position_identifier not in self.counted_identifiers:
                self.counted_identifiers.add(position_identifier)
                self.entry_count += 1
            return
        if self.orders == 1:
            self.state = "EXIT_PENDING" if self.exit_intent != "NONE" else "ENTRY_PENDING"
            return
        if self.runtime_failed:
            self.state = "MANAGE_ONLY"
        else:
            self.expected = False
            self.state = "FLAT"

    def manage(self, *, flatten: bool = False, max_hold: bool = False, current_open: int = 0) -> None:
        self.reconcile()
        if flatten and (self.positions or self.orders):
            self.exit_intent = "FRIDAY_DESIGN"
            self.entry_block_until = max(self.entry_block_until, current_open + 900)
        elif self.runtime_failed and (self.positions or self.orders):
            self.exit_intent = "RUNTIME_FAULT"
            self.entry_block_until = max(self.entry_block_until, current_open + 900)
        elif max_hold and self.positions:
            self.exit_intent = "TIME"
            self.entry_block_until = max(self.entry_block_until, current_open + 900)
        if self.exit_intent != "NONE" and self.orders:
            self.orders -= 1
            self.actions.append("CANCEL")
            return
        if self.exit_intent != "NONE" and self.positions:
            self.positions -= 1
            self.actions.append("CLOSE")

    def can_enter(self, decision_time: int) -> bool:
        return not self.runtime_failed and decision_time >= self.entry_block_until


def committed_snapshot_loads(committed: int, slot_generations: tuple[int | None, int | None]) -> bool:
    current_slot = committed % 2
    other_slot = 1 - current_slot
    if slot_generations[current_slot] != committed:
        return False
    other = slot_generations[other_slot]
    return other is None or other <= committed


def lifecycle_requires_tick(
    *,
    new_m15_bar: bool = False,
    state: str = "FLAT",
    exit_intent: str = "NONE",
    expected_direction: int = 0,
    reverse_direction: int = 0,
    pending_request: int = 0,
    pending_order: int = 0,
    pending_deal: int = 0,
    request_started: int = 0,
    runtime_failed: bool = False,
) -> bool:
    return any(
        (
            new_m15_bar,
            state != "FLAT",
            exit_intent != "NONE",
            expected_direction != 0,
            reverse_direction != 0,
            pending_request != 0,
            pending_order != 0,
            pending_deal != 0,
            request_started != 0,
            runtime_failed,
        )
    )


@dataclass
class IdempotentSnapshotModel:
    generation: int = 0
    committed_payload: tuple[object, ...] | None = None
    writes: int = 0

    def persist(self, payload: tuple[object, ...], *, write_ok: bool = True) -> bool:
        if self.committed_payload == payload:
            return True
        if not write_ok:
            return False
        self.generation += 1
        self.committed_payload = payload
        self.writes += 1
        return True


def test_done_partial_and_placed_are_tracking_not_fill() -> None:
    for retcode in ("DONE", "DONE_PARTIAL", "PLACED"):
        model = LifecycleModel()
        model.accepted_entry(retcode)
        assert model.state == "ENTRY_PENDING"
        assert model.entry_count == 0
        model.positions = 1
        model.reconcile(position_identifier=11)
        assert model.state == "OPEN" and model.entry_count == 1


def test_flat_fast_path_skips_only_stateless_same_bar_ticks() -> None:
    assert not lifecycle_requires_tick()
    assert lifecycle_requires_tick(new_m15_bar=True)
    assert lifecycle_requires_tick(state="OPEN")
    assert lifecycle_requires_tick(state="ENTRY_PENDING")
    assert lifecycle_requires_tick(exit_intent="TIME")
    assert lifecycle_requires_tick(expected_direction=1)
    assert lifecycle_requires_tick(reverse_direction=-1)
    assert lifecycle_requires_tick(pending_request=7)
    assert lifecycle_requires_tick(pending_order=8)
    assert lifecycle_requires_tick(pending_deal=9)
    assert lifecycle_requires_tick(request_started=10)
    assert lifecycle_requires_tick(runtime_failed=True)


def test_idempotent_snapshot_commits_only_state_changes() -> None:
    model = IdempotentSnapshotModel()
    flat = ("FLAT", "NONE", 0, 0.0, 0.0, 0.0)
    pending = ("ENTRY_PENDING", "NONE", 1, 0.1, 1900.0, 1910.0)
    assert model.persist(flat)
    assert model.persist(flat)
    assert (model.generation, model.writes) == (1, 1)
    assert model.persist(pending)
    assert (model.generation, model.writes) == (2, 2)
    assert not model.persist(("OPEN",), write_ok=False)
    assert model.committed_payload == pending
    assert (model.generation, model.writes) == (2, 2)


def test_partial_position_plus_order_drains_cancel_then_close() -> None:
    model = LifecycleModel(positions=1, orders=1, expected=True, pending_request=True)
    model.reconcile()
    assert model.exit_intent == "PROTECTION_INVALID"
    model.manage()
    model.manage()
    assert model.actions == ["CANCEL", "CLOSE"]
    assert (model.orders, model.positions) == (0, 0)


def test_multiple_exposure_enters_runtime_drain() -> None:
    model = LifecycleModel(positions=2, orders=2)
    model.manage()
    assert model.runtime_failed and model.actions == ["CANCEL"]
    model.manage()
    model.manage()
    model.manage()
    assert model.orders == 0 and model.positions == 0


def test_transient_zero_visibility_never_becomes_flat_or_reenterable() -> None:
    model = LifecycleModel(state="ENTRY_PENDING", expected=True, pending_request=True, request_age=30)
    model.reconcile()
    assert model.state == "ENTRY_PENDING"
    model.request_age = 61
    model.reconcile()
    assert model.state == "MANAGE_ONLY" and model.runtime_failed


def test_persistence_failure_before_and_after_send_fail_closed() -> None:
    before = LifecycleModel()
    before.accepted_entry("DONE", persist_before=False)
    assert before.actions == ["NO_SEND_PERSIST_FAIL"] and before.state == "MANAGE_ONLY"
    after = LifecycleModel()
    after.accepted_entry("PLACED", persist_after=False)
    assert after.pending_request and after.runtime_failed and after.exit_intent == "RUNTIME_FAULT"


def test_corrupt_restart_with_exposure_is_manage_only_and_drained() -> None:
    model = LifecycleModel(positions=1, runtime_failed=True, state="MANAGE_ONLY")
    model.manage()
    assert model.actions == ["CLOSE"] and model.positions == 0


def test_selection_api_failure_is_not_flat() -> None:
    model = LifecycleModel(state="ENTRY_PENDING", expected=True, pending_request=True)
    model.reconcile(read_ok=False)
    assert model.state == "MANAGE_ONLY" and model.runtime_failed


def test_friday_or_design_end_cancels_pending_entry() -> None:
    for decision_time in (DESIGN_END, DESIGN_END + 900):
        model = LifecycleModel(state="ENTRY_PENDING", orders=1, expected=True, pending_request=True)
        model.manage(flatten=decision_time >= DESIGN_END)
        assert model.actions == ["CANCEL"] and model.orders == 0


def test_open_exposure_is_flattened_at_design_end() -> None:
    model = LifecycleModel(state="OPEN", positions=1, expected=True)
    model.manage(flatten=True)
    assert model.actions == ["CLOSE"] and model.exit_intent == "FRIDAY_DESIGN"


def test_missing_entry_clock_forces_exit() -> None:
    model = LifecycleModel(positions=1, expected=True, entry_clock_known=False)
    model.manage()
    assert model.exit_intent == "ENTRY_CLOCK_UNKNOWN"
    model.manage()
    assert model.actions == ["CLOSE"]


def test_restart_counter_is_identifier_idempotent() -> None:
    model = LifecycleModel(positions=1, expected=True)
    model.reconcile(position_identifier=99)
    model.reconcile(position_identifier=99)
    assert model.entry_count == 1


def test_max_hold_has_priority_over_same_tick_opposite_flip() -> None:
    model = LifecycleModel(state="OPEN", positions=1, expected=True)
    model.manage(max_hold=True, current_open=10_000)
    assert model.exit_intent == "TIME" and model.actions == ["CLOSE"]
    assert not model.can_enter(10_000)
    assert model.can_enter(10_900)


def test_newer_uncommitted_snapshot_is_rejected_not_rolled_back() -> None:
    assert committed_snapshot_loads(4, (4, 3))
    assert not committed_snapshot_loads(4, (4, 5))
    assert not committed_snapshot_loads(4, (2, 3))
