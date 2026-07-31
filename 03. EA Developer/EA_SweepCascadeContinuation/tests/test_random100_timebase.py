from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pandas as pd


PACKAGE = Path(__file__).resolve().parents[1]
SCRIPT = PACKAGE / "research" / "prepare_hyp004_random100.py"
VALIDATOR = PACKAGE / "research" / "validate_hyp004_random100_casebooks.py"
GROK_BATCHES = PACKAGE / "research" / "prepare_hyp004_random100_grok_batches.py"
GROK_VALIDATOR = PACKAGE / "research" / "validate_hyp004_random100_grok_reviews.py"
GROK_CAMPAIGN = PACKAGE / "research" / "run_hyp004_grok_acp_campaign.py"


def load_prepare_module():
    spec = importlib.util.spec_from_file_location("prepare_hyp004_random100", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator_module():
    spec = importlib.util.spec_from_file_location(
        "validate_hyp004_random100_casebooks", VALIDATOR
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_grok_validator_module():
    spec = importlib.util.spec_from_file_location(
        "validate_hyp004_random100_grok_reviews", GROK_VALIDATOR
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_grok_batches_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_hyp004_random100_grok_batches", GROK_BATCHES
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_grok_campaign_module():
    spec = importlib.util.spec_from_file_location(
        "run_hyp004_grok_acp_campaign", GROK_CAMPAIGN
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lifecycle_server_time_is_converted_to_utc_before_charting() -> None:
    module = load_prepare_module()
    assert module.iso_server_to_utc("2020.03.10 03:15:00") == "2020-03-10T01:15:00"
    assert module.iso_server_to_utc("2022.10.03 00:30:00") == "2022-10-02T21:30:00"


def test_casebook_fields_do_not_relabel_raw_server_time_as_utc() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"entry_time_utc": iso_server_to_utc(row["open_time"])' in source
    assert '"decision_time_utc": iso_server_to_utc(row["decision_time"])' in source
    assert '"exit_time_utc": iso_server_to_utc(row["close_time"])' in source


def test_casebook_qc_rejects_price_markers_on_the_wrong_clock(tmp_path: Path) -> None:
    validator = load_validator_module()
    bars = pd.DataFrame(
        [
            {
                "time_utc": "2020-03-10 01:15:00",
                "open": 1.13905,
                "high": 1.13910,
                "low": 1.13900,
                "close": 1.13907,
            },
            {
                "time_utc": "2020-03-10 01:41:00",
                "open": 1.13995,
                "high": 1.14006,
                "low": 1.13990,
                "close": 1.14004,
            },
            {
                "time_utc": "2020-03-10 03:15:00",
                "open": 1.14500,
                "high": 1.14510,
                "low": 1.14490,
                "close": 1.14500,
            },
            {
                "time_utc": "2020-03-10 03:41:00",
                "open": 1.14600,
                "high": 1.14610,
                "low": 1.14590,
                "close": 1.14600,
            },
        ]
    )
    bars_path = tmp_path / "bars.parquet"
    bars.to_parquet(bars_path, index=False)
    aligned = [
        {
            "case_id": "aligned",
            "entry_time_utc": "2020-03-10T01:15:00",
            "entry": "1.13907",
            "exit_time_utc": "2020-03-10T01:41:37",
            "exit": "1.14004",
        }
    ]
    _, aligned_errors = validator.validate_case_time_alignment(aligned, bars_path)
    assert aligned_errors == []

    wrong_clock = [dict(aligned[0])]
    wrong_clock[0]["entry_time_utc"] = "2020-03-10T03:15:00"
    wrong_clock[0]["exit_time_utc"] = "2020-03-10T03:41:37"
    stats, wrong_errors = validator.validate_case_time_alignment(
        wrong_clock, bars_path
    )
    assert stats["median_distance_points"] > 500
    assert any("clock/price alignment" in error for error in wrong_errors)


def test_grok_visual_batches_embed_png_pixels_not_only_local_paths(
    tmp_path: Path,
) -> None:
    module = load_grok_batches_module()
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAA"
        "FElEQVR4nGP8z4AdMOAQAC0FAB4oAQBl7l8GAAAAAElFTkSuQmCC"
    )
    image_path = tmp_path / "case.png"
    image_path.write_bytes(png)

    block = module.acp_image_block(
        image_path,
        case_id="R100_001_PID000000268",
        view="decision",
    )

    assert block["type"] == "image"
    assert block["mimeType"] == "image/png"
    assert base64.b64decode(block["data"], validate=True) == png
    assert block["_meta"]["case_id"] == "R100_001_PID000000268"
    assert block["_meta"]["view"] == "decision"


def test_grok_review_validator_has_no_batch_specific_manual_rescue() -> None:
    source = GROK_VALIDATOR.read_text(encoding="utf-8")
    assert 'if batch_id == "batch04"' not in source
    assert "normalized_duplicate_response.json" not in source
    assert "caller_normalized_exact_duplicate" not in source


def test_grok_panel_claim_detector_handles_negation_and_word_boundaries() -> None:
    module = load_grok_validator_module()
    assert (
        module.has_forbidden_visual_claim(
            {
                "data_quality_note": (
                    "Modest post-entry mean-reversion hit the stop."
                )
            }
        )
        is False
    )
    assert (
        module.has_forbidden_visual_claim(
            {
                "decision_observations": [
                    "No M15, MACD, RSI, ADX or FVG panel is rendered."
                ]
            }
        )
        is False
    )
    assert (
        module.has_forbidden_visual_claim(
            {"decision_observations": ["M15 shows RSI oversold at entry."]}
        )
        is True
    )


def test_grok_retry_tightens_transport_after_duplicate_json(
    tmp_path: Path,
) -> None:
    module = load_grok_campaign_module()
    batch = tmp_path / "batch13"
    run = batch / "run"
    run2 = batch / "run2"
    run.mkdir(parents=True)
    run2.mkdir()
    (run / "summary.json").write_text("{}", encoding="utf-8")
    (run2 / "summary.json").write_text(
        json.dumps(
            {
                "structured_output_validation": {
                    "error": "ValueError: output_text must contain exactly one JSON instance"
                }
            }
        ),
        encoding="utf-8",
    )
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAA"
        "FElEQVR4nGP8z4AdMOAQAC0FAB4oAQBl7l8GAAAAAElFTkSuQmCC"
    )
    blocks = [{"type": "text", "text": "Return the visual review."}] + [
        {
            "type": "image",
            "data": base64.b64encode(png).decode("ascii"),
            "mimeType": "image/png",
        }
        for _ in range(10)
    ]
    blocks_path = batch / "grok-prompt-blocks.json"
    blocks_path.write_text(json.dumps(blocks), encoding="utf-8")
    schema = {
        "properties": {
            "case_reviews": {
                "items": {
                    "properties": {
                        "decision_observations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "anatomy_observations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                    }
                }
            },
            "batch_findings": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
            },
        }
    }
    request = {
        "task": "batch13",
        "prompt_blocks_file": str(blocks_path),
        "prompt_blocks_sha256": module.sha256(blocks_path),
        "request": {
            "response_format": {
                "json_schema": {
                    "schema": schema,
                }
            }
        },
    }
    original_request = batch / "grok-request.json"
    original_request.write_text(json.dumps(request), encoding="utf-8")

    retry_path, retry_run, retry_number = module.prepare_invocation(batch)
    retry = json.loads(retry_path.read_text(encoding="utf-8"))
    retry_blocks = Path(retry["prompt_blocks_file"])
    frozen_blocks = json.loads(retry_blocks.read_text(encoding="utf-8"))

    assert retry_number == 2
    assert retry_run == batch / "run3"
    assert retry["recovery"]["contract_changed"] is False
    assert retry["recovery"]["output_transport_amended"] is True
    assert retry["prompt_blocks_sha256"] == module.sha256(retry_blocks)
    assert "Never repeat" in frozen_blocks[0]["text"]
    props = retry["request"]["response_format"]["json_schema"]["schema"][
        "properties"
    ]
    assert (
        props["case_reviews"]["items"]["properties"]["decision_observations"][
            "maxItems"
        ]
        == 1
    )
    assert props["batch_findings"]["maxItems"] == 2

    retry_run.mkdir()
    (retry_run / "summary.json").write_text(
        json.dumps(
            {
                "request_file": str(retry_path),
                "structured_output_validation": {"error": None},
            }
        ),
        encoding="utf-8",
    )
    retry_path_2, retry_run_2, retry_number_2 = module.prepare_invocation(batch)
    retry_2 = json.loads(retry_path_2.read_text(encoding="utf-8"))

    assert retry_number_2 == 3
    assert retry_run_2 == batch / "run4"
    assert retry_2["recovery"]["output_transport_amended"] is True
    assert "grok-prompt-blocks-retry3.json" in retry_2["prompt_blocks_file"]


def test_grok_retry_tightens_transport_after_max_token_truncation(
    tmp_path: Path,
) -> None:
    module = load_grok_campaign_module()
    batch = tmp_path / "batch20"
    run = batch / "run"
    run.mkdir(parents=True)
    (run / "summary.json").write_text("{}", encoding="utf-8")
    (run / "run.err").write_text(
        'Internal error: {"error_kind":"max_tokens_truncation"}',
        encoding="utf-8",
    )
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAA"
        "FElEQVR4nGP8z4AdMOAQAC0FAB4oAQBl7l8GAAAAAElFTkSuQmCC"
    )
    blocks_path = batch / "grok-prompt-blocks.json"
    blocks_path.write_text(
        json.dumps(
            [{"type": "text", "text": "Return the visual review."}]
            + [
                {
                    "type": "image",
                    "data": base64.b64encode(png).decode("ascii"),
                    "mimeType": "image/png",
                }
                for _ in range(10)
            ]
        ),
        encoding="utf-8",
    )
    schema = {
        "properties": {
            "case_reviews": {
                "items": {
                    "properties": {
                        "decision_observations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                        "anatomy_observations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "string"},
                        },
                    }
                }
            },
            "batch_findings": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
            },
        }
    }
    original_request = batch / "grok-request.json"
    original_request.write_text(
        json.dumps(
            {
                "task": "batch20",
                "prompt_blocks_file": str(blocks_path),
                "prompt_blocks_sha256": module.sha256(blocks_path),
                "request": {
                    "response_format": {
                        "json_schema": {
                            "schema": schema,
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    retry_path, _, retry_number = module.prepare_invocation(batch)
    retry = json.loads(retry_path.read_text(encoding="utf-8"))

    assert retry_number == 1
    assert retry["recovery"]["output_transport_amended"] is True
    assert "grok-prompt-blocks-retry1.json" in retry["prompt_blocks_file"]
