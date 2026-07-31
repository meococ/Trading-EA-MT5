from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "acquire_trendstack_002_design_m1.py"
CLOCK_PATH = ROOT.parents[1] / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
DSR_PATH = ROOT.parents[1] / "02. AlphaFactory" / "tools" / "research" / "dsr.py"
STAGE0_LEDGER_PATH = ROOT / "research" / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_eligibility_ledger.jsonl"


def load_tool():
    spec = importlib.util.spec_from_file_location("acquire_trendstack_002_design_m1", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def load_clock():
    spec = importlib.util.spec_from_file_location("test_fivepercent_server_clock", CLOCK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def server_wall_for_utc(value: datetime) -> datetime:
    clock = load_clock()
    naive = value.replace(tzinfo=None)
    matches = []
    for offset in (2, 3):
        server = naive + timedelta(hours=offset)
        if clock.server_to_utc(server) == naive:
            matches.append(server)
    assert len(matches) == 1
    return matches[0]


def request_row(day: str = "2016-01-04", sequence: int = 1, clock_module=None) -> dict[str, object]:
    start = datetime.fromisoformat(day).replace(hour=12, minute=1, tzinfo=timezone.utc)
    end = datetime.fromisoformat(day).replace(hour=18, tzinfo=timezone.utc)
    if clock_module is None:
        start_server = server_wall_for_utc(start)
        end_server = server_wall_for_utc(end)
    else:
        def convert(value: datetime) -> datetime:
            naive = value.replace(tzinfo=None)
            matches = [naive + timedelta(hours=offset) for offset in (2, 3) if clock_module.server_to_utc(naive + timedelta(hours=offset)) == naive]
            assert len(matches) == 1
            return matches[0]

        start_server = convert(start)
        end_server = convert(end)
    return {
        "schema_version": "trendstack_002_design_m1_request.v1",
        "hypothesis_id": "HYP-TRENDSTACK-EURUSD-H1-002",
        "request_id": f"M1-DESIGN-{sequence:04d}-{day.replace('-', '')}",
        "sequence": sequence,
        "split": "DESIGN",
        "opportunity_id": day,
        "canonical_from_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "canonical_to_inclusive_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "api_server_wall_from_encoded_as_utc": start_server.replace(tzinfo=timezone.utc).isoformat(),
        "api_server_wall_to_encoded_as_utc": end_server.replace(tzinfo=timezone.utc).isoformat(),
        "from_clock_roundtrip_status": "PASS",
        "to_clock_roundtrip_status": "PASS",
        "expected_rows": 360,
        "source_plan_sha256": "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF",
        "design_plan_sha256": "06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9",
    }


def accepted_dates() -> list[str]:
    return [
        row["opportunity_id"]
        for row in (json.loads(line) for line in STAGE0_LEDGER_PATH.read_text(encoding="utf-8").splitlines())
        if row["split"] == "DESIGN"
    ]


def wrong_interior_dates() -> list[str]:
    accepted = accepted_dates()
    accepted_set = set(accepted)
    cursor = date(2016, 1, 4)
    absent = []
    while cursor <= date(2020, 12, 31):
        value = cursor.isoformat()
        if value not in accepted_set and value not in {accepted[0], accepted[-1]}:
            absent.append(value)
        cursor += timedelta(days=1)
    wrong = sorted((accepted_set - set(accepted[1:375])) | set(absent[:374]))
    assert len(wrong) == 1297 and len(set(wrong) - accepted_set) == 374
    return wrong


def request_rows_for_dates(dates: list[str]) -> list[dict[str, object]]:
    clock = load_clock()
    rows = []
    for sequence, day in enumerate(dates, start=1):
        rows.append(request_row(day, sequence, clock_module=clock))
    return rows


def write_plan(path: Path, rows: list[dict[str, object]]) -> str:
    payload = b"".join(canonical(row) + b"\n" for row in rows)
    path.write_bytes(payload)
    return sha256(payload)


def valid_rates(day: str = "2016-01-04") -> list[dict[str, object]]:
    start = datetime.fromisoformat(day).replace(hour=12, minute=1, tzinfo=timezone.utc)
    rows = []
    for index in range(360):
        utc = start + timedelta(minutes=index)
        server = server_wall_for_utc(utc)
        price = 1.10000 + index * 0.000001
        rows.append(
            {
                "time": int(server.replace(tzinfo=timezone.utc).timestamp()),
                "open": price,
                "high": price + 0.00010,
                "low": price - 0.00010,
                "close": price + 0.00001,
                "tick_volume": 10 + index,
                "spread": 12,
                "real_volume": 0,
            }
        )
    return rows


class FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TIMEFRAME_M1 = 1
    __version__ = "5.test"

    def __init__(self, native_path: Path, rates: list[dict[str, object]], *, shutdown_error: bool = False):
        self._core = SimpleNamespace(__file__=str(native_path))
        self.rates = rates
        self.shutdown_error = shutdown_error
        self.calls = []
        self.shutdown_called = False

    def initialize(self, **kwargs):
        self.initialize_kwargs = kwargs
        return True

    def last_error(self):
        return (0, "ok")

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=False, connected=True, build=9999)

    def account_info(self):
        return SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd")

    def symbol_info(self, symbol):
        assert symbol == "EURUSD"
        return SimpleNamespace(digits=5, point=0.00001, select=True, visible=True)

    def copy_rates_range(self, *args):
        self.calls.append(args)
        return self.rates

    def shutdown(self):
        self.shutdown_called = True
        if self.shutdown_error:
            raise RuntimeError("shutdown failed")


def configure_single_request(tool, monkeypatch) -> None:
    monkeypatch.setattr(tool, "EXPECTED_REQUEST_COUNT", 1)
    monkeypatch.setattr(tool, "EXPECTED_TOTAL_ROWS", 360)
    monkeypatch.setattr(tool, "EXPECTED_FIRST_DATE", "2016-01-04")
    monkeypatch.setattr(tool, "EXPECTED_LAST_DATE", "2016-01-04")
    monkeypatch.setattr(tool, "REQUIRED_DATA_DRIVE", None)


def valid_run_packet(tool, output_root: Path, **overrides) -> dict[str, object]:
    packet = {
        "schema_version": "trendstack_002_design_run_packet.v1",
        "hypothesis_id": tool.HYPOTHESIS_ID,
        "verdict": "FROZEN_DESIGN_M1_PROXY_ONE_RUN_AUTHORIZED",
        "source_plan_sha256": tool.SOURCE_PLAN_SHA256,
        "design_plan_sha256": tool.DESIGN_PLAN_SHA256,
        "design_plan_v2_path": tool.DESIGN_PLAN_V2_RELATIVE_PATH,
        "design_plan_v2_sha256": tool.DESIGN_PLAN_V2_SHA256,
        "design_date_set_sha256": tool.DESIGN_DATE_SET_SHA256,
        "stage0_eligibility_ledger_sha256": tool.STAGE0_LEDGER_SHA256,
        "stage0_receipt_sha256": tool.STAGE0_RECEIPT_SHA256,
        "stage0_access_trace_sha256": tool.STAGE0_ACCESS_TRACE_SHA256,
        "stage0_reconciliation_sha256": tool.STAGE0_RECONCILIATION_SHA256,
        "decision_packet_manifest_sha256": tool.PACKET_MANIFEST_SHA256,
        "decision_packet_receipt_sha256": tool.PACKET_RECEIPT_SHA256,
        "decision_packet_set_sha256": tool.PACKET_SET_SHA256,
        "request_plan_sha256": "1" * 64,
        "request_plan_receipt_sha256": "2" * 64,
        "request_count": 1297,
        "expected_m1_rows": 466_920,
        "first_design_date": "2016-01-04",
        "last_design_date": "2020-12-31",
        "request_plan_builder_sha256": "3" * 64,
        "acquisition_tool_sha256": sha256(TOOL_PATH.read_bytes()),
        "evaluator_tool_sha256": "4" * 64,
        "clock_tool_sha256": sha256(CLOCK_PATH.read_bytes()),
        "dsr_tool_sha256": tool.DSR_SHA256,
        "design_m1_output_root": str(output_root.resolve()),
        "design_m1_authorized": True,
        "validation_m1_authorized": False,
        "holdout_authorized": False,
        "model0_authorized": False,
        "promotion_authorized": False,
    }
    packet.update(overrides)
    return packet


def write_run_packet(tool, path: Path, packet: dict[str, object], *, canonical_bytes: bool = True) -> str:
    payload = canonical(packet) + b"\n"
    if not canonical_bytes:
        payload = json.dumps(packet, indent=2).encode("utf-8") + b"\n"
    path.write_bytes(payload)
    return sha256(payload)


def configure_authorization_bypass(tool, monkeypatch, tmp_path: Path, output: Path, plan_sha: str) -> dict[str, object]:
    packet = valid_run_packet(
        tool,
        output,
        request_plan_sha256=plan_sha,
        request_count=tool.EXPECTED_REQUEST_COUNT,
        expected_m1_rows=tool.EXPECTED_TOTAL_ROWS,
        first_design_date=tool.EXPECTED_FIRST_DATE,
        last_design_date=tool.EXPECTED_LAST_DATE,
    )
    run_packet = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    request_receipt = output / "design_request_plan_receipt.json"
    run_packet.write_bytes(canonical(packet) + b"\n")
    request_receipt.write_bytes(b"{}\n")
    monkeypatch.setattr(tool, "read_run_packet", lambda _: (packet, "A" * 64))
    monkeypatch.setattr(tool, "_verify_authority_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "read_request_receipt", lambda *args, **kwargs: {})
    return {
        "request_receipt_path": request_receipt,
        "run_packet_path": run_packet,
        "dsr_path": DSR_PATH,
        "authority_paths": {},
    }


def make_authority_files(tool, tmp_path: Path, packet: dict[str, object]) -> dict[str, Path]:
    root = tmp_path / "authority"
    root.mkdir()
    paths = {}
    for name, packet_field in tool.AUTHORITY_PATH_FIELDS.items():
        path = root / f"{name}.bin"
        payload = f"authority:{name}\n".encode("ascii")
        path.write_bytes(payload)
        packet[packet_field] = sha256(payload)
        paths[name] = path
    return paths


def test_acquisition_pins_plans_and_requires_d_drive_by_default() -> None:
    tool = load_tool()
    assert tool.DESIGN_PLAN_SHA256 == "06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9"
    assert tool.SOURCE_PLAN_SHA256 == "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
    assert tool.REQUIRED_DATA_DRIVE == "D:"
    source = TOOL_PATH.read_text(encoding="utf-8")
    assert "copy_rates_range" in source
    assert "portable=True" in source
    assert "shutdown" in source


def test_canonical_run_packet_is_mandatory_strict_and_cannot_use_caller_expected_hash_authority(tmp_path: Path) -> None:
    tool = load_tool()
    signature = inspect.signature(tool.acquire_design_m1)
    assert "run_packet_path" in signature.parameters
    assert "expected_request_plan_sha256" not in signature.parameters
    output = tmp_path / "data"
    packet = valid_run_packet(tool, output)
    packet_path = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    expected_sha = write_run_packet(tool, packet_path, packet)
    parsed, observed_sha = tool.read_run_packet(packet_path)
    assert parsed == packet
    assert observed_sha == expected_sha

    for mutation in (
        {**packet, "verdict": "UNAUTHORIZED"},
        {**packet, "extra": "forbidden"},
        {key: value for key, value in packet.items() if key != "design_m1_authorized"},
        {**packet, "design_m1_authorized": 1},
    ):
        path = tmp_path / f"case-{len(list(tmp_path.iterdir()))}.json"
        write_run_packet(tool, path, mutation)
        with pytest.raises(tool.InvalidEngineering):
            tool.read_run_packet(path)

    noncanonical = tmp_path / "noncanonical.json"
    write_run_packet(tool, noncanonical, packet, canonical_bytes=False)
    with pytest.raises(tool.InvalidEngineering, match="canonical"):
        tool.read_run_packet(noncanonical)


@pytest.mark.parametrize(
    ("terminal", "account", "symbol"),
    [
        (SimpleNamespace(trade_allowed=0, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=1, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=False, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server=123, company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=True, point=0.00001, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=True, select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=float("nan"), select=True, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=1, visible=True)),
        (SimpleNamespace(trade_allowed=False, connected=True, build=1), SimpleNamespace(trade_mode=0, server="FivePercentOnline-Real", company="Five Percent Online Ltd"), SimpleNamespace(digits=5, point=0.00001, select=True, visible=False)),
    ],
)
def test_runtime_guards_reject_all_bool_numeric_and_missing_visibility_coercions(terminal, account, symbol) -> None:
    tool = load_tool()
    with pytest.raises(tool.InvalidEngineering):
        tool.validate_runtime_guards(SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0), terminal, account, symbol)


def test_fake_self_hash_run_packet_never_reaches_initialize(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    monkeypatch.setattr(tool, "REQUIRED_DATA_DRIVE", None)
    output = tmp_path / "data"
    output.mkdir()
    packet = valid_run_packet(tool, output)
    authority_paths = make_authority_files(tool, tmp_path, packet)
    packet["acquisition_tool_sha256"] = "0" * 64
    run_packet = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    request_receipt = output / "design_request_plan_receipt.json"
    request_plan = output / "design_request_plan.jsonl"
    run_packet.write_bytes(canonical(packet) + b"\n")
    request_receipt.write_bytes(b"{}\n")
    request_plan.write_bytes(b"{}\n")
    monkeypatch.setattr(tool, "read_run_packet", lambda _: (packet, sha256(run_packet.read_bytes())))
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    fake = FakeMt5(native, valid_rates())
    with pytest.raises(tool.InvalidEngineering, match="self-hash"):
        tool.acquire_design_m1(
            request_plan,
            request_receipt,
            run_packet,
            terminal_path=terminal,
            output_root=output,
            mt5_api=fake,
            clock_path=CLOCK_PATH,
            dsr_path=DSR_PATH,
            authority_paths=authority_paths,
        )
    assert not hasattr(fake, "initialize_kwargs")


def test_self_hashed_interior_validation_date_plan_never_reaches_initialize(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    configure_single_request(tool, monkeypatch)
    output = tmp_path / "data"
    output.mkdir()
    validation_row = request_row("2021-01-04")
    request_plan = output / "design_request_plan.jsonl"
    plan_sha = write_plan(request_plan, [validation_row])
    packet = valid_run_packet(
        tool,
        output,
        request_plan_sha256=plan_sha,
        request_count=1,
        expected_m1_rows=360,
        first_design_date="2021-01-04",
        last_design_date="2021-01-04",
    )
    authority_paths = make_authority_files(tool, tmp_path, packet)
    packet["acquisition_tool_sha256"] = sha256(TOOL_PATH.read_bytes())
    run_packet = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    request_receipt = output / "design_request_plan_receipt.json"
    run_packet.write_bytes(canonical(packet) + b"\n")
    request_receipt.write_bytes(b"{}\n")
    monkeypatch.setattr(tool, "read_run_packet", lambda _: (packet, sha256(run_packet.read_bytes())))
    monkeypatch.setattr(tool, "read_request_receipt", lambda *args: {})
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    fake = FakeMt5(native, valid_rates())
    with pytest.raises(tool.InvalidEngineering, match="validation/holdout"):
        tool.acquire_design_m1(
            request_plan,
            request_receipt,
            run_packet,
            terminal_path=terminal,
            output_root=output,
            mt5_api=fake,
            clock_path=CLOCK_PATH,
            dsr_path=DSR_PATH,
            authority_paths=authority_paths,
        )
    assert not hasattr(fake, "initialize_kwargs")


def test_self_consistent_wrong_374_date_interior_set_never_reaches_initialize(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    monkeypatch.setattr(tool, "REQUIRED_DATA_DRIVE", None)
    output = tmp_path / "data"
    output.mkdir()
    wrong_rows = request_rows_for_dates(wrong_interior_dates())
    request_plan = output / "design_request_plan.jsonl"
    plan_sha = write_plan(request_plan, wrong_rows)
    packet = valid_run_packet(tool, output, request_plan_sha256=plan_sha)
    authority_paths = make_authority_files(tool, tmp_path, packet)
    packet["acquisition_tool_sha256"] = sha256(TOOL_PATH.read_bytes())
    run_packet = tmp_path / "HYP-TRENDSTACK-EURUSD-H1-002_DESIGN_RUN_PACKET.json"
    request_receipt = output / "design_request_plan_receipt.json"
    run_packet.write_bytes(canonical(packet) + b"\n")
    request_receipt.write_bytes(b"{}\n")
    monkeypatch.setattr(tool, "read_run_packet", lambda _: (packet, sha256(run_packet.read_bytes())))
    monkeypatch.setattr(tool, "read_request_receipt", lambda *args: {})
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    fake = FakeMt5(native, valid_rates())
    with pytest.raises(tool.InvalidEngineering, match="date-set"):
        tool.acquire_design_m1(
            request_plan,
            request_receipt,
            run_packet,
            terminal_path=terminal,
            output_root=output,
            mt5_api=fake,
            clock_path=CLOCK_PATH,
            dsr_path=DSR_PATH,
            authority_paths=authority_paths,
        )
    assert not hasattr(fake, "initialize_kwargs")


def test_one_exact_call_writes_one_row_group_manifest_and_false_outcome_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    tool = load_tool()
    configure_single_request(tool, monkeypatch)
    output = tmp_path / "data"
    output.mkdir()
    plan = output / "design_request_plan.jsonl"
    plan_sha = write_plan(plan, [request_row()])
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    fake = FakeMt5(native, valid_rates())
    authorization = configure_authorization_bypass(tool, monkeypatch, tmp_path, output, plan_sha)
    receipt = tool.acquire_design_m1(
        plan,
        **authorization,
        terminal_path=terminal,
        output_root=output,
        mt5_api=fake,
        clock_path=CLOCK_PATH,
    )
    assert fake.initialize_kwargs == {"path": str(terminal), "portable": True, "timeout": 60_000}
    assert len(fake.calls) == 1
    assert fake.shutdown_called is True
    shard = output / "raw_m1" / "DESIGN" / "2016-01-04" / "1201_1800.parquet"
    parquet = pq.ParquetFile(shard)
    assert parquet.metadata.num_rows == 360
    assert parquet.metadata.num_row_groups == 1
    assert receipt["design_m1_opened"] is True
    assert receipt["validation_m1_opened"] is False
    assert receipt["holdout_opened"] is False
    assert receipt["economics_computed"] is False
    assert receipt["physical_partition_status"] == "PASS"
    assert receipt["request_plan_sha256"] == plan_sha
    assert receipt["run_packet_sha256"] == "A" * 64


@pytest.mark.parametrize("defect", ["missing", "duplicate", "outside", "geometry"])
def test_invalid_grid_or_geometry_quarantines_attempt_and_always_shuts_down(
    tmp_path: Path, monkeypatch, defect: str
) -> None:
    tool = load_tool()
    configure_single_request(tool, monkeypatch)
    output = tmp_path / "data"
    output.mkdir()
    plan = output / "design_request_plan.jsonl"
    plan_sha = write_plan(plan, [request_row()])
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    rates = valid_rates()
    if defect == "missing":
        rates.pop(10)
    elif defect == "duplicate":
        rates[10] = dict(rates[9])
    elif defect == "outside":
        rates[-1]["time"] += 60
    else:
        rates[10]["high"] = rates[10]["low"] - 0.1
    fake = FakeMt5(native, rates)
    authorization = configure_authorization_bypass(tool, monkeypatch, tmp_path, output, plan_sha)
    with pytest.raises(tool.InvalidEngineering):
        tool.acquire_design_m1(
            plan,
            **authorization,
            terminal_path=terminal,
            output_root=output,
            mt5_api=fake,
            clock_path=CLOCK_PATH,
        )
    assert fake.shutdown_called is True
    assert not (output / "design_m1_source_receipt.json").exists()
    quarantine = output / "quarantine"
    assert quarantine.is_dir()
    assert any((child / "failure_manifest.json").is_file() for child in quarantine.iterdir())


def test_shutdown_failure_invalidates_and_never_publishes_receipt(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    configure_single_request(tool, monkeypatch)
    output = tmp_path / "data"
    output.mkdir()
    plan = output / "design_request_plan.jsonl"
    plan_sha = write_plan(plan, [request_row()])
    terminal = tmp_path / "terminal64.exe"
    native = tmp_path / "_core.pyd"
    terminal.write_bytes(b"terminal")
    native.write_bytes(b"native")
    fake = FakeMt5(native, valid_rates(), shutdown_error=True)
    authorization = configure_authorization_bypass(tool, monkeypatch, tmp_path, output, plan_sha)
    with pytest.raises(tool.InvalidEngineering, match="shutdown"):
        tool.acquire_design_m1(
            plan,
            **authorization,
            terminal_path=terminal,
            output_root=output,
            mt5_api=fake,
            clock_path=CLOCK_PATH,
        )
    assert fake.shutdown_called is True
    assert not (output / "design_m1_source_receipt.json").exists()


@pytest.mark.parametrize(
    ("terminal_trade_allowed", "trade_mode", "server", "company", "digits", "point"),
    [
        (True, 0, "FivePercentOnline-Real", "Five Percent Online Ltd", 5, 0.00001),
        (False, 1, "FivePercentOnline-Real", "Five Percent Online Ltd", 5, 0.00001),
        (False, 0, "Wrong", "Five Percent Online Ltd", 5, 0.00001),
        (False, 0, "FivePercentOnline-Real", "Wrong", 5, 0.00001),
        (False, 0, "FivePercentOnline-Real", "Five Percent Online Ltd", 4, 0.0001),
    ],
)
def test_runtime_guards_fail_closed(
    terminal_trade_allowed, trade_mode, server, company, digits, point
) -> None:
    tool = load_tool()
    fake = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0)
    terminal = SimpleNamespace(trade_allowed=terminal_trade_allowed, build=1)
    account = SimpleNamespace(trade_mode=trade_mode, server=server, company=company)
    symbol = SimpleNamespace(digits=digits, point=point)
    with pytest.raises(tool.InvalidEngineering):
        tool.validate_runtime_guards(fake, terminal, account, symbol)


def test_request_plan_rejects_validation_holdout_hardlink_and_hash_drift(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    configure_single_request(tool, monkeypatch)
    plan = tmp_path / "design_request_plan.jsonl"
    row = request_row("2016-01-04")
    row["split"] = "VALIDATION"
    plan_sha = write_plan(plan, [row])
    with pytest.raises(tool.InvalidEngineering):
        tool.read_request_plan(plan, plan_sha, CLOCK_PATH)
    with pytest.raises(tool.InvalidEngineering):
        tool.read_request_plan(plan, "0" * 64, CLOCK_PATH)

    good = tmp_path / "good.jsonl"
    good_sha = write_plan(good, [request_row()])
    hardlink = tmp_path / "hardlink.jsonl"
    os.link(good, hardlink)
    with pytest.raises(tool.InvalidEngineering):
        tool.read_request_plan(good, good_sha, CLOCK_PATH)
