# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path(__file__).resolve().parents[2] / "04. Memory" / "hot.md"
raw = p.read_bytes()
# Try utf-8 first
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    text = raw.decode("utf-8", errors="replace")

# Mojibake from UTF-8 interpreted as cp1252 then re-saved
fixes = {
    "\u00e2\u20ac\u201d": "\u2014",  # —
    "\u00e2\u20ac\u2014": "\u2014",
    "\u00e2\u20ac\u00a6": "\u2026",  # …
    "\u00e2\u2020\u2019": "\u2192",  # → (common broken form)
    "\u00c2\u00b7": "\u00b7",  # ·
}
for a, b in fixes.items():
    text = text.replace(a, b)

# Literal mojibake strings often seen
literal_fixes = [
    ("â€”", "—"),
    ("â€“", "–"),
    ("â€¦", "…"),
    ("â†’", "→"),
    ("Â·", "·"),
]
for a, b in literal_fixes:
    text = text.replace(a, b)

text = re.sub(
    r"auth \*\*`20260714_225915`\*\* \(prior label\s*`225340` same metrics class\):",
    "auth **`20260714_225915`**:",
    text,
)

# Rewrite first Updated line cleanly
lines = text.splitlines(keepends=True)
if lines and lines[0].startswith("# Hot Cache"):
    # find Updated line
    for i, ln in enumerate(lines[:8]):
        if ln.startswith("Updated:"):
            lines[i] = (
                "Updated: 2026-07-14 ~23:00 ICT | Wave5 CLOSED NY-IB PARK "
                "PF 1.02; next rebuild A/B; RR2 best; GOAL unmet\n"
            )
            # drop leftover wrap line if it looks like old continuation
            if i + 1 < len(lines) and lines[i + 1].startswith("("):
                lines[i + 1] = "\n"
            break
    text = "".join(lines)

p.write_text(text, encoding="utf-8", newline="\n")
print("OK")
for ln in p.read_text(encoding="utf-8").splitlines()[:22]:
    print(ln)
