import json
import unittest

from kuten_inspector import (
    format_kuten,
    jis_x_0208_kuten,
    load_counter_from_char_counter_json,
    rows_from_counter,
)


class KutenInspectorTest(unittest.TestCase):
    def test_returns_jis_x_0208_kuten_for_hiragana(self):
        self.assertEqual(jis_x_0208_kuten("あ"), (4, 2))
        self.assertEqual(format_kuten((4, 2)), "04-02")

    def test_returns_none_for_non_jis_x_0208_character(self):
        self.assertIsNone(jis_x_0208_kuten("😀"))
        self.assertEqual(format_kuten(None), "")

    def test_builds_rows_with_font_coverage(self):
        rows = rows_from_counter({"あ": 2, "😀": 1}, {ord("あ")})

        self.assertEqual(
            rows,
            [
                {
                    "character": "あ",
                    "display": "あ",
                    "codepoint": "U+3042",
                    "count": 2,
                    "jis_x_0208_kuten": "04-02",
                    "in_jis_x_0208": True,
                    "in_font": True,
                },
                {
                    "character": "😀",
                    "display": "😀",
                    "codepoint": "U+1F600",
                    "count": 1,
                    "jis_x_0208_kuten": "",
                    "in_jis_x_0208": False,
                    "in_font": False,
                },
            ],
        )

    def test_loads_char_counter_json(self):
        # unittest does not provide tmp_path; keep this test independent of pytest.
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "chars.json"
            path.write_text(
                json.dumps(
                    {
                        "type_count": 1,
                        "characters": [
                            {"character": "あ", "display": "あ", "count": 2}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self.assertEqual(load_counter_from_char_counter_json(path), {"あ": 2})


if __name__ == "__main__":
    unittest.main()
