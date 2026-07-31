"""Synthetic tmp_path tests for G10 XMOM source-inventory builder.

No real HCC, MT5, registry or evidence root is accessed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Iterator

import importlib.util
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "build_g10_xmom_001_source.py"
SPEC = importlib.util.spec_from_file_location("build_g10_xmom_001_source", SOURCE)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)

REAL_HISTORY = (
    Path(r"D:/Trading EA MT5/02. AlphaFactory/runtime/mt5-portable-fivepercent")
    / "Bases/FivePercentOnline-Real/history"
)
REAL_EVIDENCE = (
    Path(r"D:/Trading EA MT5/03. EA Developer/EA_G10WeeklyXSMomentum/research/evidence")
    / "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY"
    / "G10XMOM001-SOURCE-001"
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


def build_synthetic_tree(tmp_path: Path) -> tuple[Path, Path]:
    history = tmp_path / sut.HISTORY_ROOT_REL
    symbols = tmp_path / sut.SYMBOLS_ROOT_REL
    for symbol in sut.BROKER_SYMBOLS:
        for year in sut.DESIGN_YEARS:
            content = f"opaque-{symbol}-{year}-payload".encode("ascii") * 3
            write_opaque(history / symbol / f"{year}.hcc", content)
    write_opaque(symbols / "symbols-26451822.dat", b"symbols-cache-opaque-bytes-001")
    write_opaque(symbols / "selected-26451822.dat", b"selected-cache-opaque-bytes-002")
    return history, symbols


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
    plan_source = SOURCE.parent / "HYP-G10-XMOM-W1-001_SOURCE_FEASIBILITY_PLAN.md"
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
def synthetic(tmp_path: Path) -> Iterator[tuple[Path, Path, Path]]:
    history, symbols = build_synthetic_tree(tmp_path)
    yield history, symbols, tmp_path


# ---------------------------------------------------------------------------
# Import inert / identity
# ---------------------------------------------------------------------------


def test_sentinel_is_exactly_disarmed_and_import_inert() -> None:
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    text = SOURCE.read_bytes()
    assert b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" in text
    matches = [line for line in text.splitlines() if sut._SENTINEL_RE.match(line.rstrip(b"\n"))]
    assert len(matches) == 1
    # No MetaTrader5 import in source AST.
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
        if "FivePercentOnline-Real" in text or "G10XMOM001-SOURCE-001" in text:
            raise AssertionError(f"real path touched on import-inert surface: {text}")
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", guarded_lstat)
    # Re-using already imported module must still not call into real roots.
    paths = sut.expected_hcc_paths(Path("C:/synthetic-history-root-only"))
    assert len(paths) == 49
    for path in paths:
        assert "2025" not in path.name
        assert "2026" not in path.name
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


def test_exact_49_paths_no_parent_enumeration(synthetic: tuple[Path, Path, Path]) -> None:
    history, _symbols, _ = synthetic
    paths = sut.expected_hcc_paths(history)
    assert len(paths) == 49
    assert len(set(paths)) == 49
    relatives = sut.expected_hcc_relative_paths()
    assert len(relatives) == 49
    assert relatives[0] == "AUDUSD/2018.hcc"
    assert relatives[-1] == "USDJPY/2024.hcc"
    # Exact symbols x years
    expected = {
        f"{symbol}/{year}.hcc"
        for symbol in sut.BROKER_SYMBOLS
        for year in sut.DESIGN_YEARS
    }
    assert set(relatives) == expected


def test_no_holdout_path_construction() -> None:
    relatives = sut.expected_hcc_relative_paths()
    joined = "\n".join(relatives)
    assert "2025.hcc" not in joined
    assert "2026.hcc" not in joined
    for year in sut.HOLDOUT_YEARS_FORBIDDEN:
        assert f"{year}.hcc" not in joined


def test_exact_two_symbol_cache_paths(synthetic: tuple[Path, Path, Path]) -> None:
    _history, symbols, _ = synthetic
    caches = sut.expected_symbol_cache_paths(symbols)
    assert len(caches) == 2
    assert caches[0].name == "symbols-26451822.dat"
    assert caches[1].name == "selected-26451822.dat"


def test_orientation_map_four_direct_three_inverse() -> None:
    result = sut.validate_orientation_map()
    assert result["direct_count"] == 4
    assert result["inverse_count"] == 3
    assert result["balanced"] is True
    assert result["complete"] is True


def test_structural_four_legs_per_week() -> None:
    identity = sut.STRUCTURAL_PORTFOLIO_IDENTITY
    assert identity["intended_entry_legs_per_eligible_week"] == 4
    assert identity["counts_legs_not_rebalance_events"] is True


# ---------------------------------------------------------------------------
# Hashing / inventory happy path
# ---------------------------------------------------------------------------


def test_happy_path_inventory_deterministic(synthetic: tuple[Path, Path, Path]) -> None:
    history, symbols, _ = synthetic
    first = sut.build_source_inventory(history_root=history, symbols_root=symbols)
    second = sut.build_source_inventory(history_root=history, symbols_root=symbols)
    assert first["observed_design_hcc_files"] == 49
    assert len(first["hcc_files"]) == 49
    assert len(first["symbol_cache_files"]) == 2
    assert first["outcome_blind_counters"] == sut.OUTCOME_BLIND_COUNTERS
    assert first["inventory_sha256"] == second["inventory_sha256"]
    assert canonical(first) == canonical(second)
    gates = sut.evaluate_inventory_gates(first)
    assert gates["all_passed"] is True
    assert gates["status"] == sut.PASS_STATUS


def test_hash_stability_and_mutation_rejection(
    synthetic: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    history, _symbols, _ = synthetic
    target = history / "AUDUSD" / "2018.hcc"
    record = sut.hash_opaque_stable(target)
    assert record["stable"] is True
    assert len(str(record["sha256"])) == 64

    # Mutate file contents during the streaming read so after-stat size changes.
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
        sut.hash_opaque_stable(target)


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


def test_opaque_hash_matches_sha256_of_bytes(synthetic: tuple[Path, Path, Path]) -> None:
    history, _symbols, _ = synthetic
    path = history / "EURUSD" / "2020.hcc"
    expected = sha(path.read_bytes())
    got = sut.hash_opaque_stable(path)["sha256"]
    assert got == expected


# ---------------------------------------------------------------------------
# Production gates
# ---------------------------------------------------------------------------


def test_production_requires_explicit_flag(synthetic: tuple[Path, Path, Path]) -> None:
    history, symbols, tmp_path = synthetic
    with pytest.raises(sut.ContractError, match="disarmed|--production"):
        sut.run_production(
            workspace_root=tmp_path,
            production=False,
        )


def test_production_disarmed_sentinel(synthetic: tuple[Path, Path, Path]) -> None:
    history, symbols, tmp_path = synthetic
    assert sut.REVIEWED_REGISTRY_ROW_SHA256 is None
    with pytest.raises(sut.ContractError, match="disarmed|sentinel"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )


def test_production_registry_and_prereg_and_source_run_gates(
    synthetic: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    history, symbols, tmp_path = synthetic
    monkeypatch.setattr(sut, "CANONICAL_WORKSPACE_ROOT", tmp_path)

    # Wrong state
    payload = materialize_control_plane(tmp_path, state="killed", source_run=True)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="source_run_authorized|probe|prereg"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    # source_run false
    payload = materialize_control_plane(
        tmp_path, state="probe", source_build=True, source_run=False
    )
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="source_run_authorized"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    # prereg mismatch
    bad_sha = "0" * 64
    payload = materialize_control_plane(tmp_path, prereg_sha=bad_sha)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", sha(payload.splitlines(True)[-1]))
    with pytest.raises(sut.ContractError, match="prereg"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )

    # sentinel mismatch
    payload = materialize_control_plane(tmp_path)
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", "A" * 64)
    with pytest.raises(sut.ContractError, match="sentinel|latest row"):
        sut.run_production(
            workspace_root=tmp_path,
            production=True,
        )


def test_production_requires_canonical_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sut, "REVIEWED_REGISTRY_ROW_SHA256", "A" * 64)
    with pytest.raises(sut.ContractError, match="canonical D-side workspace"):
        sut.run_production(workspace_root=tmp_path, production=True)


def test_production_requires_plan_and_exact_reviewed_hashes(
    synthetic: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    _history, _symbols, tmp_path = synthetic
    monkeypatch.setattr(sut, "CANONICAL_WORKSPACE_ROOT", tmp_path)

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
    synthetic: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    history, symbols, tmp_path = synthetic
    monkeypatch.setattr(sut, "CANONICAL_WORKSPACE_ROOT", tmp_path)
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
    synthetic: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    history, symbols, tmp_path = synthetic
    monkeypatch.setattr(sut, "CANONICAL_WORKSPACE_ROOT", tmp_path)
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
        # Canonical: single LF-terminated object
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
    assert inventory["observed_design_hcc_files"] == 49
    assert inventory["outcome_blind_counters"]["returns_computed"] == 0
    assert inventory["outcome_blind_counters"]["trades_simulated"] == 0
    assert inventory["hcc_decode"] is False


def test_cli_parse_production_flag() -> None:
    args = sut.parse_args(["--production", "--workspace-root", "."])
    assert args.production is True


def test_deterministic_inventory_byte_identity(synthetic: tuple[Path, Path, Path]) -> None:
    history, symbols, _ = synthetic
    a = sut.build_source_inventory(history_root=history, symbols_root=symbols)
    b = sut.build_source_inventory(history_root=history, symbols_root=symbols)
    assert canonical(a) == canonical(b)


def test_missing_hcc_fails_closed(synthetic: tuple[Path, Path, Path]) -> None:
    history, symbols, _ = synthetic
    (history / "AUDUSD" / "2018.hcc").unlink()
    with pytest.raises(sut.ContractError, match="missing"):
        sut.build_source_inventory(history_root=history, symbols_root=symbols)


def test_real_paths_not_required_by_tests() -> None:
    # Tests must not depend on real HCC existence.
    assert REAL_HISTORY != Path(".")
    # We never call into these in happy-path unit tests above.
    assert REAL_EVIDENCE.name == "G10XMOM001-SOURCE-001"
    assert REAL_REGISTRY.name == "CANDIDATE_REGISTRY.jsonl"


def test_no_self_referential_embedded_builder_hash() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    # Builder must not embed its own content hash as a frozen constant of itself.
    own = sha(SOURCE.read_bytes())
    assert own not in text
    assert "BUILDER_SHA256" not in text
    assert "SELF_SHA" not in text


def test_economic_counters_hard_zero_constant() -> None:
    for key, value in sut.OUTCOME_BLIND_COUNTERS.items():
        if isinstance(value, bool):
            assert value is False
        else:
            assert value == 0
