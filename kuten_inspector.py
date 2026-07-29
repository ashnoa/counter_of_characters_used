#!/usr/bin/env python3
"""Inspect JIS X 0208 kuten codes and font coverage for counted characters."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

from char_counter import count_characters, display_char, read_text_file


MISAKI_KUTEN_EXTENSIONS = {
    "Ⅰ": (13, 21),
    "Ⅱ": (13, 22),
    "Ⅲ": (13, 23),
}


def jis_x_0208_kuten(char: str) -> tuple[int, int] | None:
    """Return the JIS X 0208 kuten code for a character, if available."""
    try:
        encoded = char.encode("iso2022_jp")
    except UnicodeEncodeError:
        return None

    marker = b"\x1b$B"
    start = encoded.find(marker)
    if start == -1:
        return None

    body_start = start + len(marker)
    if len(encoded) < body_start + 2:
        return None

    first, second = encoded[body_start], encoded[body_start + 1]
    if not (0x21 <= first <= 0x7E and 0x21 <= second <= 0x7E):
        return None

    return first - 0x20, second - 0x20


def kuten_for_character(
    char: str,
    *,
    misaki: bool = False,
) -> tuple[int, int] | None:
    """Return a usable kuten code, optionally including Misaki extensions."""
    kuten = jis_x_0208_kuten(char)
    if kuten is not None:
        return kuten
    if misaki:
        return MISAKI_KUTEN_EXTENSIONS.get(char)
    return None


def format_kuten(kuten: tuple[int, int] | None) -> str:
    if kuten is None:
        return ""
    ku, ten = kuten
    return f"{ku:02d}-{ten:02d}"


def load_font_codepoints(font_path: Path, font_number: int | None = None) -> set[int]:
    try:
        from fontTools.ttLib import TTCollection, TTFont
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "fontTools is required to inspect font coverage. "
            "Install it with: python3 -m pip install -r requirements.txt"
        ) from exc

    if font_path.suffix.lower() == ".ttc":
        collection = TTCollection(font_path)
        if font_number is None:
            font_number = 0
        if font_number < 0 or font_number >= len(collection.fonts):
            raise ValueError(
                f"font number {font_number} is out of range; "
                f"{font_path} contains {len(collection.fonts)} fonts"
            )
        font = collection.fonts[font_number]
    elif font_number is None:
        font = TTFont(font_path)
    else:
        font = TTFont(font_path, fontNumber=font_number)

    codepoints: set[int] = set()
    for table in font["cmap"].tables:
        if table.isUnicode():
            codepoints.update(table.cmap.keys())
    return codepoints


def rows_from_counter(
    counter: dict[str, int],
    font_codepoints: set[int],
    *,
    misaki: bool = False,
) -> list[dict[str, str | int | bool]]:
    rows: list[dict[str, str | int | bool]] = []
    for char, count in counter.items():
        jis_kuten = jis_x_0208_kuten(char)
        kuten = jis_kuten
        if kuten is None and misaki:
            kuten = MISAKI_KUTEN_EXTENSIONS.get(char)
        rows.append(
            {
                "character": char,
                "display": display_char(char),
                "codepoint": f"U+{ord(char):04X}",
                "count": count,
                "jis_x_0208_kuten": format_kuten(kuten),
                "in_jis_x_0208": jis_kuten is not None,
                "in_font": ord(char) in font_codepoints,
            }
        )
    return rows


def load_counter_from_char_counter_json(path: Path) -> dict[str, int]:
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    characters = data.get("characters")
    if not isinstance(characters, list):
        raise ValueError("JSON must contain a characters array")

    counter: dict[str, int] = {}
    for item in characters:
        if not isinstance(item, dict):
            raise ValueError("Each characters item must be an object")
        char = item.get("character")
        count = item.get("count")
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError("Each characters item must contain a single character")
        if not isinstance(count, int):
            raise ValueError("Each characters item must contain an integer count")
        counter[char] = count
    return counter


def format_csv(rows: list[dict[str, str | int | bool]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "character",
            "display",
            "codepoint",
            "count",
            "jis_x_0208_kuten",
            "in_jis_x_0208",
            "in_font",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().rstrip("\r\n")


def format_json(rows: list[dict[str, str | int | bool]]) -> str:
    return json.dumps({"characters": rows}, ensure_ascii=False, indent=2)


def warn_missing_kuten(
    rows: list[dict[str, str | int | bool]],
    *,
    stream: Any = sys.stderr,
) -> None:
    missing_rows = [row for row in rows if not row["jis_x_0208_kuten"]]
    if not missing_rows:
        return

    print(
        f"warning: {len(missing_rows)} character(s) have no JIS X 0208 kuten code:",
        file=stream,
    )
    for row in missing_rows:
        print(
            f"  {row['display']} ({row['codepoint']})",
            file=stream,
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect JIS X 0208 kuten codes and font coverage.",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--text",
        type=Path,
        help="Text file to analyze directly.",
    )
    input_group.add_argument(
        "--char-counter-json",
        type=Path,
        help="JSON file generated by: python3 char_counter.py --json ...",
    )
    parser.add_argument(
        "--font",
        type=Path,
        required=True,
        help="OpenType/TrueType font file to inspect.",
    )
    parser.add_argument(
        "--font-number",
        type=int,
        default=None,
        help="Font index to use for TTC collections. Defaults to 0 for .ttc files.",
    )
    parser.add_argument(
        "--misaki",
        action="store_true",
        help="Include Misaki Font kuten extensions in row 13.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding for --text input. Defaults to utf-8.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON. Defaults to CSV.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if args.text:
            text = read_text_file(args.text, args.encoding)
            counter = dict(count_characters(text))
        else:
            counter = load_counter_from_char_counter_json(args.char_counter_json)

        font_codepoints = load_font_codepoints(args.font, args.font_number)
        rows = rows_from_counter(counter, font_codepoints, misaki=args.misaki)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    warn_missing_kuten(rows)

    if args.json:
        print(format_json(rows))
    else:
        print(format_csv(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
