# counter_of_characters_used

テキストファイルの中で使われている文字の種類と、それぞれの出現回数を数えるCLIツールです。

例えば `あいうえおあ` という内容のファイルでは、使われている文字の種類は `あ`, `い`, `う`, `え`, `お` の5種類として扱います。

## Requirements

- Python 3.10+
- 追加の外部ライブラリは不要です

## Usage

基本的な使い方:

```bash
python3 char_counter.py path/to/file.txt
```

出力例:

```text
種類数: 5
文字	回数
あ	2
い	1
う	1
え	1
お	1
```

デフォルトでは、スペース、タブ、改行などの空白文字も集計対象に含めます。空白文字は見やすいように `<SPACE>`, `<TAB>`, `<LF>`, `<CR>` のように表示されます。

## Options

### 空白文字を除外する

```bash
python3 char_counter.py --exclude-whitespace path/to/file.txt
```

`str.isspace()` が真になる文字を集計から除外します。

### 文字コードを指定する

```bash
python3 char_counter.py --encoding shift_jis path/to/file.txt
```

指定しない場合は `utf-8` で読み込みます。

### CSVで出力する

```bash
python3 char_counter.py --csv path/to/file.txt
```

出力例:

```csv
character,display,count
あ,あ,2
い,い,1
```

列の意味:

- `character`: 実際の文字
- `display`: 表示用の文字。改行などは `<LF>` のように表示
- `count`: 出現回数

### JSONで出力する

```bash
python3 char_counter.py --json path/to/file.txt
```

出力例:

```json
{
  "type_count": 2,
  "characters": [
    {
      "character": "あ",
      "display": "あ",
      "count": 2
    },
    {
      "character": "\n",
      "display": "<LF>",
      "count": 1
    }
  ]
}
```

`--csv` と `--json` は同時に指定できません。

## Counting Rules

- Pythonの通常のUnicode文字単位で数えます。
- 文字の並び順は、ファイル内で最初に出現した順です。
- Unicode正規化や、絵文字の結合文字列を見た目上の1文字として扱う処理は行いません。

## Test

```bash
python3 -m unittest discover -v
```
