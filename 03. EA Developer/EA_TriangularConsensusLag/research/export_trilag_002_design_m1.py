#!/usr/bin/env python3
"""Outcome-blind DESIGN M1 close exporter for HYP-TRILAG-EURJPY-M1-002.

Importing this module is inert. A real MT5 read requires --production, an
independently reviewed implementation receipt, and an armed sentinel matching
the latest LF-terminated registry row. The frozen payload is exactly
``symbol,time_utc,close`` for 2016-2020; every 2021+ request is rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HYPOTHESIS_ID = "HYP-TRILAG-EURJPY-M1-002"
PARENT_HYPOTHESIS_ID = "HYP-TRILAG-EURJPY-M1-001"
EA_NAME = "EA_TriangularConsensusLag"
ATTEMPT_ID = "TRILAG002-DESIGN-EXPORT-001"

PLAN_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-002_DESIGN_STRUCTURE_PLAN.md"
)
PLAN_SHA256 = "33715BD2CB337C3A700BA08421EE1BD3E92434555E92C85B044FB115412F9200"
PARENT_INVENTORY_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY/"
    "TRILAG001-SOURCE-001/source_inventory.json"
)
PARENT_INVENTORY_SHA256 = (
    "899B874074A3DFAAE477CDD66E135420059FF0D220FED5BB68E25A87ED753541"
)
PARENT_TERMINAL_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    "HYP-TRILAG-EURJPY-M1-001_SOURCE_FEASIBILITY/"
    "TRILAG001-SOURCE-001/attempt_terminal.json"
)
PARENT_TERMINAL_SHA256 = (
    "208E89558566E477EFA350A912EEDD41880DF5F5CD0EA7AD1C60B604AA96263B"
)
EXPORTER_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "export_trilag_002_design_m1.py"
)
EVALUATOR_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "evaluate_trilag_002_design_structure.py"
)
TEST_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/tests/"
    "test_trilag_002_design_structure.py"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-002_DESIGN_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
TERMINAL_REL = "02. AlphaFactory/runtime/mt5-portable-fivepercent/terminal64.exe"
DATASET_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    f"HYP-TRILAG-EURJPY-M1-002/{ATTEMPT_ID}"
)
PARQUET_NAME = "design_m1_close.parquet"
MANIFEST_NAME = "design_m1_manifest.json"
RECEIPT_NAME = "design_export_receipt.json"

SYMBOLS: tuple[str, ...] = ("EURUSD", "USDJPY", "EURJPY")
SCHEMA_COLUMNS: tuple[str, ...] = ("symbol", "time_utc", "close")
DESIGN_START = datetime(2016, 1, 1, tzinfo=timezone.utc)
DESIGN_END = datetime(2020, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
DESIGN_YEARS: tuple[int, ...] = (2016, 2017, 2018, 2019, 2020)
SEALED_VALIDATION_YEARS: tuple[int, ...] = (2021, 2022, 2023, 2024)
EXPECTED_SERVER = "FivePercentOnline-Real"
EXPECTED_COMPANY_FRAGMENT = "Five Percent"
EXPECTED_DIGITS = {"EURUSD": 5, "USDJPY": 3, "EURJPY": 3}
PIP_SIZE = {"EURUSD": 0.0001, "USDJPY": 0.01, "EURJPY": 0.01}
CHUNK_SIZE = 1024 * 1024
HEX = frozenset("0123456789ABCDEF")

# Independent review must replace this exact sentinel before the one real read.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed engineering contract violation; never a market verdict."""


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical or non-finite JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("hash input must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in HEX for c in value)


def normalized_exporter_base_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("exporter payload must be bytes")
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("exporter must contain exactly one valid sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


normalized_base_sha256 = normalized_exporter_base_sha256


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d_side(path: Path, *, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: storage")
    return resolved


def assert_design_request(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or end.tzinfo is None:
        raise ContractError("requested bounds must be timezone-aware UTC")
    if start.astimezone(timezone.utc) != DESIGN_START:
        raise ContractError("design start drift")
    if end.astimezone(timezone.utc) != DESIGN_END:
        raise ContractError("design end drift")
    if end.year >= 2021:
        raise ContractError("2021+ request forbidden")


def epoch_to_utc(epoch: int) -> str:
    observed = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    if observed < DESIGN_START or observed > DESIGN_END or observed.year >= 2021:
        raise ContractError(f"returned bar outside DESIGN:{epoch}")
    return observed.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_symbol_geometry(symbol: str, digits: int, point: float) -> None:
    if symbol not in SYMBOLS:
        raise ContractError(f"unexpected symbol:{symbol}")
    if int(digits) != EXPECTED_DIGITS[symbol]:
        raise ContractError(f"digits mismatch:{symbol}:{digits}")
    expected_point = PIP_SIZE[symbol] / 10.0
    if not math.isclose(float(point), expected_point, rel_tol=0.0, abs_tol=1e-12):
        raise ContractError(f"point mismatch:{symbol}:{point}")


def validate_close_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not rows:
        raise ContractError("no DESIGN M1 close rows")
    per_symbol: dict[str, list[str]] = {symbol: [] for symbol in SYMBOLS}
    seen: set[tuple[str, str]] = set()
    previous: dict[str, str] = {}
    for row in rows:
        if tuple(row.keys()) != SCHEMA_COLUMNS:
            raise ContractError("row schema/order drift")
        symbol = str(row["symbol"])
        if symbol not in SYMBOLS:
            raise ContractError(f"unexpected symbol:{symbol}")
        time_utc = str(row["time_utc"])
        try:
            stamp = datetime.strptime(time_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise ContractError(f"non-canonical UTC timestamp:{time_utc}") from exc
        if stamp < DESIGN_START or stamp > DESIGN_END or stamp.year >= 2021:
            raise ContractError(f"row outside DESIGN:{symbol}:{time_utc}")
        close = float(row["close"])
        if not math.isfinite(close) or close <= 0.0:
            raise ContractError(f"invalid close:{symbol}:{time_utc}")
        key = (symbol, time_utc)
        if key in seen:
            raise ContractError(f"duplicate symbol timestamp:{symbol}:{time_utc}")
        if symbol in previous and time_utc <= previous[symbol]:
            raise ContractError(f"timestamps not strictly increasing:{symbol}")
        seen.add(key)
        previous[symbol] = time_utc
        per_symbol[symbol].append(time_utc)
    if any(not per_symbol[symbol] for symbol in SYMBOLS):
        raise ContractError("one or more required symbols have zero rows")
    return {
        symbol: {
            "rows": len(values),
            "first_time_utc": values[0],
            "last_time_utc": values[-1],
        }
        for symbol, values in per_symbol.items()
    }


def rows_to_dataframe(rows: Sequence[Mapping[str, object]]) -> Any:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - host dependency
        raise ContractError(f"pandas import failed:{exc}") from exc
    frame = pd.DataFrame(list(rows), columns=list(SCHEMA_COLUMNS))
    if tuple(frame.columns) != SCHEMA_COLUMNS:
        raise ContractError("dataframe schema drift")
    frame["symbol"] = frame["symbol"].astype("string")
    frame["time_utc"] = frame["time_utc"].astype("string")
    frame["close"] = frame["close"].astype("float64")
    return frame


def build_manifest(
    *,
    rows: Sequence[Mapping[str, object]],
    parquet_sha256: str,
    terminal_metadata: Mapping[str, object],
) -> dict[str, object]:
    coverage = validate_close_rows(rows)
    return {
        "schema_version": "trilag_002_design_m1_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_hypothesis_id": PARENT_HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "split": "DESIGN",
        "design_years": list(DESIGN_YEARS),
        "sealed_validation_years": list(SEALED_VALIDATION_YEARS),
        "research_holdout_rule": "EVERY_YEAR_2025PLUS_FORBIDDEN",
        "requested_start_utc": DESIGN_START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_end_utc": DESIGN_END.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "symbols": list(SYMBOLS),
        "schema": list(SCHEMA_COLUMNS),
        "row_count": len(rows),
        "per_symbol": coverage,
        "pip_size": dict(PIP_SIZE),
        "bar_contract": "BROKER_BID_COMPLETED_M1_CLOSE",
        "acquisition_api": "MetaTrader5.copy_rates_range(symbol,TIMEFRAME_M1,start,end)",
        "terminal_metadata": dict(terminal_metadata),
        "plan_sha256": PLAN_SHA256,
        "parent_inventory_sha256": PARENT_INVENTORY_SHA256,
        "parent_terminal_sha256": PARENT_TERMINAL_SHA256,
        "parquet_path": f"{DATASET_ROOT_REL}/{PARQUET_NAME}",
        "parquet_sha256": parquet_sha256,
        "outcome_blind_counters": {
            "bars_requested_2021plus": 0,
            "bars_exported_2021plus": 0,
            "post_decision_bars_read": 0,
            "future_path_labels": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "pf_computed": 0,
            "pnl_computed": 0,
            "economics_executed": False,
            "validation_opened": False,
            "research_holdout_opened": False,
            "orders_submitted": 0,
            "network_calls": 0,
            "paid_requests_made": 0,
        },
    }


def _read(path: Path) -> bytes:
    return Path(path).read_bytes()


def atomic_write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise ContractError(f"create-new target already exists:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{os.urandom(6).hex()}")
    try:
        with temp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def atomic_json(path: Path, value: object) -> None:
    atomic_write(path, canonical_json(value) + b"\n")


def publish_dataset(
    *,
    dataset_root: Path,
    rows: Sequence[Mapping[str, object]],
    terminal_metadata: Mapping[str, object],
) -> dict[str, object]:
    root = require_d_side(dataset_root, label="dataset root")
    parquet_path = root / PARQUET_NAME
    manifest_path = root / MANIFEST_NAME
    if root.exists() and any(root.iterdir()):
        raise ContractError("dataset root must be absent or empty")
    root.mkdir(parents=True, exist_ok=True)
    validate_close_rows(rows)
    frame = rows_to_dataframe(rows)
    temp = root / f".{PARQUET_NAME}.tmp-{os.getpid()}-{os.urandom(6).hex()}"
    try:
        frame.to_parquet(temp, index=False)
        if parquet_path.exists():
            raise ContractError("parquet target already exists")
        os.replace(temp, parquet_path)
    finally:
        if temp.exists():
            temp.unlink()
    parquet_sha = sha256_file(parquet_path)
    manifest = build_manifest(
        rows=rows,
        parquet_sha256=parquet_sha,
        terminal_metadata=terminal_metadata,
    )
    atomic_json(manifest_path, manifest)
    return {
        "parquet_path": str(parquet_path),
        "parquet_sha256": parquet_sha,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "row_count": len(rows),
        "manifest": manifest,
    }


def parse_registry(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    rows: list[dict[str, object]] = []
    lines: list[bytes] = []
    for raw in payload.splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("registry contains invalid JSONL") from exc
        if type(row) is not dict:
            raise ContractError("registry row must be an object")
        rows.append(row)
        lines.append(raw + b"\n")
    return rows, lines


def validate_registry_authority(payload: bytes, expected_row_sha: str) -> dict[str, object]:
    rows, lines = parse_registry(payload)
    candidates = [
        (row, line) for row, line in zip(rows, lines)
        if row.get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if not candidates:
        raise ContractError("registry hypothesis missing")
    row, line = candidates[-1]
    if sha256_bytes(line) != expected_row_sha:
        raise ContractError("armed row SHA is not latest hypothesis row")
    validation = row.get("validation")
    metrics = row.get("metrics")
    if type(validation) is not dict or type(metrics) is not dict:
        raise ContractError("registry authority missing validation/metrics")
    if row.get("state") != "probe":
        raise ContractError("design export requires probe state")
    if validation.get("design_export_run_authorized") is not True:
        raise ContractError("design export is not authorized")
    if validation.get("design_structure_evaluation_authorized") is not False:
        raise ContractError("export row must not authorize structural evaluation")
    if validation.get("one_use") is not True:
        raise ContractError("one-use authority missing")
    if int(metrics.get("design_export_attempts_consumed", -1)) != 0:
        raise ContractError("design export attempt already consumed")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt id already present in registry")
    for key in (
        "reviewed_exporter_base_sha256",
        "reviewed_evaluator_base_sha256",
        "reviewed_test_sha256",
        "independent_review_receipt_sha256",
    ):
        if not _valid_sha(validation.get(key)):
            raise ContractError(f"invalid reviewed binding:{key}")
    return row


def _lazy_import_metatrader5() -> Any:
    import importlib

    try:
        return importlib.import_module("MetaTrader5")
    except Exception as exc:  # pragma: no cover - environment dependent
        raise ContractError(f"MetaTrader5 import failed:{exc}") from exc


def initialize_terminal(mt5: Any, terminal_path: Path) -> dict[str, object]:
    terminal = require_d_side(terminal_path, label="terminal")
    if terminal.name.lower() != "terminal64.exe" or not terminal.is_file():
        raise ContractError(f"portable terminal missing:{terminal}")
    if not mt5.initialize(path=str(terminal), timeout=60_000, portable=True):
        raise ContractError(f"mt5 initialize failed:{mt5.last_error()}")
    terminal_info = mt5.terminal_info()
    account = mt5.account_info()
    if terminal_info is None or account is None:
        raise ContractError("terminal/account metadata missing")
    data_path = require_d_side(Path(str(terminal_info.data_path)), label="MT5 data path")
    server = str(account.server)
    company = str(getattr(account, "company", "") or "")
    if server != EXPECTED_SERVER or EXPECTED_COMPANY_FRAGMENT not in company:
        raise ContractError(f"broker identity mismatch:{server}:{company}")
    if bool(getattr(terminal_info, "trade_allowed", False)):
        raise ContractError("refusing terminal with trading enabled")
    for symbol in SYMBOLS:
        if not mt5.symbol_select(symbol, True):
            raise ContractError(f"symbol select failed:{symbol}:{mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        if info is None:
            raise ContractError(f"symbol info missing:{symbol}")
        validate_symbol_geometry(symbol, int(info.digits), float(info.point))
    return {
        "terminal_path": str(terminal),
        "terminal_build": int(terminal_info.build),
        "data_path": str(data_path),
        "portable": True,
        "server": server,
        "company": company,
        "login": int(account.login),
    }


def fetch_design_rows(mt5: Any) -> list[dict[str, object]]:
    assert_design_request(DESIGN_START, DESIGN_END)
    rows: list[dict[str, object]] = []
    for symbol in SYMBOLS:
        rates = mt5.copy_rates_range(
            symbol, mt5.TIMEFRAME_M1, DESIGN_START, DESIGN_END
        )
        if rates is None:
            raise ContractError(f"copy_rates_range failed:{symbol}:{mt5.last_error()}")
        for rate in rates:
            close = float(rate["close"])
            if not math.isfinite(close) or close <= 0.0:
                raise ContractError(f"invalid returned close:{symbol}:{rate['time']}")
            rows.append(
                {
                    "symbol": symbol,
                    "time_utc": epoch_to_utc(int(rate["time"])),
                    "close": close,
                }
            )
    rows.sort(key=lambda row: (str(row["symbol"]), str(row["time_utc"])))
    validate_close_rows(rows)
    return rows


def reserve_dir(path: Path) -> Path:
    target = require_d_side(path, label="evidence root")
    try:
        target.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("exclusive evidence root already exists") from exc
    return target


def run_production(*, workspace_root: Path, production: bool) -> dict[str, object]:
    if production is not True:
        raise ContractError("explicit --production is required")
    if REVIEWED_REGISTRY_ROW_SHA256 is None or not _valid_sha(
        REVIEWED_REGISTRY_ROW_SHA256
    ):
        raise ContractError("reviewed registry-row sentinel is absent or invalid")
    workspace = require_d_side(Path(workspace_root), label="workspace")
    canonical = require_d_side(workspace_from_source(), label="source workspace")
    if os.path.normcase(str(workspace)) != os.path.normcase(str(canonical)):
        raise ContractError("workspace is not the source-bound canonical root")

    row = validate_registry_authority(
        _read(workspace / REGISTRY_REL), REVIEWED_REGISTRY_ROW_SHA256
    )
    validation = row["validation"]
    if sha256_file(workspace / PLAN_REL) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")
    if sha256_file(workspace / PARENT_INVENTORY_REL) != PARENT_INVENTORY_SHA256:
        raise ContractError("parent inventory SHA mismatch")
    if sha256_file(workspace / PARENT_TERMINAL_REL) != PARENT_TERMINAL_SHA256:
        raise ContractError("parent terminal SHA mismatch")
    exporter_sha = normalized_exporter_base_sha256(_read(workspace / EXPORTER_REL))
    evaluator_payload = _read(workspace / EVALUATOR_REL)
    # Evaluator exposes the same normalized helper name without importing MT5.
    evaluator_sha = sha256_bytes(
        re.sub(
            rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$',
            b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
            evaluator_payload,
            count=1,
            flags=re.MULTILINE,
        )
    )
    test_sha = sha256_file(workspace / TEST_REL)
    receipt_sha = sha256_file(workspace / REVIEW_RECEIPT_REL)
    bindings = {
        "reviewed_exporter_base_sha256": exporter_sha,
        "reviewed_evaluator_base_sha256": evaluator_sha,
        "reviewed_test_sha256": test_sha,
        "independent_review_receipt_sha256": receipt_sha,
    }
    for key, actual in bindings.items():
        if validation.get(key) != actual:
            raise ContractError(f"review binding mismatch:{key}")

    evidence_root = reserve_dir(workspace / EVIDENCE_ROOT_REL)
    atomic_json(
        evidence_root / "attempt_started.json",
        {
            "schema_version": "trilag_002_design_export_attempt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
            "status": "STARTED_AUTHORITY_CONSUMED",
            **bindings,
        },
    )
    dataset_root = workspace / DATASET_ROOT_REL
    if dataset_root.exists() and any(dataset_root.iterdir()):
        raise ContractError("dataset root is non-empty")

    mt5 = _lazy_import_metatrader5()
    try:
        terminal_metadata = initialize_terminal(mt5, workspace / TERMINAL_REL)
        rows = fetch_design_rows(mt5)
        published = publish_dataset(
            dataset_root=dataset_root,
            rows=rows,
            terminal_metadata=terminal_metadata,
        )
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    receipt = {
        "schema_version": "trilag_002_design_export_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "DESIGN_EXPORT_COMPLETE_OUTCOME_BLIND",
        "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
        "plan_sha256": PLAN_SHA256,
        **bindings,
        "parquet_sha256": published["parquet_sha256"],
        "manifest_sha256": published["manifest_sha256"],
        "row_count": published["row_count"],
        "per_symbol": published["manifest"]["per_symbol"],
        "requested_start_utc": published["manifest"]["requested_start_utc"],
        "requested_end_utc": published["manifest"]["requested_end_utc"],
        "counters": {
            "design_export_attempts_consumed": 1,
            "mt5_launches": 1,
            "orders_submitted": 0,
            "bars_requested_2021plus": 0,
            "bars_exported_2021plus": 0,
            "post_decision_bars_read": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "outcomes_opened": 0,
            "economics_executed": False,
            "validation_opened": False,
            "research_holdout_opened": False,
            "network_calls": 0,
            "paid_requests_made": 0,
        },
    }
    atomic_json(evidence_root / RECEIPT_NAME, receipt)
    return receipt


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--production", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(
        canonical_json(
            run_production(
                workspace_root=args.workspace_root,
                production=bool(args.production),
            )
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    sys_exit = main()
    raise SystemExit(sys_exit)
