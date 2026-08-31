"""Immutable, content-addressed artifacts and an append-only audit ledger.

This module deliberately owns no trading side effects.  Its only mutations are
durable evidence writes below an explicitly supplied artifact root.
"""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from typing import Any, Iterator, Mapping

from pydantic import BaseModel

from .models import ArtifactRef, SessionPlan


_ZERO_HASH = "0" * 64


class ArtifactError(RuntimeError):
    """Base error for immutable artifact storage."""


class ArtifactExistsError(ArtifactError):
    """Raised when a write would replace an existing artifact."""


class ArtifactIntegrityError(ArtifactError):
    """Raised when content does not match its declared identity or chain."""


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    """Encode JSON identically across runs, without insignificant whitespace."""

    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    """Best-effort directory fsync (unsupported by normal Windows handles)."""

    try:
        descriptor = os.open(path, os.O_RDONLY)
    except (AttributeError, OSError):
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


@contextmanager
def _exclusive_file_lock(path: Path, timeout_seconds: float = 10.0) -> Iterator[None]:
    """Hold a one-byte advisory lock, using native Windows/POSIX primitives."""

    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open("a+b")
    deadline = time.monotonic() + timeout_seconds
    locked = False
    try:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())

        if os.name == "nt":
            import msvcrt

            while not locked:
                try:
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out acquiring artifact lock: {path}")
                    time.sleep(0.02)
        else:
            import fcntl

            while not locked:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"timed out acquiring artifact lock: {path}")
                    time.sleep(0.02)
        yield
    finally:
        if locked:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


