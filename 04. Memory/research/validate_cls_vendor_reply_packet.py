#!/usr/bin/env python3
"""Fail-closed validator for the CLS written vendor-reply metadata packet."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cls_fx_spot_flow_vendor_reply_packet.v1"
PACKET_SCOPE = "WRITTEN_VENDOR_REPLY_METADATA_ONLY"
SOURCE_OBJECT_ID = "CLS-FXSPOTFLOW-FUND-G10CS-DAILY"
CONTACT_ROUTE = "enquiries@cls-group.com"
ALLOWED_CONTACT_STATES = {"NOT_SENT", "SENT_AWAITING_REPLY", "REPLY_RECEIVED"}
ALLOWED_GATE_STATES = {"NOT_EVALUATED", "PASS", "FAIL"}
REQUIRED_FALSE_AUTHORITIES = {
    "trial_authorized",
    "purchase_authorized",
    "sample_access_authorized",
    "api_credentials_authorized",
    "source_download_authorized",
    "outcome_prices_authorized",
    "economics_authorized",
    "mql5_authorized",
    "mt5_authorized",
    "paper_trading_authorized",
    "live_trading_authorized",
    "owner_cost_ceiling_approved",
}
REQUIRED_FALSE_VERDICTS = {
    "source_intake_pass",
    "hypothesis_authorized",
    "engineering_valid",
    "economic_valid",
    "promotion_ready",
}
FORBIDDEN_OUTCOME_KEYS = {
    "profit_factor",
    "pnl",
    "net_profit",
    "return",
    "returns",
    "target_price",
    "ohlc",
    "trade_count",
    "expectancy",
    "drawdown",
}


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(packet.get("schema_version") == SCHEMA_VERSION, "schema_version mismatch", errors)
    _require(packet.get("packet_scope") == PACKET_SCOPE, "packet_scope mismatch", errors)
    _require(packet.get("source_object_id") == SOURCE_OBJECT_ID, "source_object_id mismatch", errors)

    contracts = packet.get("bound_contracts")
    _require(isinstance(contracts, list) and len(contracts) == 3, "three bound contracts required", errors)
    if isinstance(contracts, list):
        kinds = {item.get("kind") for item in contracts if isinstance(item, dict)}
        _require(
            kinds == {"inquiry_r2", "fifteen_gate_intake_contract", "pre_contact_review"},
            "bound contract kinds mismatch",
            errors,
        )
        for item in contracts:
            if not isinstance(item, dict):
                errors.append("bound contract must be an object")
                continue
            _require(bool(item.get("path")), f"contract path missing: {item.get('kind')}", errors)
            _require(
                bool(re.fullmatch(r"[0-9A-F]{64}", str(item.get("sha256", "")))),
                f"contract sha256 invalid: {item.get('kind')}",
                errors,
            )

    contact = packet.get("contact_state")
    _require(isinstance(contact, dict), "contact_state object required", errors)
    if isinstance(contact, dict):
        _require(contact.get("status") in ALLOWED_CONTACT_STATES, "invalid contact status", errors)
        _require(contact.get("route") == CONTACT_ROUTE, "contact route mismatch", errors)
        if contact.get("status") == "NOT_SENT":
            _require(contact.get("owner_contact_authorized") is False, "unsent packet cannot claim contact authority", errors)
            _require(contact.get("sent_at_utc") is None, "unsent packet cannot have sent_at_utc", errors)

    reply = packet.get("reply")
    _require(isinstance(reply, dict), "reply object required", errors)
    reply_received = bool(reply.get("received")) if isinstance(reply, dict) else False
    if isinstance(reply, dict):
        if reply_received:
            _require(contact.get("status") == "REPLY_RECEIVED", "received reply requires REPLY_RECEIVED contact state", errors)
            _require(bool(reply.get("received_at_utc")), "received reply requires received_at_utc", errors)
            _require(bool(reply.get("sender")), "received reply requires sender", errors)
            _require(
                bool(re.fullmatch(r"[0-9A-F]{64}", str(reply.get("body_sha256", "")))),
                "received reply requires uppercase SHA256 body hash",
                errors,
            )
        else:
            _require(contact.get("status") != "REPLY_RECEIVED", "REPLY_RECEIVED state requires reply.received=true", errors)

    gates = packet.get("gates")
    _require(isinstance(gates, list) and len(gates) == 15, "exactly fifteen gates required", errors)
    gate_by_id: dict[int, dict[str, Any]] = {}
    if isinstance(gates, list):
        for gate in gates:
            if not isinstance(gate, dict) or not isinstance(gate.get("id"), int):
                errors.append("each gate requires an integer id")
                continue
            gate_id = gate["id"]
            if gate_id in gate_by_id:
                errors.append(f"duplicate gate id {gate_id}")
            gate_by_id[gate_id] = gate
            status = gate.get("status")
            _require(status in ALLOWED_GATE_STATES, f"invalid gate status {gate_id}", errors)
            refs = gate.get("evidence_refs")
            _require(isinstance(refs, list), f"gate {gate_id} evidence_refs must be a list", errors)
            if status == "PASS":
                _require(bool(refs), f"gate {gate_id} PASS requires evidence_refs", errors)
            if status == "FAIL":
                _require(bool(gate.get("reason")), f"gate {gate_id} FAIL requires reason", errors)
        _require(set(gate_by_id) == set(range(1, 16)), "gate ids must be exactly 1..15", errors)

    for gate_id in range(10, 16):
        gate = gate_by_id.get(gate_id, {})
        _require(
            gate.get("status") == "NOT_EVALUATED",
            f"gate {gate_id} cannot be evaluated from a written vendor reply",
            errors,
        )

    if not reply_received:
        for gate_id, gate in gate_by_id.items():
            _require(
                gate.get("status") == "NOT_EVALUATED",
                f"unsent/unreceived packet cannot evaluate gate {gate_id}",
                errors,
            )

    authority = packet.get("authority")
    _require(isinstance(authority, dict), "authority object required", errors)
    if isinstance(authority, dict):
        for key in REQUIRED_FALSE_AUTHORITIES:
            _require(authority.get(key) is False, f"{key} must remain false", errors)

    verdict = packet.get("verdict")
    _require(isinstance(verdict, dict), "verdict object required", errors)
    if isinstance(verdict, dict):
        for key in REQUIRED_FALSE_VERDICTS:
            _require(verdict.get(key) is False, f"{key} must remain false", errors)
        if not reply_received:
            _require(
                verdict.get("vendor_reply_metadata_complete") is False,
                "unreceived reply cannot be metadata-complete",
                errors,
            )

    forbidden = sorted(_walk_keys(packet) & FORBIDDEN_OUTCOME_KEYS)
    _require(not forbidden, f"outcome fields forbidden in reply packet: {', '.join(forbidden)}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"CLS_VENDOR_REPLY_PACKET_INVALID: {exc}", file=sys.stderr)
        return 2
    if not isinstance(packet, dict):
        print("CLS_VENDOR_REPLY_PACKET_INVALID: root must be an object", file=sys.stderr)
        return 2
    errors = validate_packet(packet)
    if errors:
        for error in errors:
            print(f"CLS_VENDOR_REPLY_PACKET_ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "CLS_VENDOR_REPLY_PACKET_OK: "
        f"scope={packet['packet_scope']} gates=15 source_intake_pass=false authorities_closed=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
