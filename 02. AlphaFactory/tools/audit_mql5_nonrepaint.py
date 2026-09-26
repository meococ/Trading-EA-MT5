#!/usr/bin/env python3
"""Fail-closed static audit of run-snapshotted MQL5 closed-bar invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "alphafactory_nonrepaint_audit.v1"
BAR_FUNCTIONS = {"iOpen", "iHigh", "iLow", "iClose", "iVolume"}
COPY_FUNCTIONS = {
    "CopyRates",
    "CopyBuffer",
    "CopyTime",
    "CopyOpen",
    "CopyHigh",
    "CopyLow",
    "CopyClose",
    "CopyTickVolume",
    "CopyRealVolume",
}
EXTREME_FUNCTIONS = {"iHighest", "iLowest"}
COLLECTION_AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
MODEL4_COLLECTION_AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
COLLECTION_AUTHORITIES = {COLLECTION_AUTHORITY, MODEL4_COLLECTION_AUTHORITY}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def sanitize_mql(text: str) -> str:
    """Remove comments/string contents while preserving offsets and newlines."""
    out = list(text)
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                out[index] = out[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and nxt == "*":
                out[index] = out[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char in {'"', "'"}:
                quote = char
                out[index] = " "
                index += 1
                state = "string"
                continue
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                out[index] = " "
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                out[index] = out[index + 1] = " "
                index += 2
                state = "code"
                continue
            if char != "\n":
                out[index] = " "
        elif state == "string":
            if char == "\\" and nxt:
                out[index] = out[index + 1] = " "
                index += 2
                continue
            if char == quote:
                state = "code"
            if char != "\n":
                out[index] = " "
        index += 1
    return "".join(out)


def split_args(body: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(body):
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            args.append(body[start:index].strip())
            start = index + 1
    args.append(body[start:].strip())
    return args


def iter_calls(text: str):
    function_names = sorted(COPY_FUNCTIONS | BAR_FUNCTIONS | EXTREME_FUNCTIONS | {"iTime"})
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, function_names)) + r")\s*\(")
    for match in pattern.finditer(text):
        open_index = text.find("(", match.start())
        depth = 1
        index = open_index + 1
        while index < len(text) and depth:
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
            index += 1
        if depth:
            yield match.group(1), match.start(), "", False
        else:
            yield match.group(1), match.start(), text[open_index + 1 : index - 1], True


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def is_literal_zero(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    return bool(re.fullmatch(r"(?:\(?0(?:\.0*)?\)?|0[Ll])", compact))


def is_literal_closed_bar_shift(value: str) -> bool:
    """Only a provably positive integer shift satisfies the static gate."""
    compact = re.sub(r"\s+", "", value)
    return bool(re.fullmatch(r"\(?[1-9]\d*[Ll]?\)?", compact))


def allowed_new_bar_gate(text: str, call_offset: int) -> bool:
    line_start = text.rfind("\n", 0, call_offset) + 1
    window = text[line_start : min(len(text), call_offset + 700)]
    assignment = re.search(
        r"\b(?:datetime|long|int)\s+(?P<current>[A-Za-z_]\w*)\s*=\s*iTime\s*\([^;]+\)\s*;",
        window,
        flags=re.DOTALL,
    )
    if not assignment:
        return False
    current = re.escape(assignment.group("current"))
    comparison = re.search(
        rf"if\s*\(\s*{current}\s*==\s*(?P<stored>[A-Za-z_]\w*)\s*\)\s*\{{?[^}}]{{0,300}}\breturn\s*;",
        window,
        flags=re.DOTALL,
    )
    if not comparison:
        return False
    stored = re.escape(comparison.group("stored"))
    return bool(re.search(rf"\b{stored}\s*=\s*{current}\s*;", window, flags=re.DOTALL))


CONTROL_BLOCK_KEYWORDS = {"if", "for", "while", "switch", "foreach"}


def enclosing_function_span(text: str, offset: int) -> tuple[int, int] | None:
    """Brace span of the function body enclosing ``offset`` in sanitized text.

    Walks outward through control blocks (``if``/``for``/``while``/...) until it
    reaches a brace block directly preceded by a non-control ``name(...)``
    signature, then returns that block's ``{...}`` span.
    """
    open_index = offset
    while True:
        depth = 0
        index = open_index - 1
        while index >= 0:
            char = text[index]
            if char == "}":
                depth += 1
            elif char == "{":
                if depth:
                    depth -= 1
                else:
                    break
            index -= 1
        if index < 0:
            return None
        open_index = index
        probe = open_index - 1
        while probe >= 0 and text[probe].isspace():
            probe -= 1
        if probe >= 0 and text[probe] == ")":
            depth = 1
            paren = probe - 1
            while paren >= 0 and depth:
                if text[paren] == ")":
                    depth += 1
                elif text[paren] == "(":
                    depth -= 1
                paren -= 1
            end = paren + 1
            while paren >= 0 and (text[paren].isalnum() or text[paren] == "_"):
                paren -= 1
            name = text[paren + 1 : end]
            if name and name.lower() not in CONTROL_BLOCK_KEYWORDS:
                break
        # else/try/control blocks keep the walk moving outward
    close = open_index + 1
    depth = 1
    while close < len(text) and depth:
        if text[close] == "{":
            depth += 1
        elif text[close] == "}":
            depth -= 1
        close += 1
    return open_index, close


def allowed_guarded_shift_param(
    text: str, args: list[str], offset: int, arg_index: int = 2
) -> bool:
    """Identifier shift arg proven >= 1 by a dominating ``if(param<1) return``
    guard earlier in the enclosing function body."""
    if len(args) <= arg_index:
        return False
    param = args[arg_index].strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", param):
        return False
    span = enclosing_function_span(text, offset)
    if span is None:
        return False
    before = text[span[0] : offset]
    guard = re.compile(
        rf"if\s*\([^)]*\b{re.escape(param)}\s*<\s*1\b[^)]*\)\s*return\b"
    )
    return bool(guard.search(before))


def allowed_for_loop_shift(
    text: str, args: list[str], offset: int, arg_index: int = 2
) -> bool:
    """Identifier shift arg proven >= 1 because it is the induction variable
    of an enclosing ``for(int v=N; cond; incr)`` whose literal init N >= 1,
    whose increment clause never decrements, and whose body never
    decrements, subtracts from, or reassigns the variable."""
    if len(args) <= arg_index:
        return False
    var = args[arg_index].strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", var):
        return False
    head = re.compile(
        rf"for\s*\(\s*int\s+{re.escape(var)}\s*=\s*(\d+)\s*;[^;]*;[^)]*\)"
    )
    for m in head.finditer(text):
        if int(m.group(1)) < 1:
            continue
        clause = m.group(0)
        if re.search(
            rf"--\s*{re.escape(var)}\b|{re.escape(var)}\s*--|"
            rf"{re.escape(var)}\s*-=|-=\s*{re.escape(var)}\b",
            clause,
        ):
            continue
        pos = m.end()
        while pos < len(text) and text[pos] in " \t\r\n":
            pos += 1
        if pos >= len(text):
            continue
        if text[pos] == "{":
            depth, j = 1, pos + 1
            while j < len(text) and depth:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            body_start, body_end = pos + 1, j - 1
        else:
            j = text.find(";", pos)
            if j < 0:
                continue
            body_start, body_end = pos, j
        if not (body_start <= offset <= body_end):
            continue
        body = text[body_start:body_end]
        if re.search(rf"\b{re.escape(var)}\s*=(?!=)", body):
            continue
        if re.search(
            rf"--\s*{re.escape(var)}\b|{re.escape(var)}\s*--|"
            rf"{re.escape(var)}\s*-=",
            body,
        ):
            continue
        return True
    return False


def allowed_bounded_datetime_range(
    text: str, function: str, args: list[str], offset: int
) -> bool:
    """Five-arg datetime-range overload (sym, tf, start_time, stop_time, buf)
    proven closed-only: both range args are ``datetime``-typed and the stop
    arg is clamped to ``iTime(<tf>, >=1)`` earlier in the same function."""
    if len(args) != 5:
        return False
    start, stop = args[2].strip(), args[3].strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", start) or not re.fullmatch(
        r"[A-Za-z_]\w*", stop
    ):
        return False
    span = enclosing_function_span(text, offset)
    if span is None:
        return False
    sig_open = text.rfind("(", 0, span[0])
    region = text[sig_open : span[1]] if sig_open >= 0 else text[span[0] : span[1]]
    before = text[sig_open if sig_open >= 0 else span[0] : offset]
    for name in (start, stop):
        if not re.search(rf"\bdatetime\b[^;,)]*\b{re.escape(name)}\b", region):
            return False
    var = None
    clamp = re.search(
        rf"if\s*\(\s*{re.escape(stop)}\s*>\s*([A-Za-z_]\w*)\s*\)\s*"
        rf"{re.escape(stop)}\s*=\s*\1",
        before,
    )
    if clamp:
        var = clamp.group(1)
    else:
        fold = re.search(
            rf"{re.escape(stop)}\s*=\s*(?:MathMin|fmin)\s*\(\s*"
            rf"{re.escape(stop)}\s*,\s*([A-Za-z_]\w*)\s*\)",
            before,
        )
        if fold:
            var = fold.group(1)
    if var is None:
        return False
    return bool(
        re.search(
            rf"\b{re.escape(var)}\s*=\s*iTime\s*\([^)]*,\s*[1-9]\d*\s*\)", before
        )
    )


def allowed_collection_provenance_copytime(
    original: str,
    text: str,
    function: str,
    args: list[str],
    probe_authorized: bool,
    offset: int,
) -> bool:
    """Allow only the frozen no-trade first-date retrieval probe.

    The probe is authorized either by a verified collection receipt or by the
    run's own data-quality contract, which mandates the emitted proof line."""
    if not probe_authorized or function != "CopyTime" or len(args) != 5:
        return False
    compact_args = [re.sub(r"\s+", "", arg) for arg in args]
    if compact_args != ["_Symbol", "PERIOD_M5", "copytime_from", "1", "copytime_values"]:
        return False
    compact = re.sub(r"\s+", "", text)
    exact_call = "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)"
    if compact.count(exact_call) != 1:
        return False
    required = (
        "constdatetimecopytime_from=(datetime)m5_first_epoch;",
        "ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE",
        "copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);",
        "copytime_result!=1||copytime_first_epoch!=m5_first_epoch||copytime_error!=0",
    )
    if "DATA_EPOCH_D0_SERIES_PROOF" not in original or any(item not in compact for item in required):
        return False
    forbidden = re.compile(
        r"\b(?:CTrade|OrderSend|OrderCheck|PositionOpen|PositionClose|HistoryDeal|FileOpen|FileWrite|FileRead)\b"
    )
    # The no-trade guarantee applies to the function emitting the probe, not
    # the whole file — a governed trading EA necessarily calls CTrade et al.
    span = enclosing_function_span(text, offset)
    return span is not None and forbidden.search(text[span[0] : span[1]]) is None


