"""Append one time-stamped entry to a log file. The stamp comes from the system clock (UTC).

Lead Ruling 14 section 14.1: every time written in a log, note, ruling or report is copied
from a command run in the same step, never estimated. This tool makes that the easy way.

Usage (from the repo root, or any cwd; the log path may be relative or absolute):
  python logline.py <log_path> "entry text"      append "- HH:MMZ entry text"
  python logline.py <log_path> @entry.txt        entry text read from a UTF-8 file (multi-line ok)
  python logline.py --now                        print HH:MMZ only
  python logline.py --now --seconds              print HH:MM:SSZ

Continuation lines of a multi-line entry are indented by two spaces, so the entry stays one
markdown list item. The file's existing newline style (LF or CRLF) is kept. Nothing is ever
rewritten or deleted: the tool only appends.
"""
import datetime
import io
import os
import sys


def stamp(seconds=False):
    fmt = "%H:%M:%SZ" if seconds else "%H:%MZ"
    return datetime.datetime.now(datetime.timezone.utc).strftime(fmt)


def _newline_of(path):
    """Return the newline style used by an existing file (default LF), and whether it ends with one."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return "\n", True
    with open(path, "rb") as f:
        head = f.read(8192)
        f.seek(-1, os.SEEK_END)
        last = f.read(1)
    nl = "\r\n" if b"\r\n" in head else "\n"
    return nl, last == b"\n"


def append_entry(path, text):
    lines = [ln.rstrip() for ln in text.strip("\r\n").splitlines()] or [""]
    entry_lines = ["- " + stamp() + " " + lines[0]] + ["  " + ln for ln in lines[1:]]
    nl, ends_ok = _newline_of(path)
    body = ("" if ends_ok else nl) + nl.join(entry_lines) + nl
    with io.open(path, "a", encoding="utf-8", newline="") as f:
        f.write(body)
    return "\n".join(entry_lines)


def main(argv):
    if len(argv) >= 2 and argv[1] == "--now":
        print(stamp(seconds="--seconds" in argv[2:]))
        return 0
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    path, text = argv[1], argv[2]
    if text.startswith("@"):
        with io.open(text[1:], encoding="utf-8") as f:
            text = f.read()
    if not text.strip():
        sys.stderr.write("logline: empty entry, nothing written\n")
        return 2
    print(append_entry(path, text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
