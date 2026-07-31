from __future__ import annotations

import importlib.util
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "run_hyp002_grok_each_image.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "run_hyp002_grok_each_image", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_manifest() -> dict:
    results = []
    for index in range(1, 13):
        results.append(
            {
                "case_id": f"F{index:03d}_PID{index:09d}",
                "position_id": str(index),
                "direction": "BUY" if index % 2 else "SELL",
                "stratum": "EXTREME_WIN" if index == 1 else "MEDIAN_LOSS",
                "net_R": 2.0 if index == 1 else -1.0,
                "decision_chart": f"decision_{index}.png",
                "decision_sha256": f"{index:064X}",
                "outcome_chart": f"outcome_{index}.png",
                "outcome_sha256": f"{index + 100:064X}",
            }
        )
    return {"hypothesis_id": "HYP-TEST", "results": results}


def test_job_specs_are_exactly_one_image_and_decisions_first() -> None:
    module = load_module()
    jobs = module.jobs_from_manifest(fake_manifest())
    assert len(jobs) == 24
    assert [job.image_type for job in jobs[:12]] == ["DECISION_ASOF"] * 12
    assert [job.image_type for job in jobs[12:]] == ["OUTCOME_ANATOMY"] * 12
    assert len({job.job_id for job in jobs}) == 24
    assert len({job.image_path for job in jobs}) == 24


def test_decision_job_does_not_leak_outcome_metadata() -> None:
    module = load_module()
    job = module.jobs_from_manifest(fake_manifest())[0]
    request = module.request_payload(job, "prompt-blocks.json", "A" * 64)
    serialized = json.dumps(request)
    assert "EXTREME_WIN" not in serialized
    assert "net_R" not in serialized
    assert "outcome_chart" not in serialized
    assert request["meta"]["outcome_blind"] is True


def test_prompt_blocks_embed_exactly_one_png(tmp_path: Path) -> None:
    module = load_module()
    image = tmp_path / "chart.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"payload")
    job = module.JobSpec(
        job_id="D01",
        case_id="F001_PID000000001",
        position_id="1",
        direction="BUY",
        image_type="DECISION_ASOF",
        image_path=str(image),
        image_sha256=module.sha256_file(image),
    )
    blocks = module.prompt_blocks(job)
    assert [block["type"] for block in blocks] == ["text", "image"]
    assert blocks[1]["mimeType"] == "image/png"
    assert isinstance(blocks[1]["data"], str) and blocks[1]["data"]


def test_result_schema_binds_identity_and_image_opened() -> None:
    module = load_module()
    job = module.jobs_from_manifest(fake_manifest())[0]
    schema = module.result_schema(job)
    properties = schema["properties"]
    assert properties["case_id"]["const"] == job.case_id
    assert properties["image_sha256"]["const"] == job.image_sha256
    assert properties["image_opened"]["const"] is True
    assert properties["no_rule_or_rerun_authority"]["const"] is True

