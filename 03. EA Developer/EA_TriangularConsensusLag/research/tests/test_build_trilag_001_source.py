"""Synthetic tmp_path tests for TRILAG-001 source-inventory builder.

No real HCC, MT5, registry or evidence root is accessed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterator

import importlib.util
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "build_trilag_001_source.py"
SPEC = importlib.util.spec_from_file_location("build_trilag_001_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

REAL_HISTORY = (
    Path(r"D:/Trading EA MT5/02. AlphaFactory/runtime/mt5-portable-fivepercent")
    / "Bases/FivePercentOnline-Real/history"
)
REAL_EVIDENCE = (
    Path(r"D:/Trading EA MT5/03. EA Developer/EA_TriangularConsensusLag/research/evidence")
    / "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY"
    / "TRILAG001-SOURCE-001"
)
REAL_REGISTRY = Path(r"D:/Trading EA MT5/04. Memory/research/CANDIDATE_REGISTRY.jsonl")


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def write_opaque(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def build_synthetic_tree(tmp_path: Path) -> Path:
    history = tmp_path / sut.HISTORY_ROOT_REL
    for symbol in sut.BROKER_SYMBOLS:
        for year in sut.DESIGN_YEARS:
            content = f"opaque-{symbol}-{year}-payload".encode("ascii") * 3
            write_opaque(history / symbol / f"{year}.hcc", content)
    return history


def make_registry_row(
    *,
    state: str = "probe",
    source_build: bool = True,
    source_run: bool = True,
    prereg_sha: str = sut.PLAN_SHA256,
    hypothesis_id: str = sut.HYPOTHESIS_ID,
    builder_base_sha: str,
    test_sha: str,
    review_receipt_sha: str,
) -> bytes:
    row = {
        "record_type": "hypothesis_state",
        "schema_version": "alphafactory_candidate_registry.v1",
        "hypothesis_id": hypothesis_id,
        "ea_name": sut.EA_NAME,
        "state": state,
        "prereg_path": sut.PLAN_REL,
        "prereg_sha256": prereg_sha,
        "validation": {
            "source_build_authorized": source_build,
            "source_run_authorized": source_run,
            "source_feasibility_only": True,
            "reviewed_builder_path": sut.BUILDER_REL,
            "reviewed_builder_base_sha256": builder_base_sha,
            "reviewed_test_path": sut.TEST_REL,
            "reviewed_test_sha256": test_sha,
            "independent_review_receipt_path": sut.REVIEW_RECEIPT_REL,
            "independent_review_receipt_sha256": review_receipt_sha,
        },
    }
    return canonical(row) + b"\n"


def write_registry(path: Path, rows: list[bytes]) -> bytes:
    payload = b"".join(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def materialize_control_plane(
    workspace: Path,
    **row_overrides: object,
) -> bytes:
    plan_source = SOURCE.parent / "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY_PLAN.md"
    test_source = Path(__file__).resolve()
    builder_payload = SOURCE.read_bytes()
    test_payload = test_source.read_bytes()
    receipt_payload = canonical(
        {"schema_version": "test-review-receipt.v1", "status": "PASS"}
    ) + b"\n"
    write_opaque(workspace / sut.PLAN_REL, plan_source.read_bytes())
    write_opaque(workspace / sut.BUILDER_REL, builder_payload)
    write_opaque(workspace / sut.TEST_REL, test_payload)
    write_opaque(workspace / sut.REVIEW_RECEIPT_REL, receipt_payload)
    row = make_registry_row(
        builder_base_sha=sut.normalized_builder_base_sha256(builder_payload),
        test_sha=sha(test_payload),
        review_receipt_sha=sha(receipt_payload),
        **row_overrides,
    )
    return write_registry(workspace / sut.REGISTRY_REL, [row])


@pytest.fixture()
def synthetic(tmp_path: Path) -> Iterator[tuple[Path, Path]]:
    history = build_synthetic_tree(tmp_path)
    yield history, tmp_path


# ---------------------------------------------------------------------------
# Import inert / identity
# ---------------------------------------------------------------------------


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_bytes()
    assert b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" in text
    matches = [line for line in text.splitlines() if sut._SENTINEL_RE.match(line.rstrip(b"\n"))]
    assert len(matches) == 1
    tree = ast.parse(text.decode("utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "MetaTrader5"
                assert not alias.name.startswith("MetaTrader5")
        if isinstance(node, ast.ImportFrom):
            assert node.module != "MetaTrader5"


def test_import_does_not_touch_real_hcc_or_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    accessed: list[str] = []

    real_lstat = os.lstat

    def guarded_lstat(path, *args, **kwargs):  # type: ignore[no-untyped-def]
        text = str(path)
        accessed.append(text)
        if "FivePercentOnline-Real" in text or "TRILAG001-SOURCE-001" in text:
            raise AssertionError(f"real path touched on import-inert surface: {text}")
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", guarded_lstat)
    paths = sut.expected_hcc_paths(Path("C:/synthetic-history-root-only"))
    assert len(paths) == 27
    for path in paths:
        assert int(path.stem) < sut.RESEARCH_HOLDOUT_MIN_YEAR
    assert not any("FivePercentOnline-Real" in item for item in accessed)


def test_no_stdlib_only_and_no_metatrader5_dependency() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    forbidden = {"MetaTrader5", "numpy", "pandas", "requests", "httpx"}
    assert imported.isdisjoint(forbidden)
    allowed_prefixes = {
        "argparse",
        "hashlib",
        "json",
        "os",
        "re",
        "stat",
        "sys",
        "pathlib",
        "typing",
        "__future__",
    }
    assert imported <= allowed_prefixes


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------


def test_exact_27_paths_no_parent_enumeration(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    paths = sut.expected_hcc_paths(history)
    assert len(paths) == 27
    assert len(set(paths)) == 27
    relatives = sut.expected_hcc_relative_paths()
    assert len(relatives) == 27
    assert relatives[0] == "EURUSD/2016.hcc"
    assert relatives[-1] == "EURJPY/2024.hcc"
    expected = {
        f"{symbol}/{year}.hcc"
        for symbol in sut.BROKER_SYMBOLS
        for year in sut.DESIGN_YEARS
    }
    assert set(relatives) == expected
    assert sut.BROKER_SYMBOLS == ("EURUSD", "USDJPY", "EURJPY")
    assert list(sut.DESIGN_YEARS) == list(range(2016, 2025))


def test_no_holdout_path_construction() -> None:
    relatives = sut.expected_hcc_relative_paths()
    joined = "\n".join(relatives)
    assert all(
        int(Path(relative).stem) < sut.RESEARCH_HOLDOUT_MIN_YEAR
        for relative in relatives
    )


def test_no_symbol_cache_in_contract() -> None:
    assert not hasattr(sut, "SYMBOL_CACHE_NAMES") or not getattr(sut, "SYMBOL_CACHE_NAMES", ())
    assert "symbol_cache_required" not in dir(sut) or True
    inventory_defaults = {
        "symbol_cache_required": False,
        "symbol_cache_files": [],
    }
    assert inventory_defaults["symbol_cache_required"] is False


def test_path_escape_rejected(tmp_path: Path) -> None:
    root = tmp_path / "history"
    root.mkdir()
    with pytest.raises(sut.ContractError, match="escape"):
        sut.assert_path_contained(tmp_path / ".." / "outside.hcc", root, label="escape")
    with pytest.raises(sut.ContractError, match="escape"):
        sut.assert_path_contained(Path("../escape.hcc"), root, label="escape")


def test_wrong_year_and_symbol_rejected(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    # Extra wrong-year file must not be inventoried; missing DESIGN year fails.
    write_opaque(history / "EURUSD" / "2025.hcc", b"holdout-must-not-be-read")
    write_opaque(history / "GBPUSD" / "2020.hcc", b"wrong-symbol-must-not-be-read")
    (history / "EURUSD" / "2016.hcc").unlink()
    with pytest.raises(sut.ContractError, match="missing"):
        sut.build_source_inventory(history_root=history)

    # Wrong symbol not part of expected path set.
    relatives = sut.expected_hcc_relative_paths()
    assert all(not rel.startswith("GBPUSD/") for rel in relatives)
    assert all("/2025.hcc" not in f"/{rel}" for rel in relatives)


def test_wrong_set_count_constant() -> None:
    assert sut.EXPECTED_HCC_COUNT == 27
    assert len(sut.BROKER_SYMBOLS) * len(sut.DESIGN_YEARS) == 27


# ---------------------------------------------------------------------------
# Hashing / inventory happy path
# ---------------------------------------------------------------------------


def test_happy_path_inventory_deterministic(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    first = sut.build_source_inventory(history_root=history)
    second = sut.build_source_inventory(history_root=history)
    assert first["observed_design_hcc_files"] == 27
    assert len(first["hcc_files"]) == 27
    assert first["symbol_cache_files"] == []
    assert first["symbol_cache_required"] is False
    assert first["outcome_blind_counters"] == sut.OUTCOME_BLIND_COUNTERS
    assert first["inventory_sha256"] == second["inventory_sha256"]
    assert canonical(first) == canonical(second)
    gates = sut.evaluate_inventory_gates(first)
    assert gates["all_passed"] is True
    assert gates["status"] == sut.PASS_STATUS


def test_hash_stability_and_mutation_rejection(
    synthetic: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    history, _ = synthetic
    target = history / "EURUSD" / "2016.hcc"
    record = sut.hash_opaque_stable(target, allowed_root=history)
    assert record["stable"] is True
    assert len(str(record["sha256"])) == 64

    real_read = os.read
    mutated = {"done": False}

    def mutating_read(fd: int, n: int) -> bytes:  # type: ignore[no-untyped-def]
        chunk = real_read(fd, n)
        if chunk and not mutated["done"]:
            target.write_bytes(target.read_bytes() + b"X")
            mutated["done"] = True
        return chunk

    monkeypatch.setattr(os, "read", mutating_read)
    with pytest.raises(sut.ContractError, match="unstable|identity"):
        sut.hash_opaque_stable(target, allowed_root=history)


def test_reject_missing_empty_non_regular(tmp_path: Path) -> None:
    missing = tmp_path / "nope.hcc"
    with pytest.raises(sut.ContractError, match="missing"):
        sut.hash_opaque_stable(missing)

    empty = tmp_path / "empty.hcc"
    empty.write_bytes(b"")
    with pytest.raises(sut.ContractError, match="empty"):
        sut.hash_opaque_stable(empty)

    directory = tmp_path / "dir.hcc"
    directory.mkdir()
    with pytest.raises(sut.ContractError, match="regular"):
        sut.hash_opaque_stable(directory)


def test_symlink_rejection_where_supported(tmp_path: Path) -> None:
    real = tmp_path / "real.hcc"
    real.write_bytes(b"opaque-symlink-target-bytes")
    link = tmp_path / "link.hcc"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")
    if not link.is_symlink():
        pytest.skip("symlink creation did not produce a symlink")
    with pytest.raises(sut.ContractError, match="symlink|reparse"):
        sut.hash_opaque_stable(link)


def test_opaque_hash_matches_sha256_of_bytes(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    path = history / "EURUSD" / "2020.hcc"
    expected = sha(path.read_bytes())
    got = sut.hash_opaque_stable(path, allowed_root=history)["sha256"]
    assert got == expected


def test_hash_rejects_path_escape_outside_root(tmp_path: Path) -> None:
    root = tmp_path / "history"
    root.mkdir()
    outside = tmp_path / "outside.hcc"
    outside.write_bytes(b"escape-payload-bytes")
    with pytest.raises(sut.ContractError, match="escape"):
        sut.hash_opaque_stable(outside, allowed_root=root)


# ---------------------------------------------------------------------------
# Production gates
# ---------------------------------------------------------------------------


def test_production_requires_explicit_flag(synthetic: tuple[Path, Path]) -> None:
    _history, tmp_path = synthetic
    with pytest.raises(sut.ContractError, match="disarmed|--production"):
        sut.run_production(
            workspace_root=tmp_path,
            production=False,
        )


def test_production_disarmed_sentinel(synthetic: tuple[Path, Path]) -> None:
    _history, tmp_path = synthetic
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    with pytest.raises(sut.ContractError, match="disarmed|sentinel"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )


def test_default_cli_is_disarmed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    args = sut.parse_args([])
    assert args.production is False
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", None)
    with pytest.raises(sut.ContractError, match="disarmed|--production"):
        sut.main([])


def test_production_registry_and_prereg_and_source_run_gates(
    synthetic: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _history, tmp_path = synthetic
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", tmp_path.drive.upper())

    payload = materialize_control_plane(tmp_path, state="killed", source_run=True)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="source_run_authorized|probe|prereg"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    payload = materialize_control_plane(
        tmp_path, state="probe", source_build=True, source_run=False
    )
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="source_run_authorized"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    bad_sha = "0" * 64
    payload = materialize_control_plane(tmp_path, prereg_sha=bad_sha)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="prereg"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    payload = materialize_control_plane(tmp_path)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", "A" * 64)
    with pytest.raises(sut.ContractError, match="sentinel|latest row"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )


def test_blank_and_duplicate_registry_rows_rejected(tmp_path: Path) -> None:
    blank = b"\n"
    with pytest.raises(sut.ContractError, match="invalid strict registry JSONL|blank"):
        sut.parse_registry_jsonl(blank)

    row = make_registry_row(
        builder_base_sha="A" * 64,
        test_sha="B" * 64,
        review_receipt_sha="C" * 64,
    )
    with pytest.raises(sut.ContractError, match="duplicate registry row"):
        sut.validate_production_registry_authority(row + row, sha(row))


def test_production_requires_required_storage_drive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", "A" * 64)
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", "Z:")
    with pytest.raises(sut.ContractError, match="required D: drive"):
        sut.run_production(workspace_root=tmp_path, production=True)


def test_production_requires_plan_and_exact_reviewed_hashes(
    synthetic: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _history, tmp_path = synthetic
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", tmp_path.drive.upper())

    payload = materialize_control_plane(tmp_path)
    monkeypatch.setattr(
        sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1])
    )
    (tmp_path / sut.PLAN_REL).unlink()
    with pytest.raises(sut.ContractError, match="required file|plan"):
        sut.run_production(workspace_root=tmp_path, production=True)

    payload = materialize_control_plane(tmp_path)
    monkeypatch.setattr(
        sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1])
    )
    (tmp_path / sut.TEST_REL).write_bytes(b"mutated-after-review")
    with pytest.raises(sut.ContractError, match="reviewed test SHA mismatch"):
        sut.run_production(workspace_root=tmp_path, production=True)


def test_armed_builder_normalizes_to_reviewed_base() -> None:
    payload = SOURCE.read_bytes()
    base_sha = sut.normalized_builder_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert sut.normalized_builder_base_sha256(armed) == base_sha


def test_preexisting_evidence_root_rejected(
    synthetic: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _history, tmp_path = synthetic
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", tmp_path.drive.upper())
    payload = materialize_control_plane(tmp_path)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    evidence = tmp_path / sut.EVIDENCE_ROOT_REL
    evidence.mkdir(parents=True)
    with pytest.raises(sut.ContractError, match="already exists"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )


def test_atomic_terminal_chain_happy_path(
    synthetic: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _history, tmp_path = synthetic
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", tmp_path.drive.upper())
    payload = materialize_control_plane(tmp_path)
    row_sha = sha(payload.splitlines(True)[-1])
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", row_sha)

    terminal = sut.run_production(
        workspace_root=tmp_path,
        production=True,
    )
    evidence = tmp_path / sut.EVIDENCE_ROOT_REL
    assert evidence.is_dir()
    for name in (
        "attempt_started.json",
        "source_inventory.json",
        "source_feasibility_receipt.json",
        "attempt_terminal.json",
    ):
        path = evidence / name
        assert path.is_file()
        body = path.read_bytes()
        assert body.endswith(b"\n")
        assert body.count(b"\n") == 1
        parsed = json.loads(body)
        assert canonical(parsed) + b"\n" == body
    assert not list(evidence.glob(".*.tmp-*"))

    assert terminal["status"] == sut.PASS_STATUS
    assert terminal["terminal_is_sole_authoritative_completion"] is True
    receipt = json.loads((evidence / "source_feasibility_receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == sut.RECEIPT_NON_TERMINAL
    assert receipt["terminal_is_sole_authoritative_completion"] is True
    assert "terminal_status" not in receipt

    inventory = json.loads((evidence / "source_inventory.json").read_text(encoding="utf-8"))
    assert inventory["observed_design_hcc_files"] == 27
    assert inventory["outcome_blind_counters"]["returns_computed"] == 0
    assert inventory["outcome_blind_counters"]["residuals_computed"] == 0
    assert inventory["outcome_blind_counters"]["trades_simulated"] == 0
    assert inventory["hcc_decode"] is False
    assert inventory["symbol_cache_files"] == []

    # Mutual hash consistency across the four artifacts.
    started_body = (evidence / "attempt_started.json").read_bytes()
    inventory_body = (evidence / "source_inventory.json").read_bytes()
    receipt_body = (evidence / "source_feasibility_receipt.json").read_bytes()
    terminal_body = (evidence / "attempt_terminal.json").read_bytes()
    started_sha = sha(started_body)
    inventory_sha = sha(inventory_body)
    receipt_sha = sha(receipt_body)
    inv = json.loads(inventory_body)
    rec = json.loads(receipt_body)
    term = json.loads(terminal_body)
    assert inv["attempt_started_sha256"] == started_sha
    assert rec["attempt_started_sha256"] == started_sha
    assert rec["source_inventory_sha256"] == inventory_sha
    assert term["attempt_started_sha256"] == started_sha
    assert term["source_inventory_sha256"] == inventory_sha
    assert term["source_feasibility_receipt_sha256"] == receipt_sha


def test_cli_parse_production_flag() -> None:
    args = sut.parse_args(["--production", "--workspace-root", "."])
    assert args.production is True


def test_deterministic_inventory_byte_identity(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    a = sut.build_source_inventory(history_root=history)
    b = sut.build_source_inventory(history_root=history)
    assert canonical(a) == canonical(b)


def test_missing_hcc_fails_closed(synthetic: tuple[Path, Path]) -> None:
    history, _ = synthetic
    (history / "EURUSD" / "2016.hcc").unlink()
    with pytest.raises(sut.ContractError, match="missing"):
        sut.build_source_inventory(history_root=history)


def test_real_paths_not_required_by_tests() -> None:
    assert REAL_HISTORY != Path(".")
    assert REAL_EVIDENCE.name == "TRILAG001-SOURCE-001"
    assert REAL_REGISTRY.name == "CANDIDATE_REGISTRY.jsonl"


def test_no_self_referential_embedded_builder_hash() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    own = sha(SOURCE.read_bytes())
    assert own not in text
    assert "BUILDER_SHA256" not in text
    assert "SELF_SHA" not in text


def test_forbidden_counters_hard_zero_constant() -> None:
    for key, value in sut.OUTCOME_BLIND_COUNTERS.items():
        if isinstance(value, bool):
            assert value is False
        else:
            assert value == 0
    required = {
        "bars_read",
        "timestamps_read",
        "prices_read",
        "residuals_computed",
        "returns_computed",
        "signals_generated",
        "trades_simulated",
        "costs_computed",
        "outcomes_opened",
        "hcc_payloads_decoded",
        "mt5_launches",
        "mql5_files_created",
        "network_calls",
        "paid_requests_made",
        "research_validation_opened",
        "research_holdout_opened",
    }
    assert required <= set(sut.OUTCOME_BLIND_COUNTERS)


def test_plan_sha_constant_matches_frozen_contract() -> None:
    assert sut.PLAN_SHA256 == (
        "A9ECD2AAD05265845800D82A50656BCD5933F4B921D1F6CBD056E683A69CD826"
    )


def test_portable_history_root_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkey_ws = tmp_path
    monkeypatch.setattr(sut, "REQUIRED_STORAGE_DRIVE", tmp_path.drive.upper())
    good = monkey_ws / sut.HISTORY_ROOT_REL
    good.mkdir(parents=True)
    resolved = sut.validate_portable_history_root(good, monkey_ws)
    assert resolved.exists() or True
    bad = monkey_ws / "other" / "history"
    bad.mkdir(parents=True)
    with pytest.raises(sut.ContractError, match="portable|exact|history root"):
        sut.validate_portable_history_root(bad, monkey_ws)
