#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flatten a local MQL5 source tree with quoted #include directives into one file.

Use case:
- keep Phoenix deliverable as one-file EA
- avoid manual copy/paste drift
- preserve include provenance with marker comments
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Set


INCLUDE_RE = re.compile(r'^\s*#include\s+"([^"]+)"')


def flatten(path: Path, root: Path, seen: Set[Path]) -> str:
    if path in seen:
        return f"\n// [flatten] skipped duplicate include: {path.relative_to(root)}\n"
    seen.add(path)

    text = path.read_text(encoding="utf-8", errors="ignore").replace("\ufeff", "")
    lines = text.splitlines()
    out = [f"// ===== BEGIN {path.relative_to(root)} ====="]
    for line in lines:
        m = INCLUDE_RE.match(line)
        if not m:
            out.append(line)
            continue
        inc = (path.parent / m.group(1)).resolve()
        if not inc.exists():
            out.append(f"// [flatten] unresolved include kept as comment: {line}")
            continue
        out.append(flatten(inc, root, seen))
    out.append(f"// ===== END {path.relative_to(root)} =====")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="Flatten MQL5 quoted includes into one file")
    ap.add_argument("--src", required=True, help="Source .mq5 file")
    ap.add_argument("--out", required=True, help="Output flattened .mq5 file")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    out = Path(args.out).resolve()
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")

    text = flatten(src, src.parent, set())
    out.write_text(text + "\n", encoding="utf-8")
    print(f"Flattened -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
