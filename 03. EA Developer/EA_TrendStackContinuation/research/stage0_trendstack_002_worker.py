import datetime
import hashlib
import json
import math
import re
import sys
from pathlib import Path


HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-002"
PLAN_SHA256 = "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
PACKET_SCHEMA = "trendstack_002_decision_packet.v1"
ROW_SCHEMA = "trendstack_002_stage0_worker_row.v1"
PACKET_FIELDS = {
    "schema_version",
    "hypothesis_id",
    "opportunity_id",
    "split",
    "decision_cutoff_utc",
    "m252_direction",
    "m6_direction",
    "alignment",
    "atr20",
    "control_m252_eligible",
    "control_m6_eligible",
    "challenger_stack_eligible",
    "negative_disagree_eligible",
    "exclusion_reason",
    "valid_prior_close_count",
    "max_source_time_utc",
    "source_shard_chain_hashes",
    "source_chain_sha256",
    "extractor_sha256",
    "source_plan_sha256",
    "packet_payload_sha256",
}
SHA256_PATTERN = r"[0-9A-F]{64}\Z"
DATE_PATTERN = r"\d{4}-\d{2}-\d{2}\Z"
UTC_PATTERN = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|\+00:00)?\Z"
WRITE_FLAG_MASK = 1 | 2 | 8 | 256 | 512 | 1024 if sys.platform == "win32" else 1 | 2 | 8 | 64 | 128 | 512 | 1024
_PACKET_OPEN_COUNT = 0


class InvalidEngineering(Exception):
    pass


def _audit_hook(event, args):
    global _PACKET_OPEN_COUNT
    if event == "open":
        target = args[0] if args else None
        mode = args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 else 0
        if str(target) != "packet.json":
            raise PermissionError("worker filesystem access denied")
        if isinstance(mode, str) and any(flag in mode for flag in ("w", "a", "x", "+")):
            raise PermissionError("worker write access denied")
        if isinstance(flags, int) and flags & WRITE_FLAG_MASK:
            raise PermissionError("worker integer write flags denied")
        _PACKET_OPEN_COUNT += 1
        if _PACKET_OPEN_COUNT != 1:
            raise PermissionError("worker packet may be opened exactly once")
    if event in {
        "import",
        "exec",
        "os.chdir",
        "os.fchdir",
        "os.listdir",
        "os.scandir",
        "os.walk",
        "subprocess.Popen",
        "socket.__new__",
        "socket.connect",
        "socket.bind",
    }:
        raise PermissionError("worker capability denied")


sys.addaudithook(_audit_hook)


def _canonical_bytes(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _pretty_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def _sha256(data):
    return hashlib.sha256(data).hexdigest().upper()


def _require(condition, message):
    if not condition:
        raise InvalidEngineering(message)


def _require_sha256(value, label):
    _require(isinstance(value, str) and re.fullmatch(SHA256_PATTERN, value) is not None, f"invalid {label}")


def _parse_utc(value, label):
    _require(isinstance(value, str) and re.fullmatch(UTC_PATTERN, value) is not None, f"invalid {label}")
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)
    except ValueError as exc:
        raise InvalidEngineering(f"invalid {label}") from exc


def _reject_json_constant(value):
    raise InvalidEngineering(f"non-finite JSON constant: {value}")


def _validate_relative_path(value, label):
    _require(isinstance(value, str) and value != "", f"invalid {label}")
    _require("\\" not in value and not value.startswith("/"), f"invalid {label}")
    _require(re.match(r"^[A-Za-z]:", value) is None, f"invalid {label}")
    parts = value.split("/")
    _require(all(part not in ("", ".", "..") for part in parts), f"invalid {label}")