class ArtifactStore:
    """A root-confined store that can create, but can never replace, evidence."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.root / ".artifact-store.lock"

    def _resolve_relative(self, relative_path: str | Path) -> tuple[Path, Path]:
        relative = Path(relative_path)
        if relative.is_absolute():
            raise ValueError("artifact path must be relative to the store root")
        target = (self.root / relative).resolve()
        try:
            normalized = target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("artifact path escapes the store root") from exc
        if normalized == Path("."):
            raise ValueError("artifact path must name a file")
        return target, normalized

    @staticmethod
    def session_plan_filename(plan: SessionPlan) -> str:
        return (
            f"SESSION_PLAN_{plan.session_date.isoformat()}_"
            f"{plan.session.value}_v{plan.version}.json"
        )

    def _write_unlocked(
        self,
        relative_path: str | Path,
        artifact: Any,
        *,
        schema_version: str | None = None,
    ) -> ArtifactRef:
        target, normalized = self._resolve_relative(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = canonical_json_bytes(artifact) + b"\n"
        try:
            with target.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise ArtifactExistsError(f"artifact already exists: {normalized.as_posix()}") from exc
        _fsync_directory(target.parent)
        return self.expected_reference(
            normalized,
            artifact,
            schema_version=schema_version,
        )

    def expected_reference(
        self,
        relative_path: str | Path,
        artifact: Any,
        *,
        schema_version: str | None = None,
    ) -> ArtifactRef:
        """Compute the exact reference an immutable canonical write will produce."""

        _, normalized = self._resolve_relative(relative_path)
        content = canonical_json_bytes(artifact) + b"\n"
        declared_schema = schema_version or getattr(artifact, "schema_version", None)
        if not declared_schema and isinstance(artifact, Mapping):
            declared_schema = artifact.get("schema_version")
        return ArtifactRef(
            schema_version=str(declared_schema or "canonical_json.v1"),
            path=normalized.as_posix(),
            sha256=sha256(content).hexdigest(),
        )

    def write_artifact(
        self,
        relative_path: str | Path,
        artifact: Any,
        *,
        schema_version: str | None = None,
    ) -> ArtifactRef:
        """Create one canonical JSON artifact using exclusive-create semantics."""

        with _exclusive_file_lock(self._lock_path):
            return self._write_unlocked(
                relative_path,
                artifact,
                schema_version=schema_version,
            )

    def write(
        self,
        artifact: Any,
        relative_path: str | Path,
        *,
        schema_version: str | None = None,
    ) -> ArtifactRef:
        """Convenience spelling with the value first."""

        return self.write_artifact(relative_path, artifact, schema_version=schema_version)

    def write_session_plan(self, plan: SessionPlan) -> ArtifactRef:
        """Write a plan, requiring v2+ to link to the immediate prior version."""

        filename = self.session_plan_filename(plan)
        with _exclusive_file_lock(self._lock_path):
            if plan.version > 1:
                previous_hash: str | None = None
                previous_created_at = None
                for historical_version in range(1, plan.version):
                    historical_filename = (
                        f"SESSION_PLAN_{plan.session_date.isoformat()}_"
                        f"{plan.session.value}_v{historical_version}.json"
                    )
                    historical_path, _ = self._resolve_relative(historical_filename)
                    if not historical_path.is_file():
                        label = (
                            "immediate prior"
                            if historical_version == plan.version - 1
                            else "historical"
                        )
                        raise ArtifactIntegrityError(
                            f"{label} plan is missing: {historical_filename}"
                        )
                    try:
                        historical_content = historical_path.read_bytes()
                        historical = SessionPlan.model_validate_json(historical_content)
                    except Exception as exc:
                        raise ArtifactIntegrityError(
                            f"historical plan is invalid: {historical_filename}"
                        ) from exc
                    if (
                        historical.plan_id != plan.plan_id
                        or historical.version != historical_version
                        or historical.session_date != plan.session_date
                        or historical.session != plan.session
                    ):
                        raise ArtifactIntegrityError(
                            f"historical plan identity does not match: {historical_filename}"
                        )
                    if historical_version > 1 and historical.supersedes_sha256 != previous_hash:
                        raise ArtifactIntegrityError(
                            f"historical plan chain is broken at {historical_filename}"
                        )
                    if (
                        previous_created_at is not None
                        and historical.created_at_utc <= previous_created_at
                    ):
                        raise ArtifactIntegrityError(
                            f"historical plan creation time is not monotonic at {historical_filename}"
                        )
                    previous_created_at = historical.created_at_utc
                    previous_hash = sha256(historical_content).hexdigest()
                if plan.supersedes_sha256 != previous_hash:
                    raise ArtifactIntegrityError(
                        "supersedes_sha256 does not match the immediate prior plan"
                    )
                if previous_created_at is not None and plan.created_at_utc <= previous_created_at:
                    raise ArtifactIntegrityError(
                        "new plan created_at_utc must be later than the immediate prior plan"
                    )
            return self._write_unlocked(filename, plan)

    def verify(self, reference: ArtifactRef) -> Path:
        return verify_artifact(self.root, reference)

    def read_verified_bytes(self, reference: ArtifactRef) -> bytes:
        """Read once, hash those exact bytes, and return that same verified buffer."""

        with _exclusive_file_lock(self._lock_path):
            return read_verified_artifact(self.root, reference)


def _confined_artifact_path(root: str | Path, reference: ArtifactRef) -> tuple[Path, Path]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ArtifactIntegrityError(f"artifact root is missing: {root_path}")
    relative = Path(reference.path)
    if relative.is_absolute():
        raise ArtifactIntegrityError("artifact reference path must be relative")
    lexical = root_path / relative
    current = root_path
    for part in relative.parts:
        current = current / part
        is_junction = getattr(current, "is_junction", lambda: False)
        if current.is_symlink() or is_junction():
            raise ArtifactIntegrityError("artifact reference traverses a link or junction")
    target = lexical.resolve()
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise ArtifactIntegrityError("artifact reference escapes the store root") from exc
    return root_path, target


def read_verified_artifact(root: str | Path, reference: ArtifactRef) -> bytes:
    """Hash and return one read buffer, preventing verify-then-parse substitution."""

    _, target = _confined_artifact_path(root, reference)
    if not target.is_file():
        raise ArtifactIntegrityError(f"artifact is missing: {reference.path}")
    try:
        with target.open("rb") as stream:
            content = stream.read()
    except OSError as exc:
        raise ArtifactIntegrityError(f"artifact cannot be read: {reference.path}") from exc
    actual = sha256(content).hexdigest()
    if actual != reference.sha256.lower():
        raise ArtifactIntegrityError(
            f"artifact hash mismatch for {reference.path}: "
            f"expected {reference.sha256}, got {actual}"
        )
    return content


def verify_artifact(root: str | Path, reference: ArtifactRef) -> Path:
    """Verify a reference and return its root-confined absolute path."""

    _, target = _confined_artifact_path(root, reference)
    read_verified_artifact(root, reference)
    return target


def _coerce_payload(payload: Any) -> Any:
    value = _jsonable(payload)
    # Round-trip now so an append can never partly fail due to an unserializable value.
    return json.loads(canonical_json_bytes(value).decode("utf-8"))


def _ledger_hash_material(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": entry["schema_version"],
        "sequence": entry["sequence"],
        "previous_sha256": entry["previous_sha256"],
        "payload": entry["payload"],
    }


def _decode_and_verify_ledger(content: bytes) -> tuple[dict[str, Any], ...]:
    if not content:
        return ()
    if not content.endswith(b"\n"):
        raise ArtifactIntegrityError("ledger has an incomplete final record")

    entries: list[dict[str, Any]] = []
    expected_previous = _ZERO_HASH
    for line_number, raw_line in enumerate(content.splitlines(keepends=True), start=1):
        try:
            entry = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactIntegrityError(f"invalid ledger JSON at line {line_number}") from exc
        if not isinstance(entry, dict):
            raise ArtifactIntegrityError(f"ledger line {line_number} is not an object")
        expected_keys = {
            "schema_version",
            "sequence",
            "previous_sha256",
            "payload",
            "entry_sha256",
        }
        if set(entry) != expected_keys:
            raise ArtifactIntegrityError(f"ledger line {line_number} has an invalid schema")
        if entry["schema_version"] != "hash_chain_entry.v1":
            raise ArtifactIntegrityError(f"ledger line {line_number} has an unknown schema")
        if entry["sequence"] != line_number:
            raise ArtifactIntegrityError(f"ledger sequence mismatch at line {line_number}")
        if entry["previous_sha256"] != expected_previous:
            raise ArtifactIntegrityError(f"ledger chain link mismatch at line {line_number}")
        actual_hash = sha256(canonical_json_bytes(_ledger_hash_material(entry))).hexdigest()
        if entry["entry_sha256"] != actual_hash:
            raise ArtifactIntegrityError(f"ledger entry hash mismatch at line {line_number}")
        if raw_line != canonical_json_bytes(entry) + b"\n":
            raise ArtifactIntegrityError(f"ledger line {line_number} is not canonical JSON")
        expected_previous = actual_hash
        entries.append(entry)
    return tuple(entries)


class HashChainLedger:
    """Concurrent-writer-safe JSONL ledger with a verified SHA-256 chain."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.lock_path = self.path.with_name(f".{self.path.name}.lock")

    def _verify_unlocked(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        return _decode_and_verify_ledger(self.path.read_bytes())

    def verify(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        with _exclusive_file_lock(self.lock_path):
            return self._verify_unlocked()

    def _append_unlocked(
        self,
        normalized_payload: Any,
        entries: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        sequence = len(entries) + 1
        previous_hash = entries[-1]["entry_sha256"] if entries else _ZERO_HASH
        material = {
            "schema_version": "hash_chain_entry.v1",
            "sequence": sequence,
            "previous_sha256": previous_hash,
            "payload": normalized_payload,
        }
        entry = {
            **material,
            "entry_sha256": sha256(canonical_json_bytes(material)).hexdigest(),
        }
        line = canonical_json_bytes(entry) + b"\n"
        with self.path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(self.path.parent)
        return entry

    def append(self, payload: Any) -> dict[str, Any]:
        normalized_payload = _coerce_payload(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_file_lock(self.lock_path):
            entries = self._verify_unlocked()
            return self._append_unlocked(normalized_payload, entries)

    def reserve_idempotency_key(self, key: str, payload: Any) -> dict[str, Any]:
        """Atomically reject duplicates and reserve a once-only intent key."""

        if len(key) != 64 or any(character not in "0123456789abcdefABCDEF" for character in key):
            raise ValueError("idempotency key must be a 64-character hexadecimal digest")
        normalized_payload = _coerce_payload(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_file_lock(self.lock_path):
            entries = self._verify_unlocked()
            for entry in entries:
                envelope = entry.get("payload")
                if not isinstance(envelope, Mapping):
                    continue
                seen = envelope.get("idempotency_key")
                nested = envelope.get("payload")
                if not seen and isinstance(nested, Mapping):
                    seen = nested.get("idempotency_key")
                if isinstance(seen, str) and seen.lower() == key.lower():
                    raise ArtifactExistsError("idempotency key is already reserved")
            return self._append_unlocked(normalized_payload, entries)

    def append_unique(self, event_key: str, payload: Any) -> dict[str, Any]:
        """Atomically append one logical component event exactly once."""

        if not event_key or len(event_key) > 240:
            raise ValueError("event_key must contain 1..240 characters")
        normalized_payload = _coerce_payload(payload)
        if not isinstance(normalized_payload, dict):
            raise ValueError("unique ledger payload must be an object")
        if normalized_payload.get("event_key") != event_key:
            raise ValueError("unique ledger payload must contain the same event_key")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_file_lock(self.lock_path):
            entries = self._verify_unlocked()
            for entry in entries:
                envelope = entry.get("payload")
                if isinstance(envelope, Mapping) and envelope.get("event_key") == event_key:
                    raise ArtifactExistsError("event_key is already recorded")
            return self._append_unlocked(normalized_payload, entries)


def verify_ledger(path: str | Path) -> tuple[dict[str, Any], ...]:
    return HashChainLedger(path).verify()


__all__ = [
    "ArtifactError",
    "ArtifactExistsError",
    "ArtifactIntegrityError",
    "ArtifactStore",
    "HashChainLedger",
    "canonical_json_bytes",
    "read_verified_artifact",
    "sha256_file",
    "verify_artifact",
    "verify_ledger",
]
