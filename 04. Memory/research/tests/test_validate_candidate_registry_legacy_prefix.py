from __future__ import annotations

import importlib.util
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
VALIDATOR = RESEARCH / "validate_candidate_registry.py"
REGISTRY = RESEARCH / "CANDIDATE_REGISTRY.jsonl"
SCHEMA = RESEARCH / "CANDIDATE_REGISTRY.schema.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("candidate_validator_legacy", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_anchored_canonical_registry_validates_current_suffix() -> None:
    validator = load_validator()

    assert validator.validate_registry(REGISTRY, SCHEMA) == []


def test_any_legacy_prefix_mutation_breaks_the_anchor(tmp_path: Path) -> None:
    validator = load_validator()
    lines = REGISTRY.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) > validator.LEGACY_PREFIX_LAST_LINE
    lines[0] = lines[0].replace('"reason":', '"reason_legacy_mutation":', 1)
    mutated = tmp_path / "CANDIDATE_REGISTRY.jsonl"
    mutated.write_text("\n".join(lines) + "\n", encoding="utf-8")

    errors = validator.validate_registry(mutated, SCHEMA)

    assert any("legacy registry prefix SHA256 mismatch" in error for error in errors)


def test_suffix_errors_are_never_grandfathered(tmp_path: Path) -> None:
    validator = load_validator()
    text = REGISTRY.read_text(encoding="utf-8-sig")
    appended_line = len(text.splitlines()) + 1
    invalid = tmp_path / "CANDIDATE_REGISTRY.jsonl"
    invalid.write_text(text + "{}\n", encoding="utf-8")

    errors = validator.validate_registry(invalid, SCHEMA)

    assert errors
    assert any(f"line {appended_line}" in error for error in errors)
