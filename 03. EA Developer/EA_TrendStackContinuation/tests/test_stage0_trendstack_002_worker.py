from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "research" / "stage0_trendstack_002_worker.py"
PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def pretty_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def make_packet(
    *,
    opportunity_id: str = "2020-01-02",
    split: str = "DESIGN",
    valid_prior_close_count: int = 253,
    m252_direction: int | None = 1,
    m6_direction: int | None = 1,
    atr20: float | None = 0.001,
    exclusion_reason: str | None = None,
) -> dict[str, object]:
    feature_complete = (
        m252_direction in (-1, 1)
        and m6_direction in (-1, 0, 1)
        and atr20 is not None
        and atr20 > 0
    )
    control_m252 = feature_complete
    control_m6 = feature_complete and m6_direction in (-1, 1)
    stack = control_m6 and m252_direction == m6_direction
    disagree = control_m6 and m252_direction == -m6_direction
    if exclusion_reason is None and disagree:
        exclusion_reason = "M252_M6_DISAGREE"
    alignment = (
        m252_direction == m6_direction
        if m252_direction in (-1, 1) and m6_direction in (-1, 1)
        else None
    )
    source_chain = {
        "prior_completed_shards_sha256": "A" * 64,
        "current_pre12_sha256": "B" * 64,
    }
    packet: dict[str, object] = {
        "schema_version": "trendstack_002_decision_packet.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "opportunity_id": opportunity_id,
        "split": split,
        "decision_cutoff_utc": f"{opportunity_id}T12:00:00+00:00",
        "m252_direction": m252_direction,
        "m6_direction": m6_direction,
        "alignment": alignment,
        "atr20": atr20,
        "control_m252_eligible": control_m252,
        "control_m6_eligible": control_m6,
        "challenger_stack_eligible": stack,
        "negative_disagree_eligible": disagree,
        "exclusion_reason": exclusion_reason,
        "valid_prior_close_count": valid_prior_close_count,
        "max_source_time_utc": f"{opportunity_id}T11:00:00+00:00",
        "source_shard_chain_hashes": source_chain,
        "source_chain_sha256": sha256(canonical_bytes(source_chain)),
        "extractor_sha256": "C" * 64,
        "source_plan_sha256": PLAN_SHA256,
    }
    packet["packet_payload_sha256"] = sha256(canonical_bytes(packet))
    return packet


def run_worker(tmp_path: Path, packet: dict[str, object], *, expected_sha: str | None = None):
    packet_path = tmp_path / "packet.json"
    raw = pretty_bytes(packet)
    packet_path.write_bytes(raw)
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(WORKER),
            "--packet",
            "packet.json",
            "--expected-sha256",
            expected_sha or sha256(raw),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (
            {},
            {
                "feature_complete": True,
                "control_m252_only_eligible": True,
                "control_m252_only_direction": 1,
                "control_m6_only_eligible": True,
                "control_m6_only_direction": 1,
                "challenger_stack_eligible": True,
                "challenger_stack_direction": 1,
                "negative_disagree_eligible": False,
                "negative_disagree_direction": None,
            },
        ),
        (
            {"m252_direction": 1, "m6_direction": -1},
            {
                "feature_complete": True,
                "control_m252_only_eligible": True,
                "control_m252_only_direction": 1,
                "control_m6_only_eligible": True,
                "control_m6_only_direction": -1,
                "challenger_stack_eligible": False,
                "challenger_stack_direction": None,
                "negative_disagree_eligible": True,
                "negative_disagree_direction": -1,
            },
        ),
        (
            {"m252_direction": -1, "m6_direction": 0, "exclusion_reason": "M6_EQUALITY"},
            {
                "feature_complete": True,
                "control_m252_only_eligible": True,
                "control_m252_only_direction": -1,
                "control_m6_only_eligible": False,
                "control_m6_only_direction": None,
                "challenger_stack_eligible": False,
                "challenger_stack_direction": None,
                "negative_disagree_eligible": False,
                "negative_disagree_direction": None,
            },
        ),
        (
            {
                "m252_direction": 1,
                "m6_direction": None,
                "atr20": None,
                "exclusion_reason": "MISSING_SIX_HOUR_BAR",
            },
            {
                "feature_complete": False,
                "control_m252_only_eligible": False,
                "control_m252_only_direction": None,
                "control_m6_only_eligible": False,
                "control_m6_only_direction": None,
                "challenger_stack_eligible": False,
                "challenger_stack_direction": None,
                "negative_disagree_eligible": False,
                "negative_disagree_direction": None,
            },
        ),
    ],
)
def test_worker_projects_the_frozen_four_arm_truth_table(
    tmp_path: Path, kwargs: dict[str, object], expected: dict[str, object]
) -> None:
    result = run_worker(tmp_path, make_packet(**kwargs))
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert result.stderr == b""
    assert result.stdout.count(b"\n") == 1
    row = json.loads(result.stdout)
    assert row["schema_version"] == "trendstack_002_stage0_worker_row.v1"
    assert row["hypothesis_id"] == HYPOTHESIS_ID
    assert {key: row[key] for key in expected} == expected
    assert result.stdout == canonical_bytes(row) + b"\n"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda packet: packet.__setitem__("schema_version", "wrong.v1"),
        lambda packet: packet.__setitem__("source_plan_sha256", "0" * 64),
        lambda packet: packet.__setitem__("control_m252_eligible", False),
        lambda packet: packet.__setitem__("challenger_stack_eligible", False),
        lambda packet: packet.__setitem__("source_chain_sha256", "D" * 64),
        lambda packet: packet.__setitem__("max_source_time_utc", packet["decision_cutoff_utc"]),
        lambda packet: packet.__setitem__("unexpected_field", True),
    ],
)
def test_worker_fails_closed_on_packet_tamper(tmp_path: Path, mutator) -> None:
    packet = make_packet()
    mutator(packet)
    packet["packet_payload_sha256"] = sha256(
        canonical_bytes({key: value for key, value in packet.items() if key != "packet_payload_sha256"})
    )
    result = run_worker(tmp_path, packet)
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"INVALID_ENGINEERING" in result.stderr


