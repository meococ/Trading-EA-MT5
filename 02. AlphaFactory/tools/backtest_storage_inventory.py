#!/usr/bin/env python3
"""Create a compact storage inventory for AlphaFactory run artifacts."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


SCHEMA = "alpha-backtest-storage-inventory-v2"


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def scan_storage(runs_root: Path, top_n: int = 50) -> dict:
    runs_root = runs_root.resolve(strict=True)
    if not runs_root.is_dir():
        raise ValueError(f"Runs root is not a directory: {runs_root}")
    total_bytes = 0
    total_files = 0
    per_ea: dict[str, dict[str, int]] = defaultdict(lambda: {"bytes": 0, "files": 0})
    top_files: list[dict] = []
    orphan_files: list[dict] = []
    mirror_map: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(dict)

    for root, dirs, files in os.walk(runs_root, followlinks=False):
        dirs[:] = [name for name in dirs if not Path(root, name).is_symlink()]
        for name in files:
            path = Path(root, name)
            try:
                stat = path.stat()
            except (FileNotFoundError, PermissionError):
                continue
            relative = path.relative_to(runs_root)
            parts = relative.parts
            ea_name = parts[0] if parts else "_root"
            size = stat.st_size
            total_bytes += size
            total_files += 1
            per_ea[ea_name]["bytes"] += size
            per_ea[ea_name]["files"] += 1
            entry = {
                "path": relative.as_posix(),
                "size_bytes": size,
                "last_write_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }
            top_files.append(entry)
            if len(parts) == 2:
                orphan_files.append(entry)
            if len(parts) >= 4:
                if parts[2] == "logs":
                    mirror_map[(parts[0], parts[1], "/".join(parts[3:]))]["primary"] = {
                        "entry": entry,
                        "identity": (stat.st_dev, stat.st_ino),
                    }
                elif len(parts) >= 5 and parts[2] == "analysis" and parts[3] == "logs":
                    mirror_map[(parts[0], parts[1], "/".join(parts[4:]))]["mirror"] = {
                        "entry": entry,
                        "identity": (stat.st_dev, stat.st_ino),
                    }

    potential_mirrors: list[dict] = []
    potential_bytes = 0
    already_hardlinked_pairs = 0
    already_hardlinked_logical_bytes = 0
    for (ea_name, run_id, name), pair in mirror_map.items():
        primary_record = pair.get("primary")
        mirror_record = pair.get("mirror")
        if not primary_record or not mirror_record:
            continue
        primary = primary_record["entry"]
        mirror = mirror_record["entry"]
        if primary_record["identity"] == mirror_record["identity"]:
            already_hardlinked_pairs += 1
            already_hardlinked_logical_bytes += mirror["size_bytes"]
        elif primary["size_bytes"] == mirror["size_bytes"]:
            potential_bytes += mirror["size_bytes"]
            potential_mirrors.append(
                {
                    "ea_name": ea_name,
                    "run_id": run_id,
                    "name": name,
                    "size_bytes": mirror["size_bytes"],
                    "primary": primary["path"],
                    "mirror": mirror["path"],
                    "status": "size_match_requires_sha256_dedupe_tool",
                }
            )

    top_files.sort(key=lambda item: item["size_bytes"], reverse=True)
    orphan_files.sort(key=lambda item: item["size_bytes"], reverse=True)
    potential_mirrors.sort(key=lambda item: item["size_bytes"], reverse=True)
    ea_rows = [
        {"ea_name": name, "size_bytes": values["bytes"], "file_count": values["files"]}
        for name, values in per_ea.items()
    ]
    ea_rows.sort(key=lambda item: item["size_bytes"], reverse=True)
    return {
        "schema_version": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(runs_root),
        "total_size_bytes": total_bytes,
        "total_file_count": total_files,
        "ea_count": len(ea_rows),
        "per_ea": ea_rows,
        "top_files": top_files[:top_n],
        "direct_orphan_file_count": len(orphan_files),
        "direct_orphan_size_bytes": sum(item["size_bytes"] for item in orphan_files),
        "top_direct_orphan_files": orphan_files[:top_n],
        "potential_mirror_pair_count": len(potential_mirrors),
        "potential_mirror_reclaimable_bytes": potential_bytes,
        "potential_mirrors": potential_mirrors[:top_n],
        "already_hardlinked_mirror_pair_count": already_hardlinked_pairs,
        "already_hardlinked_mirror_logical_bytes": already_hardlinked_logical_bytes,
        "estimated_physical_size_bytes": total_bytes - already_hardlinked_logical_bytes,
        "limits": {
            "top_n": top_n,
            "mirror_candidates_are_size_only": True,
            "execute_requires_exact_sha256": True,
            "estimated_physical_size_deduplicates_recognized_log_mirrors_only": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--top", type=int, default=50)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.top < 1 or args.top > 500:
        raise ValueError("--top must be between 1 and 500")
    alpha_root = Path(__file__).resolve().parents[1]
    runs_root = args.runs_root or (alpha_root / "runs")
    output = args.out or (alpha_root / "runtime" / "storage" / "backtest_inventory.json")
    payload = scan_storage(runs_root, args.top)
    _atomic_json(output.resolve(), payload)
    print(
        "BACKTEST_STORAGE_INVENTORY_CREATED "
        f"path={output.resolve()} bytes={payload['total_size_bytes']} files={payload['total_file_count']} "
        f"orphan_bytes={payload['direct_orphan_size_bytes']} "
        f"potential_mirror_bytes={payload['potential_mirror_reclaimable_bytes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
