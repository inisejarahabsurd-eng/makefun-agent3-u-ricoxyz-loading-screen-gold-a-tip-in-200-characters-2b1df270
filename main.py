#!/usr/bin/env python3
"""Generate a single loading-screen tip and write it to /output/entry.txt.

Design constraints from the competition brief:
  * 1-200 characters, UTF-8, not only whitespace, no trailing whitespace.
  * Judge weighs (1) laugh, (2) audience fit, (3) economy of words.
  * Audience is doubly-served: stressed developers AND AI coding agents.
  * Short (~60-120 chars) beats padded 200-char filler.

Strategy: keep a curated list of candidate tips, filter each through the
exact same validation rules the sealed gate applies, then pick the
shortest candidate that survives. The chosen line hits both audiences in
one breath (agents retry; developers wait on retries) and repeats on
every loading screen without wearing out.
"""
from __future__ import annotations

import os
import sys
import tempfile
from typing import Iterable, List

MAX_CHARS = 200
OUTPUT_PATH = os.environ.get("ENTRY_PATH", "/output/entry.txt")

# Candidate tips, ordered subjectively from strongest to weakest.
# Each targets both audiences: developers *and* AI coding agents.
# Kept short: economy is a scoring axis, not a nice-to-have.
CANDIDATES: List[str] = [
    # 1. Hits retry loops (agent) and flaky CI (developer). Tight pivot.
    "Retrying, like you, on the thing that already failed. It'll work this time.",
    # 2. Hallucination + stack trace. One pivot from "confident" to "wrong".
    "Still thinking. Which, statistically, means it may be confidently wrong.",
    # 3. Context window + deploy anxiety. Short, warm, self-aware.
    "Warming up. Unlike your context window, this one never forgets.",
    # 4. Tool loop + Monday deploys. Comic fatalism.
    "Loading. If this is a loop, at least you're not alone in it.",
    # 5. Token bill + patience. Baseline, weaker than the rest.
    "Thinking… burning tokens so you don't have to. You're welcome.",
]


def validate(text: str) -> tuple[bool, str]:
    """Apply the same gate the sealed scorer uses.

    Returns (ok, reason). OK means: UTF-8, 1..MAX_CHARS chars, not only
    whitespace, no trailing whitespace.
    """
    if text is None:
        return False, "None"
    if not isinstance(text, str):
        return False, f"not str: {type(text).__name__}"
    # Encoding must round-trip as UTF-8 bytes.
    try:
        raw = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        return False, f"encode failed: {exc}"
    # 1..200 characters, counted as Unicode code points.
    n = len(text)
    if n < 1:
        return False, "empty"
    if n > MAX_CHARS:
        return False, f"too long: {n} > {MAX_CHARS}"
    if text.strip() == "":
        return False, "only whitespace"
    if text != text.rstrip():
        return False, "trailing whitespace"
    if len(raw) == 0:
        return False, "empty bytes"
    return True, f"ok ({n} chars, {len(raw)} bytes)"


def pick(candidates: Iterable[str]) -> str:
    """Return the shortest candidate that passes validate()."""
    valid = []
    for c in candidates:
        ok, reason = validate(c)
        if ok:
            valid.append(c)
    if not valid:
        raise SystemExit("FATAL: no candidate passed validation")
    valid.sort(key=len)
    return valid[0]


def write_atomic(path: str, data: str) -> None:
    """Write bytes atomically so /output/entry.txt is never half-written."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".entry.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    try:
        chosen = pick(CANDIDATES)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    # Final defensive check on the exact bytes we will write.
    ok, reason = validate(chosen)
    if not ok:
        print(f"FATAL: chosen tip failed validation: {reason}", file=sys.stderr)
        return 2
    write_atomic(OUTPUT_PATH, chosen)
    n = len(chosen)
    print(f"wrote {OUTPUT_PATH} ({n} chars, valid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())