def test_worker_rejects_file_hash_tamper_before_projection(tmp_path: Path) -> None:
    result = run_worker(tmp_path, make_packet(), expected_sha="0" * 64)
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"INVALID_ENGINEERING" in result.stderr


def test_worker_requires_the_single_literal_staged_path(tmp_path: Path) -> None:
    packet = make_packet()
    raw = canonical_bytes(packet)
    (tmp_path / "other.json").write_bytes(raw)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(WORKER),
            "--packet",
            "other.json",
            "--expected-sha256",
            sha256(raw),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == b""


def test_worker_is_deterministic(tmp_path: Path) -> None:
    packet = make_packet()
    first = run_worker(tmp_path, packet)
    second = run_worker(tmp_path, packet)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert first.stderr == second.stderr == b""


def test_worker_allows_earlier_current_day_source_when_no_current_feature_exists(tmp_path: Path) -> None:
    packet = make_packet(
        m252_direction=1,
        m6_direction=None,
        atr20=None,
        exclusion_reason="MISSING_SIX_HOUR_BAR",
    )
    packet["max_source_time_utc"] = "2020-01-02T10:00:00+00:00"
    packet["packet_payload_sha256"] = sha256(
        canonical_bytes({key: value for key, value in packet.items() if key != "packet_payload_sha256"})
    )
    result = run_worker(tmp_path, packet)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")


@pytest.mark.parametrize("field", ["m252_direction", "m6_direction"])
def test_review_attack_worker_rejects_boolean_direction_values(tmp_path: Path, field: str) -> None:
    packet = make_packet()
    packet[field] = True
    packet["packet_payload_sha256"] = sha256(
        canonical_bytes({key: value for key, value in packet.items() if key != "packet_payload_sha256"})
    )
    result = run_worker(tmp_path, packet)
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"INVALID_ENGINEERING" in result.stderr


def test_review_attack_audit_hook_blocks_integer_writes_dynamic_access_and_has_no_prehook_calls() -> None:
    source = WORKER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    hook_index = next(
        index
        for index, node in enumerate(tree.body)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "addaudithook"
    )
    prehook_calls = [
        call
        for node in tree.body[:hook_index]
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
    ]
    assert prehook_calls == []
    assert "WRITE_FLAG_MASK" in source
    assert '"import"' in source
    assert '"exec"' in source
    assert '"os.chdir"' in source


def test_review_attack_audit_hook_runtime_denies_write_import_chdir_enumeration_and_other_open(
    tmp_path: Path,
) -> None:
    source = WORKER.read_text(encoding="utf-8").replace(
        'if __name__ == "__main__":',
        'if __name__ == "__stage0_worker_main__":',
    )
    attacks = r'''
def expect_denied(action):
    try:
        action()
    except PermissionError:
        return
    raise AssertionError("audit attack was not denied")

expect_denied(lambda: os.open("packet.json", os.O_WRONLY | os.O_CREAT))
expect_denied(lambda: open("other.json", "rb"))
expect_denied(lambda: os.listdir("."))
expect_denied(lambda: os.chdir("."))
expect_denied(lambda: __import__("fractions"))
expect_denied(lambda: eval("1 + 1"))
'''
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", "import os\n" + source + attacks],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")


def test_worker_ast_has_only_the_frozen_stdlib_allowlist_and_early_audit_hook() -> None:
    source = WORKER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= {"argparse", "datetime", "hashlib", "json", "math", "re", "sys", "pathlib"}
    assert "sys.addaudithook(_audit_hook)" in source
    assert source.index("sys.addaudithook(_audit_hook)") < source.index("def main(")
    forbidden_calls = {"glob", "rglob", "iterdir", "listdir", "scandir", "walk"}
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called.isdisjoint(forbidden_calls)
