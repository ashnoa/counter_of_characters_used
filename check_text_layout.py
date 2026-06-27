#!/usr/bin/env python3
"""Check text layout limits for Game Boy diary text."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


PAGE_BREAK_LINE = "[改ページ]"
MAX_LINE_LENGTH = 18
MAX_LINES_PER_PAGE = 16


@dataclass(frozen=True)
class LayoutIssue:
    message: str


def is_page_break_line(line: str) -> bool:
    return line.rstrip("\r\n") == PAGE_BREAK_LINE


def split_pages_with_line_numbers(text: str) -> list[list[tuple[int, str]]]:
    pages: list[list[tuple[int, str]]] = []
    current_page: list[tuple[int, str]] = []

    for line_number, line in enumerate(text.splitlines(keepends=True), start=1):
        if is_page_break_line(line):
            pages.append(current_page)
            current_page = []
        else:
            current_page.append((line_number, line))

    pages.append(current_page)
    return pages


def check_text_layout(text: str) -> list[LayoutIssue]:
    issues: list[LayoutIssue] = []
    pages = split_pages_with_line_numbers(text)

    for page_index, page in enumerate(pages):
        if len(page) > MAX_LINES_PER_PAGE:
            issues.append(
                LayoutIssue(
                    f"page {page_index}: has {len(page)} lines; "
                    f"maximum is {MAX_LINES_PER_PAGE}"
                )
            )

        for line_number, line in page:
            content = line.rstrip("\r\n")
            if len(content) > MAX_LINE_LENGTH:
                issues.append(
                    LayoutIssue(
                        f"line {line_number}: has {len(content)} characters; "
                        f"maximum is {MAX_LINE_LENGTH}: {content}"
                    )
                )

    return issues


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check line length and page line count for diary text.",
    )
    parser.add_argument("file", type=Path, help="Text file to check.")
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding used to read the file. Defaults to utf-8.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        text = args.file.read_text(encoding=args.encoding)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    issues = check_text_layout(text)
    if issues:
        for issue in issues:
            print(f"error: {issue.message}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
