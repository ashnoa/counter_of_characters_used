#!/usr/bin/env python3
"""Count distinct characters used in a text file."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter
from pathlib import Path


VISIBLE_LABELS = {
    " ": "<SPACE>",
    "\n": "<LF>",
    "\r": "<CR>",
    "\t": "<TAB>",
}
PAGE_BREAK_LINE = "[改ページ]"


def remove_page_break_lines(text: str) -> str:
    """Remove lines that only contain the page break marker."""
    return "".join(
        line
        for line in text.splitlines(keepends=True)
        if line.rstrip("\r\n") != PAGE_BREAK_LINE
    )


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


def count_rows(counter: Counter[str]) -> list[dict[str, str | int]]:
    return [
        {"character": char, "display": display_char(char), "count": count}
        for char, count in counter.items()
    ]


def format_csv(counter: Counter[str]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["character", "display", "count"])
    writer.writeheader()
    writer.writerows(count_rows(counter))
    return output.getvalue().rstrip("\r\n")


def format_json(counter: Counter[str]) -> str:
    result = {
        "type_count": len(counter),
        "characters": count_rows(counter),
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


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
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--csv",
        action="store_true",
        help="Output results as CSV.",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
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

    counter = count_characters(
        remove_page_break_lines(text),
        exclude_whitespace=args.exclude_whitespace,
    )
    if args.csv:
        print(format_csv(counter))
    elif args.json:
        print(format_json(counter))
    else:
        print(format_counts(counter))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
