#!/usr/bin/env python3
"""Render encoded text words with banked PNG tilesets for visual inspection."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any


TILE_WIDTH = 8
TILE_HEIGHT = 8
CANVAS_COLUMNS = 32
CANVAS_ROWS = 32
CANVAS_WIDTH = CANVAS_COLUMNS * TILE_WIDTH
CANVAS_HEIGHT = CANVAS_ROWS * TILE_HEIGHT
TILESET_COLUMNS = 16
TILESET_ROWS = 24
TILESET_WIDTH = TILESET_COLUMNS * TILE_WIDTH
TILESET_HEIGHT = TILESET_ROWS * TILE_HEIGHT
TILESET_TILE_COUNT = TILESET_COLUMNS * TILESET_ROWS
BACKGROUND_COLOR = (255, 255, 255)
NEWLINE_WORD = 0xFFFE
EOF_WORD = 0xFFFF


def load_pillow() -> Any:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Pillow is required to render previews. "
            "Install it with: python3 -m pip install -r requirements.txt"
        ) from exc
    return Image


def parse_asm_words(text: str) -> list[int]:
    words: list[int] = []
    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.split(";", 1)[0].strip()
        if not line:
            continue

        match = re.fullmatch(r"(?i:dw)\s+(.+)", line)
        if match is None:
            raise ValueError(f"line {line_number}: expected a dw directive")

        operands = match.group(1).split(",")
        for operand in operands:
            value = operand.strip()
            if re.fullmatch(r"\$[0-9A-Fa-f]{1,4}", value) is None:
                raise ValueError(
                    f"line {line_number}: invalid 16-bit hexadecimal value: {value!r}"
                )
            words.append(int(value[1:], 16))

    if EOF_WORD not in words:
        raise ValueError("ASM does not contain the EOF word $FFFF")

    eof_position = words.index(EOF_WORD)
    if eof_position != len(words) - 1:
        raise ValueError(
            f"word {eof_position + 2}: data appears after the EOF word $FFFF"
        )
    return words


def parse_tileset_arguments(values: list[str]) -> dict[int, Path]:
    tilesets: dict[int, Path] = {}
    for value in values:
        bank_text, separator, path_text = value.partition("=")
        if not separator or not bank_text or not path_text:
            raise ValueError(
                f"invalid tileset specification {value!r}; expected BANK=PATH"
            )
        try:
            bank = int(bank_text, 0)
        except ValueError as exc:
            raise ValueError(
                f"invalid bank in tileset specification {value!r}"
            ) from exc
        if not 0 <= bank <= 0xF:
            raise ValueError(f"tileset bank must be between 0 and 15: {bank}")
        if bank in tilesets:
            raise ValueError(f"duplicate tileset bank: {bank}")
        tilesets[bank] = Path(path_text)
    return tilesets


def load_tilesets(paths: dict[int, Path]) -> dict[int, Any]:
    Image = load_pillow()
    tilesets: dict[int, Any] = {}
    for bank, path in paths.items():
        with Image.open(path) as image:
            if image.size != (TILESET_WIDTH, TILESET_HEIGHT):
                raise ValueError(
                    f"tileset for bank {bank} must be "
                    f"{TILESET_WIDTH}x{TILESET_HEIGHT} px: "
                    f"got {image.size[0]}x{image.size[1]} px"
                )
            tilesets[bank] = image.convert("RGB")
    return tilesets


def source_box_for_index(index: int) -> tuple[int, int, int, int]:
    if not 0 <= index < TILESET_TILE_COUNT:
        raise ValueError(
            f"tileset index must be between 0 and {TILESET_TILE_COUNT - 1}: {index}"
        )
    left = (index % TILESET_COLUMNS) * TILE_WIDTH
    top = (index // TILESET_COLUMNS) * TILE_HEIGHT
    return left, top, left + TILE_WIDTH, top + TILE_HEIGHT


def render_encoded_words(
    words: list[int],
    tilesets: dict[int, Any],
    *,
    start_x: int = 1,
    start_y: int = 1,
) -> Any:
    if not 0 <= start_x < CANVAS_COLUMNS:
        raise ValueError(f"start_x must be between 0 and {CANVAS_COLUMNS - 1}")
    if not 0 <= start_y < CANVAS_ROWS:
        raise ValueError(f"start_y must be between 0 and {CANVAS_ROWS - 1}")

    Image = load_pillow()
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BACKGROUND_COLOR)
    x = start_x
    y = start_y

    for word_position, word in enumerate(words, start=1):
        if word == EOF_WORD:
            return canvas
        if word == NEWLINE_WORD:
            x = start_x
            y += 1
            continue
        if not 0 <= word <= 0xFFFF:
            raise ValueError(f"word {word_position}: value must fit in 16 bits: {word}")
        if not 0 <= x < CANVAS_COLUMNS or not 0 <= y < CANVAS_ROWS:
            raise ValueError(
                f"word {word_position} (${word:04X}) does not fit at tile ({x},{y})"
            )

        bank = word >> 12
        index = word & 0x0FFF
        try:
            tileset = tilesets[bank]
        except KeyError as exc:
            raise ValueError(
                f"word {word_position} (${word:04X}) references missing tileset bank {bank}"
            ) from exc
        try:
            source_box = source_box_for_index(index)
        except ValueError as exc:
            raise ValueError(
                f"word {word_position} (${word:04X}) has invalid tileset index {index}"
            ) from exc

        tile = tileset.crop(source_box)
        canvas.paste(tile, (x * TILE_WIDTH, y * TILE_HEIGHT))
        x += 1

    raise ValueError("encoded words do not contain the EOF word $FFFF")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render encoded ASM text as a 32x32-tile PNG preview.",
    )
    parser.add_argument("--asm", type=Path, required=True, help="Encoded ASM file.")
    parser.add_argument(
        "--tileset",
        action="append",
        required=True,
        metavar="BANK=PATH",
        help="Tileset PNG for a bank. May be specified more than once.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output PNG path.")
    parser.add_argument(
        "--start-x",
        type=int,
        default=1,
        help="Starting tile X coordinate. Defaults to 1.",
    )
    parser.add_argument(
        "--start-y",
        type=int,
        default=1,
        help="Starting tile Y coordinate. Defaults to 1.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        words = parse_asm_words(args.asm.read_text(encoding="utf-8"))
        tileset_paths = parse_tileset_arguments(args.tileset)
        tilesets = load_tilesets(tileset_paths)
        preview = render_encoded_words(
            words,
            tilesets,
            start_x=args.start_x,
            start_y=args.start_y,
        )
        preview.save(args.output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
