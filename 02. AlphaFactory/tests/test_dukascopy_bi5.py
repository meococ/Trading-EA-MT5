from __future__ import annotations

import hashlib
import importlib.util
import json
import lzma
import struct
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "research" / "dukascopy_bi5.py"
)
SPEC = importlib.util.spec_from_file_location("dukascopy_bi5", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
duka = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = duka
SPEC.loader.exec_module(duka)


def compressed(*records: tuple[int, int, int, float, float]) -> bytes:
    raw = b"".join(struct.pack(">3I2f", *record) for record in records)
    return lzma.compress(raw)


def test_host_rate_limiter_serializes_and_shares_penalty() -> None:
    now = [0.0]
    sleeps: list[float] = []

    def clock() -> float:
        return now[0]

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        now[0] += seconds

    limiter = duka.HostRateLimiter(0.25, clock=clock, sleeper=sleeper)
    limiter.wait()
    limiter.wait()
    assert sleeps == pytest.approx([0.25])
    limiter.penalize(3.0)
    limiter.wait()
    assert sleeps[-1] == pytest.approx(3.0)


def test_chunk_url_uses_zero_based_month() -> None:
    hour = datetime(2018, 1, 8, 14, tzinfo=timezone.utc)
    assert duka.chunk_url("EURUSD", hour).endswith(
        "/EURUSD/2018/00/08/14h_ticks.bi5"
    )


def test_decode_bid_ask_scale_and_timestamp() -> None:
    hour = datetime(2025, 1, 15, 14, tzinfo=timezone.utc)
    payload = compressed(
        (65, 112_348, 112_345, 2.5, 3.5),
        (66, 112_349, 112_346, 4.5, 5.5),
    )
    result = duka.decode_bi5(payload, symbol="EURUSD", hour_start=hour)
    assert result.count == 2
    assert result.ticks[0].time_msc == int(hour.timestamp()) * 1000 + 65
    assert result.ticks[0].bid == pytest.approx(1.12345)
    assert result.ticks[0].ask == pytest.approx(1.12348)
    assert result.ticks[0].bid_volume_raw == pytest.approx(3.5)
    assert result.ticks[0].ask_volume_raw == pytest.approx(2.5)


@pytest.mark.parametrize(
    "records, message",
    [
        (((2, 112_348, 112_345, 1.0, 1.0), (1, 112_348, 112_345, 1.0, 1.0)), "regressed"),
        (((1, 112_345, 112_348, 1.0, 1.0),), "crossed quote"),
        (((3_600_000, 112_348, 112_345, 1.0, 1.0),), "outside hour"),
    ],
)
def test_decode_rejects_invalid_stream(records, message: str) -> None:
    hour = datetime(2025, 1, 15, 14, tzinfo=timezone.utc)
    with pytest.raises(duka.Bi5ValidationError, match=message):
        duka.decode_bi5(compressed(*records), symbol="EURUSD", hour_start=hour)


def test_daily_binary_is_hash_bound(tmp_path: Path) -> None:
    ticks = (
        duka.Tick(1_515_427_200_001, 1.20, 1.2001, 0.0, 0.0),
        duka.Tick(1_515_427_200_002, 1.21, 1.2101, 0.0, 0.0),
    )
    path = tmp_path / "day.afdticks"
    receipt = duka.write_day_binary(path, ticks)
    payload = path.read_bytes()
    magic, count = struct.unpack_from("<QQ", payload)
    assert magic == duka.AFD_MAGIC
    assert count == 2
    assert receipt["sha256"] == hashlib.sha256(payload).hexdigest().upper()
    assert len(payload) == 16 + 2 * 24


def test_acquire_day_writes_receipt_and_resumes(tmp_path: Path) -> None:
    source_day = date(2018, 1, 8)
    payload = compressed((1, 112_348, 112_345, 1.0, 1.0))
    calls: list[str] = []

    def fake_fetch(url: str, *, timeout: int):
        calls.append(url)
        if url.endswith("14h_ticks.bi5"):
            return 200, payload, {"etag": "pilot"}
        return 404, b"", {}

    contract = tmp_path / "contract.json"
    contract.write_text("{}\n", encoding="utf-8")
    contract_sha = hashlib.sha256(contract.read_bytes()).hexdigest().upper()
    first = duka.acquire_day(
        symbol="EURUSD",
        source_day=source_day,
        root=tmp_path / "data",
        timeout=1,
        retries=0,
        workers=4,
        contract_path=contract,
        contract_sha256=contract_sha,
        fetcher=fake_fetch,
    )
    assert first["status"] == "PASS"
    assert first["tick_count"] == 1
    assert first["empty_hour_count"] == 23
    assert len(calls) == 24

    calls.clear()
    second = duka.acquire_day(
        symbol="EURUSD",
        source_day=source_day,
        root=tmp_path / "data",
        timeout=1,
        retries=0,
        workers=4,
        contract_path=contract,
        contract_sha256=contract_sha,
        fetcher=fake_fetch,
    )
    assert second["acquisition"] == "VERIFIED_EXISTING_DAY"
    assert calls == []


def test_resume_fails_closed_after_binary_tamper(tmp_path: Path) -> None:
    source_day = date(2018, 1, 8)
    payload = compressed((1, 112_348, 112_345, 1.0, 1.0))

    def fake_fetch(url: str, *, timeout: int):
        return (200, payload, {}) if url.endswith("14h_ticks.bi5") else (404, b"", {})

    contract = tmp_path / "contract.json"
    contract.write_text("{}\n", encoding="utf-8")
    contract_sha = hashlib.sha256(contract.read_bytes()).hexdigest().upper()
    kwargs = dict(
        symbol="EURUSD",
        source_day=source_day,
        root=tmp_path / "data",
        timeout=1,
        retries=0,
        workers=4,
        contract_path=contract,
        contract_sha256=contract_sha,
        fetcher=fake_fetch,
    )
    receipt = duka.acquire_day(**kwargs)
    Path(receipt["binary"]["path"]).write_bytes(b"tampered")
    with pytest.raises(duka.Bi5ValidationError, match="binding mismatch"):
        duka.acquire_day(**kwargs)


def test_partial_hour_resume_uses_raw_and_empty_markers(tmp_path: Path) -> None:
    source_day = date(2018, 1, 8)
    root = tmp_path / "data"
    raw_root, _, _ = duka._day_paths(root, "EURUSD", source_day)
    raw_root.mkdir(parents=True)
    payload = compressed((1, 112_348, 112_345, 1.0, 1.0))
    (raw_root / "14h_ticks.bi5").write_bytes(payload)
    for hour in range(24):
        if hour == 14:
            continue
        hour_start = datetime(
            source_day.year, source_day.month, source_day.day, hour, tzinfo=timezone.utc
        )
        url = duka.chunk_url("EURUSD", hour_start)
        duka.write_json_atomic(
            raw_root / f"{hour:02d}h_ticks.empty.json",
            {"url": url, "status": "EMPTY_HOUR", "http_status": 404, "headers": {}},
        )

    def forbidden_fetch(url: str, *, timeout: int):
        raise AssertionError(f"network fetch was not expected: {url}")

    contract = tmp_path / "contract.json"
    contract.write_text("{}\n", encoding="utf-8")
    contract_sha = hashlib.sha256(contract.read_bytes()).hexdigest().upper()
    receipt = duka.acquire_day(
        symbol="EURUSD",
        source_day=source_day,
        root=root,
        timeout=1,
        retries=0,
        workers=4,
        contract_path=contract,
        contract_sha256=contract_sha,
        fetcher=forbidden_fetch,
    )
    assert receipt["tick_count"] == 1
    assert receipt["empty_hour_count"] == 23
    assert receipt["hours"][14]["acquisition"] == "VERIFIED_EXISTING_HOUR"


def test_contract_loader_rejects_hash_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    path.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")
    with pytest.raises(duka.Bi5ValidationError, match="SHA256 mismatch"):
        duka._contract(path, "0" * 64)
