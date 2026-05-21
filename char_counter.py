#!/usr/bin/env python3
"""Count distinct characters used in a text file."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path


VISIBLE_LABELS = {
    " ": "<SPACE>",
    "\n": "<LF>",
    "\r": "<CR>",
    "\t": "<TAB>",
}


def count_characters(text: str, *, exclude_whitespace: bool = False) -> Counter[str]:
    """Return character counts, preserving first-seen order."""
    counter: Counter[str] = Counter()
    for char in text:
        if exclude_whitespace and char.isspace():
            continue
        counter[char] += 1
    return counter


def display_char(char: str) -> str:
    """Return a readable label for characters that are hard to see."""
    if char in VISIBLE_LABELS:
        return VISIBLE_LABELS[char]
    if char.isspace():
        codepoint = ord(char)
        return f"<U+{codepoint:04X}>"
    return char


def format_counts(counter: Counter[str]) -> str:
    lines = [f"種類数: {len(counter)}", "文字\t回数"]
    for char, count in counter.items():
        lines.append(f"{display_char(char)}\t{count}")
    return "\n".join(lines)


def read_text_file(path: Path, encoding: str) -> str:
    return path.read_text(encoding=encoding)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count distinct characters used in a text file.",
    )
    parser.add_argument("file", type=Path, help="Text file to analyze.")
    parser.add_argument(
        "--exclude-whitespace",
        action="store_true",
        help="Exclude whitespace characters such as spaces, tabs, and newlines.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding used to read the file. Defaults to utf-8.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        text = read_text_file(args.file, args.encoding)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1
    except IsADirectoryError:
        print(f"error: not a file: {args.file}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as exc:
        print(
            f"error: could not decode {args.file} with encoding {args.encoding}: {exc}",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"error: could not read {args.file}: {exc}", file=sys.stderr)
        return 1

    counter = count_characters(text, exclude_whitespace=args.exclude_whitespace)
    print(format_counts(counter))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
