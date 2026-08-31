import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "04. Memory" / "research"
TEMPLATE = RESEARCH / "20260813_CLS_FX_SPOT_FLOW_VENDOR_REPLY_PACKET.template.json"
VALIDATOR = RESEARCH / "validate_cls_vendor_reply_packet.py"

SPEC = importlib.util.spec_from_file_location("cls_reply_validator", VALIDATOR)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def load_template():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_pristine_template_is_valid_and_closed():
    assert MODULE.validate_packet(load_template()) == []


def test_source_intake_cannot_be_promoted_from_vendor_reply():
    packet = load_template()
    packet["verdict"]["source_intake_pass"] = True
    assert "source_intake_pass must remain false" in MODULE.validate_packet(packet)


def test_purchase_authority_must_remain_closed():
    packet = load_template()
    packet["authority"]["purchase_authorized"] = True
    assert "purchase_authorized must remain false" in MODULE.validate_packet(packet)


def test_sample_gate_cannot_pass_in_written_reply_packet():
    packet = load_template()
    packet["gates"][9]["status"] = "PASS"
    packet["gates"][9]["evidence_refs"] = ["attachment://manifest.json"]
    assert "gate 10 cannot be evaluated from a written vendor reply" in MODULE.validate_packet(packet)


def test_pass_gate_requires_evidence_reference():
    packet = load_template()
    packet["reply"].update(
        {
            "received": True,
            "received_at_utc": "2026-08-14T00:00:00Z",
            "sender": "enquiries@cls-group.com",
            "body_sha256": "A" * 64,
        }
    )
    packet["contact_state"].update(
        {"status": "REPLY_RECEIVED", "owner_contact_authorized": True, "sent_at_utc": "2026-08-13T00:00:00Z"}
    )
    packet["gates"][0]["status"] = "PASS"
    assert "gate 1 PASS requires evidence_refs" in MODULE.validate_packet(packet)


def test_outcome_fields_are_rejected():
    packet = load_template()
    packet["vendor_assertions"]["profit_factor"] = 1.5
    errors = MODULE.validate_packet(packet)
    assert any("outcome fields forbidden" in error for error in errors)


def test_gate_set_must_be_exactly_one_through_fifteen():
    packet = load_template()
    packet["gates"] = copy.deepcopy(packet["gates"][:-1])
    errors = MODULE.validate_packet(packet)
    assert "exactly fifteen gates required" in errors
    assert "gate ids must be exactly 1..15" in errors
