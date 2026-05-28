#!/usr/bin/env python3
"""Encode text characters into 16-bit words using bank/index mapping CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


NEWLINE_WORD = 0xFFFE
EOF_WORD = 0xFFFF


def load_mapping(path: Path) -> dict[str, int]:
    mapping: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"character", "bank", "index"}
        if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
            fields = ", ".join(sorted(required_fields))
            raise ValueError(f"mapping CSV must contain columns: {fields}")

        for line_number, row in enumerate(reader, start=2):
            char = row["character"]
            if len(char) != 1:
                raise ValueError(
                    f"line {line_number}: character must be exactly one character"
                )

            try:
                bank = int(row["bank"], 0)
                index = int(row["index"], 0)
            except ValueError as exc:
                raise ValueError(
                    f"line {line_number}: bank and index must be integers"
                ) from exc

            if not 0 <= bank <= 0xF:
                raise ValueError(f"line {line_number}: bank must fit in 4 bits")
            if not 0 <= index <= 0xFFF:
                raise ValueError(f"line {line_number}: index must fit in 12 bits")
            if char in mapping:
                raise ValueError(f"line {line_number}: duplicate character: {char}")

            mapping[char] = (bank << 12) | index

    return mapping


def encode_text(text: str, mapping: dict[str, int]) -> list[int]:
    words: list[int] = []
    for position, char in enumerate(text, start=1):
        if char == "\n":
            words.append(NEWLINE_WORD)
            continue

        try:
            words.append(mapping[char])
        except KeyError as exc:
            codepoint = f"U+{ord(char):04X}"
            raise ValueError(
                f"no mapping for character at position {position}: {char} ({codepoint})"
            ) from exc

    words.append(EOF_WORD)
    return words


def format_dw(words: list[int], *, values_per_line: int = 16) -> str:
    if values_per_line <= 0:
        raise ValueError("values_per_line must be greater than zero")

    lines: list[str] = []
    for start in range(0, len(words), values_per_line):
        chunk = words[start : start + values_per_line]
        values = ", ".join(f"${word:04X}" for word in chunk)
        lines.append(f"dw {values}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Encode a text file into dw words using bank/index mapping CSV.",
    )
    parser.add_argument("--text", type=Path, required=True, help="Source text file.")
    parser.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="CSV file containing character, bank, and index columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file. Defaults to standard output.",
    )
    parser.add_argument(
        "--values-per-line",
        type=int,
        default=16,
        help="Number of dw values per line. Defaults to 16.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        mapping = load_mapping(args.mapping)
        text = args.text.read_text(encoding="utf-8")
        output = format_dw(encode_text(text, mapping), values_per_line=args.values_per_line)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            args.output.write_text(output + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