def audit_file(
    path: Path, *, probe_authorized: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    original = path.read_text(encoding="utf-8-sig", errors="strict")
    text = sanitize_mql(original)
    findings: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []

    for function, offset, body, complete in iter_calls(text):
        line = line_number(text, offset)
        if not complete:
            findings.append(
                {"path": str(path), "line": line, "rule": "unclosed_call", "function": function}
            )
            continue
        args = split_args(body)
        if function in COPY_FUNCTIONS:
            if len(args) < 3:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_copy_call", "function": function}
                )
            elif allowed_collection_provenance_copytime(
                original, text, function, args, probe_authorized, offset
            ):
                allowed.append(
                    {
                        "path": str(path),
                        "line": line,
                        "rule": "collection_first_date_copytime",
                        "function": function,
                        "disposition": "allowed_collection_provenance_read",
                    }
                )
            elif is_literal_zero(args[2]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_copy", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[2]):
                record = {
                    "path": str(path),
                    "line": line,
                    "rule": "unproven_closed_bar_shift",
                    "function": function,
                    "shift_expression": args[2],
                }
                if allowed_guarded_shift_param(text, args, offset):
                    record["disposition"] = "allowed_guarded_shift_param"
                    allowed.append(record)
                elif allowed_for_loop_shift(text, args, offset):
                    record["disposition"] = "allowed_for_loop_shift"
                    allowed.append(record)
                elif allowed_bounded_datetime_range(text, function, args, offset):
                    record["disposition"] = "allowed_bounded_datetime_range"
                    allowed.append(record)
                else:
                    findings.append(record)
        elif function in BAR_FUNCTIONS:
            if len(args) < 3:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_series_call", "function": function}
                )
            elif is_literal_zero(args[2]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_series", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[2]):
                record = {
                    "path": str(path),
                    "line": line,
                    "rule": "unproven_closed_bar_shift",
                    "function": function,
                    "shift_expression": args[2],
                }
                if allowed_guarded_shift_param(text, args, offset):
                    record["disposition"] = "allowed_guarded_shift_param"
                    allowed.append(record)
                elif allowed_for_loop_shift(text, args, offset):
                    record["disposition"] = "allowed_for_loop_shift"
                    allowed.append(record)
                else:
                    findings.append(record)
        elif function in EXTREME_FUNCTIONS:
            if len(args) < 5:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_extreme_call", "function": function}
                )
            elif is_literal_zero(args[4]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_extreme_window", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[4]):
                record = {
                    "path": str(path),
                    "line": line,
                    "rule": "unproven_closed_bar_shift",
                    "function": function,
                    "shift_expression": args[4],
                }
                if allowed_guarded_shift_param(text, args, offset, arg_index=4):
                    record["disposition"] = "allowed_guarded_shift_param"
                    allowed.append(record)
                elif allowed_for_loop_shift(text, args, offset, arg_index=4):
                    record["disposition"] = "allowed_for_loop_shift"
                    allowed.append(record)
                else:
                    findings.append(record)
        elif function == "iTime" and len(args) >= 3 and is_literal_zero(args[2]):
            # iTime returns only the bar's OPEN TIME. At shift 0 that is the
            # forming bar's open timestamp — clock information, never price —
            # so the read cannot leak lookahead. It is the canonical new-bar
            # edge idiom. Recorded as allowed for transparency.
            record = {"path": str(path), "line": line, "rule": "iTime_zero", "function": function}
            record["disposition"] = (
                "allowed_new_bar_gate"
                if allowed_new_bar_gate(text, offset)
                else "allowed_timestamp_only_read"
            )
            allowed.append(record)
        elif function == "iTime" and len(args) >= 3 and not is_literal_closed_bar_shift(args[2]):
            record = {
                "path": str(path),
                "line": line,
                "rule": "unproven_closed_bar_shift",
                "function": function,
                "shift_expression": args[2],
            }
            if allowed_guarded_shift_param(text, args, offset):
                record["disposition"] = "allowed_guarded_shift_param"
                allowed.append(record)
            elif allowed_for_loop_shift(text, args, offset):
                record["disposition"] = "allowed_for_loop_shift"
                allowed.append(record)
            else:
                findings.append(record)

    direct_series = re.compile(r"\b(?:Open|High|Low|Close|Time|Volume)\s*\[\s*0\s*\]")
    for match in direct_series.finditer(text):
        findings.append(
            {
                "path": str(path),
                "line": line_number(text, match.start()),
                "rule": "direct_bar_zero_array",
                "function": match.group(0),
            }
        )
    return findings, allowed


def resolve_snapshot_files(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    run_dir = manifest_path.parent.resolve()
    snapshot_root = Path(str(manifest.get("snapshot_root") or "")).resolve()
    if not snapshot_root.is_relative_to(run_dir):
        raise ValueError("snapshot_root escapes the run directory")
    refs: list[dict[str, str]] = []
    source_path = Path(str(manifest.get("source_snapshot") or "")).resolve()
    source_hash = str(manifest.get("source_sha256") or "")
    refs.append({"path": str(source_path), "sha256": source_hash})
    include_refs = manifest.get("include_snapshots")
    if not isinstance(include_refs, list):
        raise ValueError("include_snapshots must be a list")
    for item in include_refs:
        if not isinstance(item, dict):
            raise ValueError("include snapshot entry must be an object")
        refs.append(
            {
                "path": str(Path(str(item.get("snapshot_path") or "")).resolve()),
                "sha256": str(item.get("sha256") or ""),
            }
        )
    for ref in refs:
        path = Path(ref["path"])
        if not path.is_file() or not path.is_relative_to(snapshot_root):
            raise ValueError(f"snapshot file is absent or escapes snapshot_root: {path}")
        if not re.fullmatch(r"[A-Fa-f0-9]{64}", ref["sha256"]):
            raise ValueError(f"invalid declared SHA256: {path}")
        actual = sha256_file(path)
        if actual != ref["sha256"].upper():
            raise ValueError(f"snapshot SHA256 mismatch: {path}")
    return refs


def resolve_collection_authority(
    manifest: dict[str, Any], receipt_path: Path | None
) -> bool:
    if receipt_path is None:
        return False
    receipt_path = receipt_path.resolve()
    if not receipt_path.is_file():
        raise ValueError(f"contract receipt is absent: {receipt_path}")
    if sha256_file(receipt_path) != str(manifest.get("contract_receipt_sha256") or "").upper():
        raise ValueError("contract receipt SHA256 does not match run manifest")
    receipt = load_json(receipt_path)
    if receipt.get("schema_version") != "alphafactory_execution_receipt.v1":
        raise ValueError("contract receipt schema is invalid")
    authority = receipt.get("authority")
    if authority not in COLLECTION_AUTHORITIES:
        return False
    binding = receipt.get("binding")
    if not isinstance(binding, dict):
        raise ValueError("collection contract receipt binding is absent")
    for field in (
        "hypothesis_id",
        "ea_name",
        "symbol",
        "period",
        "from",
        "to",
        "model",
        "run_role",
        "execution_mode",
        "fixed_delay_ms",
        "telemetry_profile",
        "telemetry_tier",
        "broker_fingerprint",
        "server_fingerprint",
        "account_fingerprint",
        "data_fingerprint",
        "overrides",
        "required_sidecars",
    ):
        if binding.get(field) != manifest.get(field):
            raise ValueError(f"collection receipt binding {field} does not match manifest")
    mapped_fields = (
        ("symbol_geometry", "contract_symbol_geometry"),
        ("include_closure_sha256", "includes_sha256"),
    )
    for receipt_field, manifest_field in mapped_fields:
        if binding.get(receipt_field) != manifest.get(manifest_field):
            raise ValueError(
                f"collection receipt binding {receipt_field} does not match manifest {manifest_field}"
            )
    if (
        binding.get("run_role") != "control"
        or binding.get("model") != (0 if authority == COLLECTION_AUTHORITY else 4)
        or binding.get("execution_mode") != 0
        or binding.get("fixed_delay_ms") != 0
        or binding.get("telemetry_profile") != "none"
        or binding.get("telemetry_tier") != "off"
        or binding.get("required_sidecars") != []
    ):
        raise ValueError("collection receipt execution mode is not collection-only")
    if manifest.get("telemetry_profile") != "none" or not isinstance(
        manifest.get("data_quality_contract"), dict
    ):
        raise ValueError("collection authority requires telemetry none and a data-quality contract")

    receipt_contract = binding.get("data_quality_contract")
    manifest_contract = manifest["data_quality_contract"]
    if not isinstance(receipt_contract, dict):
        raise ValueError("collection receipt data-quality contract is absent")
    receipt_threshold = receipt_contract.get("history_quality")
    if not isinstance(receipt_threshold, dict):
        raise ValueError("collection receipt History Quality threshold is absent")
    contract_pairs = (
        (receipt_contract.get("coverage_mode"), manifest_contract.get("coverage_mode")),
        (receipt_contract.get("requested_from"), manifest_contract.get("requested_from")),
        (receipt_contract.get("requested_to"), manifest_contract.get("requested_to")),
        (
            receipt_contract.get("require_tester_journal_bounds"),
            manifest_contract.get("require_tester_journal_bounds"),
        ),
        (receipt_threshold.get("value"), manifest_contract.get("history_quality_threshold")),
    )
    if receipt_threshold.get("operator") != "gt" or any(left != right for left, right in contract_pairs):
        raise ValueError("collection receipt data-quality contract does not match manifest")
    try:
        receipt_asof = datetime.fromisoformat(
            str(receipt_contract.get("availability_asof_utc") or "").replace("Z", "+00:00")
        )
        manifest_asof = datetime.fromisoformat(
            str(manifest_contract.get("availability_asof_utc") or "").replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("collection receipt availability timestamp is invalid") from exc
    if receipt_asof != manifest_asof:
        raise ValueError("collection receipt availability timestamp does not match manifest")

    evidence = receipt.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("collection receipt evidence list is absent")
    source_evidence = [item for item in evidence if isinstance(item, dict) and item.get("label") == "source"]
    if len(source_evidence) != 1 or source_evidence[0].get("sha256") != manifest.get("source_sha256"):
        raise ValueError("collection receipt source SHA256 does not match manifest")
    return True


def run(manifest_path: Path, output_path: Path, receipt_path: Path | None = None) -> int:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    refs = resolve_snapshot_files(manifest_path, manifest)
    collection_authorized = resolve_collection_authority(manifest, receipt_path)
    # The frozen first-date provenance probe is mandatory evidence whenever the
    # run binds a data-quality contract: alpha.ps1 requires the
    # DATA_EPOCH_D0_SERIES_PROOF journal line (including the copytime fields)
    # for every governed run, not only collection-only runs. Its legality rests
    # on the exact frozen shape verified by
    # allowed_collection_provenance_copytime (read-only, fixed epoch derived
    # from SERIES_FIRSTDATE, no trade/file functions in scope), so a bound
    # contract authorizes it the same way a verified collection receipt does.
    probe_authorized = collection_authorized or isinstance(
        manifest.get("data_quality_contract"), dict
    )
    findings: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for ref in refs:
        file_findings, file_allowed = audit_file(
            Path(ref["path"]), probe_authorized=probe_authorized
        )
        findings.extend(file_findings)
        allowed.extend(file_allowed)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not findings else "FAIL",
        "hypothesis_id": manifest.get("hypothesis_id"),
        "run_id": manifest.get("run_id"),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "collection_authority_verified": collection_authorized,
        "audited_files": refs,
        "findings": findings,
        "allowed_new_bar_gates": allowed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if payload["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    try:
        output_path = Path(args.out)
        code = run(
            Path(args.manifest),
            output_path,
            Path(args.receipt) if args.receipt else None,
        )
        print(output_path.read_text(encoding="utf-8"), end="")
        return code
    except Exception as exc:
        print(f"NONREPAINT_AUDIT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