def _validate_packet(packet, raw, expected_file_sha256):
    _require(isinstance(packet, dict), "packet must be a JSON object")
    _require(set(packet) == PACKET_FIELDS, "packet schema fields mismatch")
    _require(packet["schema_version"] == PACKET_SCHEMA, "packet schema version mismatch")
    _require(packet["hypothesis_id"] == HYPOTHESIS_ID, "hypothesis mismatch")
    _require(packet["source_plan_sha256"] == PLAN_SHA256, "frozen plan hash mismatch")
    _require(packet["split"] in ("DESIGN", "VALIDATION_FEATURE_ONLY"), "forbidden split")
    _require_sha256(expected_file_sha256, "expected file sha256")
    _require(_sha256(raw) == expected_file_sha256, "packet file sha256 mismatch")

    payload_sha = packet["packet_payload_sha256"]
    _require_sha256(payload_sha, "packet payload sha256")
    unsigned = {key: value for key, value in packet.items() if key != "packet_payload_sha256"}
    _require(_sha256(_canonical_bytes(unsigned)) == payload_sha, "packet payload sha256 mismatch")
    _require(raw == _pretty_bytes(packet), "packet serialization is not canonical pretty JSON")

    opportunity_value = packet["opportunity_id"]
    _require(
        isinstance(opportunity_value, str) and re.fullmatch(DATE_PATTERN, opportunity_value) is not None,
        "invalid opportunity id",
    )
    try:
        opportunity = datetime.date.fromisoformat(opportunity_value)
    except ValueError as exc:
        raise InvalidEngineering("invalid opportunity id") from exc
    _require(
        datetime.date(2016, 1, 4) <= opportunity < datetime.date(2023, 1, 1),
        "opportunity outside frozen range",
    )
    expected_split = "DESIGN" if opportunity < datetime.date(2021, 1, 1) else "VALIDATION_FEATURE_ONLY"
    _require(packet["split"] == expected_split, "split date mismatch")
    cutoff = _parse_utc(packet["decision_cutoff_utc"], "decision cutoff")
    _require(
        cutoff.date() == opportunity and cutoff.hour == 12 and cutoff.minute == 0 and cutoff.second == 0,
        "decision cutoff must be noon UTC",
    )
    max_source = _parse_utc(packet["max_source_time_utc"], "max source time")
    _require(max_source < cutoff, "source is not causal")
    if max_source.date() == cutoff.date():
        _require(max_source.hour <= 11, "current-day source exceeds 11:00 UTC")
    _require(max_source.date() == opportunity, "source max date mismatch")
    _require(cutoff.year != 2023 and max_source.year != 2023, "forbidden 2023 partition")

    chain = packet["source_shard_chain_hashes"]
    _require(
        isinstance(chain, dict)
        and set(chain) == {"prior_completed_shards_sha256", "current_pre12_sha256"},
        "source chain schema mismatch",
    )
    _require_sha256(chain["prior_completed_shards_sha256"], "prior completed shards sha256")
    _require_sha256(chain["current_pre12_sha256"], "current pre12 sha256")
    _require_sha256(packet["source_chain_sha256"], "source chain sha256")
    _require(
        _sha256(_canonical_bytes(chain)) == packet["source_chain_sha256"],
        "source chain sha256 mismatch",
    )
    _require_sha256(packet["extractor_sha256"], "extractor sha256")

    count = packet["valid_prior_close_count"]
    _require(isinstance(count, int) and not isinstance(count, bool) and count >= 0, "invalid prior close count")
    m252 = packet["m252_direction"]
    m6 = packet["m6_direction"]
    _require(m252 is None or type(m252) is int and m252 in (-1, 0, 1), "invalid M252 direction")
    _require(m6 is None or type(m6) is int and m6 in (-1, 0, 1), "invalid M6 direction")
    if m252 is None:
        _require(count < 253, "missing M252 despite sufficient history")
    else:
        _require(count >= 253, "M252 without sufficient history")
    atr20 = packet["atr20"]
    if atr20 is not None:
        _require(
            isinstance(atr20, (int, float))
            and not isinstance(atr20, bool)
            and math.isfinite(atr20),
            "invalid ATR20",
        )

    feature_complete = m252 in (-1, 1) and m6 in (-1, 0, 1) and atr20 is not None and atr20 > 0
    control_m252 = feature_complete
    control_m6 = feature_complete and m6 in (-1, 1)
    stack = control_m6 and m252 == m6
    disagree = control_m6 and m252 == -m6
    alignment = m252 == m6 if m252 in (-1, 1) and m6 in (-1, 1) else None
    _require(packet["alignment"] is alignment, "alignment truth-table mismatch")
    _require(packet["control_m252_eligible"] is control_m252, "M252_ONLY truth-table mismatch")
    _require(packet["control_m6_eligible"] is control_m6, "M6_ONLY truth-table mismatch")
    _require(packet["challenger_stack_eligible"] is stack, "STACK truth-table mismatch")
    _require(packet["negative_disagree_eligible"] is disagree, "DISAGREE truth-table mismatch")
    exclusion = packet["exclusion_reason"]
    if m252 is None and count < 253:
        expected_exclusion = "INSUFFICIENT_M252_HISTORY"
    elif m252 == 0:
        expected_exclusion = "M252_EQUALITY"
    elif m252 in (-1, 1) and m6 is None:
        expected_exclusion = "MISSING_SIX_HOUR_BAR"
    elif m252 in (-1, 1) and m6 in (-1, 0, 1) and not feature_complete:
        expected_exclusion = "INSUFFICIENT_OR_INVALID_ATR20"
    elif m6 == 0:
        expected_exclusion = "M6_EQUALITY"
    elif disagree:
        expected_exclusion = "M252_M6_DISAGREE"
    elif stack:
        expected_exclusion = None
    else:
        raise InvalidEngineering("unreachable feature projection")
    _require(exclusion == expected_exclusion, "exclusion reason mismatch")
    current_feature_exists = m6 is not None or atr20 is not None and atr20 > 0
    if current_feature_exists:
        _require(
            max_source.hour == 11 and max_source.minute == 0 and max_source.second == 0,
            "current feature source time mismatch",
        )

    return {
        "schema_version": ROW_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "opportunity_id": packet["opportunity_id"],
        "split": packet["split"],
        "packet_payload_sha256": payload_sha,
        "packet_file_sha256": expected_file_sha256,
        "source_chain_sha256": packet["source_chain_sha256"],
        "max_source_time_utc": packet["max_source_time_utc"],
        "feature_complete": feature_complete,
        "control_m252_only_eligible": control_m252,
        "control_m252_only_direction": m252 if control_m252 else None,
        "control_m6_only_eligible": control_m6,
        "control_m6_only_direction": m6 if control_m6 else None,
        "challenger_stack_eligible": stack,
        "challenger_stack_direction": m252 if stack else None,
        "negative_disagree_eligible": disagree,
        "negative_disagree_direction": m6 if disagree else None,
        "exclusion_reason": exclusion,
    }


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    _require(
        len(arguments) == 4
        and arguments[0] == "--packet"
        and arguments[2] == "--expected-sha256",
        "invalid worker arguments",
    )
    packet_argument = arguments[1]
    expected_sha256 = arguments[3]
    _require(packet_argument == "packet.json", "only literal packet.json is permitted")
    packet_path = Path(packet_argument)
    _require(not packet_path.is_symlink(), "staged packet must not be a symlink")
    _require(packet_path.is_file(), "staged packet is missing")
    raw = packet_path.read_bytes()
    _require(_PACKET_OPEN_COUNT == 1, "worker packet open count mismatch")
    try:
        packet = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidEngineering("invalid packet JSON") from exc
    row = _validate_packet(packet, raw, expected_sha256)
    sys.stdout.buffer.write(_canonical_bytes(row) + b"\n")
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InvalidEngineering as exc:
        print(f"INVALID_ENGINEERING: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:
        print(f"INVALID_ENGINEERING: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
