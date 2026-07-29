import tempfile
import unittest
from pathlib import Path

from render_encoded_text import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    EOF_WORD,
    NEWLINE_WORD,
    TILESET_HEIGHT,
    TILESET_WIDTH,
    load_pillow,
    load_tilesets,
    parse_asm_words,
    parse_tileset_arguments,
    render_encoded_words,
    source_box_for_index,
)


class RenderEncodedTextTest(unittest.TestCase):
    def test_parses_generated_asm_format(self):
        self.assertEqual(
            parse_asm_words("dw $1000, $1001 ; text\nDW $FFFE, $FFFF\n"),
            [0x1000, 0x1001, NEWLINE_WORD, EOF_WORD],
        )

    def test_rejects_invalid_asm_and_missing_eof(self):
        with self.assertRaisesRegex(ValueError, "line 1"):
            parse_asm_words("db $1000\n")
        with self.assertRaisesRegex(ValueError, "invalid"):
            parse_asm_words("dw 0x1000, $FFFF\n")
        with self.assertRaisesRegex(ValueError, "does not contain"):
            parse_asm_words("dw $1000\n")
        with self.assertRaisesRegex(ValueError, "after"):
            parse_asm_words("dw $FFFF, $1000\n")

    def test_parses_repeated_bank_tileset_arguments(self):
        self.assertEqual(
            parse_tileset_arguments(["1=one.png", "0x2=two.png"]),
            {1: Path("one.png"), 2: Path("two.png")},
        )

    def test_rejects_invalid_or_duplicate_tileset_arguments(self):
        for values in (["one.png"], ["16=one.png"], ["1=a.png", "1=b.png"]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                parse_tileset_arguments(values)

    def test_source_box_uses_sixteen_column_tileset(self):
        self.assertEqual(source_box_for_index(0), (0, 0, 8, 8))
        self.assertEqual(source_box_for_index(17), (8, 8, 16, 16))
        with self.assertRaises(ValueError):
            source_box_for_index(384)

    def test_renders_banks_newline_and_default_start_position(self):
        Image = load_pillow()
        bank1 = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white")
        bank2 = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white")
        bank1.paste((255, 0, 0), source_box_for_index(0))
        bank1.paste((0, 255, 0), source_box_for_index(1))
        bank2.paste((0, 0, 255), source_box_for_index(0))

        preview = render_encoded_words(
            [0x1000, 0x1001, NEWLINE_WORD, 0x2000, EOF_WORD],
            {1: bank1, 2: bank2},
        )

        self.assertEqual(preview.size, (CANVAS_WIDTH, CANVAS_HEIGHT))
        self.assertEqual(preview.getpixel((8, 8)), (255, 0, 0))
        self.assertEqual(preview.getpixel((16, 8)), (0, 255, 0))
        self.assertEqual(preview.getpixel((8, 16)), (0, 0, 255))
        self.assertEqual(preview.getpixel((0, 0)), (255, 255, 255))

    def test_renders_at_custom_start_position(self):
        Image = load_pillow()
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), (10, 20, 30))

        preview = render_encoded_words(
            [0x1000, EOF_WORD],
            {1: tileset},
            start_x=3,
            start_y=4,
        )

        self.assertEqual(preview.getpixel((24, 32)), (10, 20, 30))

    def test_rejects_missing_bank_invalid_index_and_canvas_overflow(self):
        Image = load_pillow()
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white")

        with self.assertRaisesRegex(ValueError, "missing tileset bank 2"):
            render_encoded_words([0x2000, EOF_WORD], {1: tileset})
        with self.assertRaisesRegex(ValueError, "invalid tileset index 384"):
            render_encoded_words([0x1180, EOF_WORD], {1: tileset})
        with self.assertRaisesRegex(ValueError, "does not fit"):
            render_encoded_words(
                [0x1000, 0x1000, EOF_WORD],
                {1: tileset},
                start_x=31,
            )
        with self.assertRaisesRegex(ValueError, "start_x"):
            render_encoded_words([EOF_WORD], {1: tileset}, start_x=32)

    def test_allows_newline_to_move_past_canvas_when_no_glyph_follows(self):
        Image = load_pillow()
        tileset = Image.new("RGB", (TILESET_WIDTH, TILESET_HEIGHT), "white")

        preview = render_encoded_words(
            [NEWLINE_WORD, EOF_WORD],
            {1: tileset},
            start_y=31,
        )

        self.assertEqual(preview.size, (CANVAS_WIDTH, CANVAS_HEIGHT))

    def test_load_tilesets_validates_dimensions(self):
        Image = load_pillow()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tileset.png"
            Image.new("RGB", (8, 8), "white").save(path)

            with self.assertRaisesRegex(ValueError, "128x192"):
                load_tilesets({1: path})


if __name__ == "__main__":
    unittest.main()
