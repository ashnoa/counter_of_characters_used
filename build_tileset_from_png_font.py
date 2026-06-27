#!/usr/bin/env python3
"""Build an 8x8 PNG tileset by copying glyphs from a kuten-ordered PNG font."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FONT_COLUMNS = 94
FONT_ROWS = 94
TILE_WIDTH = 8
TILE_HEIGHT = 8
TILESET_COLUMNS = 16
TILESET_ROWS = 24
TILESET_TILE_COUNT = TILESET_COLUMNS * TILESET_ROWS
TILESET_WIDTH = TILE_WIDTH * TILESET_COLUMNS
TILESET_HEIGHT = TILE_HEIGHT * TILESET_ROWS
BACKGROUND_COLOR = (255, 255, 255)
CONTROL_TOP_COLOR = (191, 191, 191)
CONTROL_BOTTOM_COLOR = (128, 128, 128)
FIXED_SYMBOL_TILE_INDEX = 254
FIXED_SYMBOL_KUTEN = (2, 7)
RESERVED_BLANK_TILE_INDEXES = {255}


@dataclass(frozen=True)
class GlyphPlacement:
    character: str
    kuten: tuple[int, int]
    bank: int
    index: int


@dataclass(frozen=True)
class FontSpec:
    name: str
    glyph_width: int
    glyph_height: int
    default_offset_x: int
    default_offset_y: int


K6X8_SPEC = FontSpec(
    name="k6x8",
    glyph_width=6,
    glyph_height=8,
    default_offset_x=1,
    default_offset_y=1,
)
MISAKI_SPEC = FontSpec(
    name="misaki",
    glyph_width=8,
    glyph_height=8,
    default_offset_x=0,
    default_offset_y=0,
)


def parse_kuten(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d{1,2})-(\d{1,2})\s*", value)
    if match is None:
        raise ValueError(f"invalid kuten value: {value!r}")

    ku = int(match.group(1))
    ten = int(match.group(2))
    if not 1 <= ku <= FONT_ROWS:
        raise ValueError(f"kuten ku must be between 1 and {FONT_ROWS}: {ku}")
    if not 1 <= ten <= FONT_COLUMNS:
        raise ValueError(f"kuten ten must be between 1 and {FONT_COLUMNS}: {ten}")
    return ku, ten


def source_box_for_kuten(
    kuten: tuple[int, int],
    *,
    font_spec: FontSpec = K6X8_SPEC,
) -> tuple[int, int, int, int]:
    ku, ten = kuten
    left = (ten - 1) * font_spec.glyph_width
    top = (ku - 1) * font_spec.glyph_height
    return (left, top, left + font_spec.glyph_width, top + font_spec.glyph_height)


def destination_position_for_index(
    index: int,
    *,
    offset_x: int = 1,
    offset_y: int = 1,
) -> tuple[int, int]:
    if not 0 <= index < TILESET_TILE_COUNT:
        raise ValueError(f"index must be between 0 and 383: {index}")

    tile_x = (index % TILESET_COLUMNS) * TILE_WIDTH
    tile_y = (index // TILESET_COLUMNS) * TILE_HEIGHT
    return tile_x + offset_x, tile_y + offset_y


def is_reserved_blank_tile(index: int) -> bool:
    return index in RESERVED_BLANK_TILE_INDEXES


def tile_origin_for_index(index: int) -> tuple[int, int]:
    if not 0 <= index < TILESET_TILE_COUNT:
        raise ValueError(f"index must be between 0 and 383: {index}")

    return (index % TILESET_COLUMNS) * TILE_WIDTH, (index // TILESET_COLUMNS) * TILE_HEIGHT


def load_placements(path: Path, *, bank: int | None) -> list[GlyphPlacement]:
    placements: list[GlyphPlacement] = []
    used_indexes: set[tuple[int, int]] = set()

    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required_fields = {"character", "jis_x_0208_kuten", "bank", "index"}
        if reader.fieldnames is None or not required_fields.issubset(reader.fieldnames):
            fields = ", ".join(sorted(required_fields))
            raise ValueError(f"mapping CSV must contain columns: {fields}")

        for line_number, row in enumerate(reader, start=2):
            character = row["character"]
            if len(character) != 1:
                raise ValueError(
                    f"line {line_number}: character must be exactly one character"
                )

            kuten_text = row["jis_x_0208_kuten"]
            if not kuten_text:
                raise ValueError(f"line {line_number}: jis_x_0208_kuten is empty")

            try:
                row_bank = int(row["bank"], 0)
                index = int(row["index"], 0)
            except ValueError as exc:
                raise ValueError(
                    f"line {line_number}: bank and index must be integers"
                ) from exc

            if bank is not None and row_bank != bank:
                continue

            key = (row_bank, index)
            if key in used_indexes:
                raise ValueError(
                    f"line {line_number}: duplicate index {index} in bank {row_bank}"
                )
            used_indexes.add(key)

            placements.append(
                GlyphPlacement(
                    character=character,
                    kuten=parse_kuten(kuten_text),
                    bank=row_bank,
                    index=index,
                )
            )

    if bank is not None and not placements:
        raise ValueError(f"no characters found for bank {bank}")

    return placements


def group_placements_by_bank(
    placements: list[GlyphPlacement],
) -> dict[int, list[GlyphPlacement]]:
    grouped: dict[int, list[GlyphPlacement]] = {}
    for placement in placements:
        grouped.setdefault(placement.bank, []).append(placement)
    return dict(sorted(grouped.items()))


def output_path_for_bank(output: Path, *, bank: int, multiple_banks: bool) -> Path:
    if not multiple_banks:
        return output
    return output.with_name(f"{output.stem}_bank{bank}{output.suffix}")


def load_pillow() -> Any:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Pillow is required to build PNG tilesets. "
            "Install it with: python3 -m pip install -r requirements.txt"
        ) from exc
    return Image


def background_color_for_image(image: Any) -> Any:
    return BACKGROUND_COLOR


def fill_control_tile(tileset: Any) -> None:
    left, top = tile_origin_for_index(TILESET_TILE_COUNT - 1)
    tileset.paste(CONTROL_TOP_COLOR, (left, top, left + TILE_WIDTH, top + 4))
    tileset.paste(
        CONTROL_BOTTOM_COLOR,
        (left, top + 4, left + TILE_WIDTH, top + TILE_HEIGHT),
    )


def paste_glyph(
    tileset: Any,
    font_image: Any,
    kuten: tuple[int, int],
    index: int,
    *,
    font_spec: FontSpec,
    offset_x: int,
    offset_y: int,
) -> None:
    glyph = font_image.crop(source_box_for_kuten(kuten, font_spec=font_spec))
    tileset.paste(
        glyph,
        destination_position_for_index(
            index,
            offset_x=offset_x,
            offset_y=offset_y,
        ),
    )


def fill_fixed_symbol_tile(
    tileset: Any,
    font_image: Any,
    *,
    font_spec: FontSpec,
    offset_x: int,
    offset_y: int,
) -> None:
    paste_glyph(
        tileset,
        font_image,
        FIXED_SYMBOL_KUTEN,
        FIXED_SYMBOL_TILE_INDEX,
        font_spec=font_spec,
        offset_x=offset_x,
        offset_y=offset_y,
    )


def build_tileset(
    font_png: Path,
    placements: list[GlyphPlacement],
    output_png: Path,
    *,
    font_spec: FontSpec = K6X8_SPEC,
    offset_x: int | None = None,
    offset_y: int | None = None,
) -> None:
    Image = load_pillow()
    font_image = Image.open(font_png)
    expected_size = (
        font_spec.glyph_width * FONT_COLUMNS,
        font_spec.glyph_height * FONT_ROWS,
    )
    if font_image.size != expected_size:
        raise ValueError(
            f"{font_spec.name} font PNG must be {expected_size[0]}x{expected_size[1]} px: "
            f"got {font_image.size[0]}x{font_image.size[1]} px"
        )

    if offset_x is None:
        offset_x = font_spec.default_offset_x
    if offset_y is None:
        offset_y = font_spec.default_offset_y

    font_image = font_image.convert("RGB")
    tileset = Image.new(
        "RGB",
        (TILESET_WIDTH, TILESET_HEIGHT),
        BACKGROUND_COLOR,
    )
    for placement in placements:
        if is_reserved_blank_tile(placement.index):
            continue
        paste_glyph(
            tileset,
            font_image,
            placement.kuten,
            placement.index,
            font_spec=font_spec,
            offset_x=offset_x,
            offset_y=offset_y,
        )

    fill_fixed_symbol_tile(
        tileset,
        font_image,
        font_spec=font_spec,
        offset_x=offset_x,
        offset_y=offset_y,
    )
    fill_control_tile(tileset)
    tileset.save(output_png)


def warn_if_tileset_is_full(
    placements: list[GlyphPlacement],
    *,
    bank: int,
    stream: Any = sys.stderr,
) -> None:
    if len(placements) >= TILESET_TILE_COUNT:
        print(
            f"warning: bank {bank} uses {len(placements)} tiles; "
            "the last tile should remain empty for control use",
            file=stream,
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a 128x192 PNG tileset from a kuten PNG font.",
    )
    parser.add_argument(
        "--font-png",
        type=Path,
        required=True,
        help="Source PNG font image. k6x8 expects 564x752 px; --misaki expects 752x752 px.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        required=True,
        help="CSV containing character, jis_x_0208_kuten, bank, and index columns.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help=(
            "Output 128x192 PNG tileset path. If multiple banks are built, "
            "the bank number is added before the suffix."
        ),
    )
    parser.add_argument(
        "--bank",
        type=int,
        default=None,
        help="Bank to build. If omitted, all banks are built as separate PNG files.",
    )
    parser.add_argument(
        "--misaki",
        action="store_true",
        help="Use 8x8 Misaki Font PNG layout instead of the default 6x8 k6x8 layout.",
    )
    parser.add_argument(
        "--offset-x",
        type=int,
        default=None,
        help="Glyph X offset inside each 8x8 tile. Defaults to 1 for k6x8 and 0 for --misaki.",
    )
    parser.add_argument(
        "--offset-y",
        type=int,
        default=None,
        help="Glyph Y offset inside each 8x8 tile. Defaults to 1 for k6x8 and 0 for --misaki.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        font_spec = MISAKI_SPEC if args.misaki else K6X8_SPEC
        placements = load_placements(args.mapping, bank=args.bank)
        grouped = group_placements_by_bank(placements)
        if not grouped:
            raise ValueError("no characters found")

        multiple_banks = len(grouped) > 1
        for bank, bank_placements in grouped.items():
            warn_if_tileset_is_full(bank_placements, bank=bank)
            build_tileset(
                args.font_png,
                bank_placements,
                output_path_for_bank(args.output, bank=bank, multiple_banks=multiple_banks),
                font_spec=font_spec,
                offset_x=args.offset_x,
                offset_y=args.offset_y,
            )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
