# counter_of_characters_used

ゲームボーイで日本語のテキストを動的に表示するためのデータを準備するCLIツール群です。

テキストファイルの中で使われている文字の種類と出現回数を数え、JIS X 0208区点の確認、bank/indexの割り当て、テキストの16bit値列への変換、PNGフォントからのタイルセット生成までを行います。

例えば `あいうえおあ` という内容のファイルでは、使われている文字の種類は `あ`, `い`, `う`, `え`, `お` の5種類として扱います。

## Requirements

- Python 3.10+
- `char_counter.py` は追加の外部ライブラリ不要です
- `kuten_inspector.py` でフォント収録状況を調べる場合は `fonttools` が必要です
- PNGフォントからタイルセットを作る場合は `Pillow` が必要です

```bash
python3 -m pip install -r requirements.txt
```

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

## JIS X 0208区点とフォント収録状況を調べる

`kuten_inspector.py` を使うと、文字ごとのJIS X 0208区点と、指定したフォントにそのUnicodeコードポイントが収録されているかを確認できます。

テキストファイルを直接調べる:

```bash
python3 kuten_inspector.py --text path/to/file.txt --font path/to/font.ttf
```

`char_counter.py --json` の結果を使う:

```bash
python3 char_counter.py --json path/to/file.txt > chars.json
python3 kuten_inspector.py --char-counter-json chars.json --font path/to/font.ttf
```

デフォルトはCSV出力です。

```csv
character,display,codepoint,count,jis_x_0208_kuten,in_jis_x_0208,in_font
あ,あ,U+3042,2,04-02,True,True
```

JSONで出力する:

```bash
python3 kuten_inspector.py --text path/to/file.txt --font path/to/font.ttf --json
```

TTCフォントコレクションの2番目以降のフォントを調べる場合は `--font-number` を指定します。

```bash
python3 kuten_inspector.py --text path/to/file.txt --font path/to/font.ttc --font-number 1
```

注意点:

- 区点はフォント固有の値ではなく、JIS X 0208上の位置です。
- フォントについては、Unicode `cmap` にその文字のコードポイントが含まれるかを確認します。
- JIS X 0208にない文字の `jis_x_0208_kuten` は空欄になります。

## bank/index CSVを使ってテキストをdw列に変換する

`encode_text_to_words.py` は、`character`, `bank`, `index` 列を持つCSVを使って、テキストをGame Boy向けの16bit値の列に変換します。

`kuten_inspector.py` のCSV出力から `character`, `bank`, `index` などを含むCSVを作るには、先に `add_bank_index_columns.py` を使います。

```bash
python3 add_bank_index_columns.py \
  --input path/to/kuten.csv \
  --output path/to/char_and_text.csv
```

追加される列:

- `mode`: 全行 `8000`
- `bank`: `1` 始まり。使用可能なindexを使い切ったら1増えます。
- `index`: `0` 始まり。最大 `382` まで使い、`255` は空白タイルとしてスキップします。
- `check`: 全行 `1`
- 改行文字の行、つまり `character` が実改行、または `display` が `<LF>` の行は出力CSVに含めず、indexも割り当てません。

```bash
python3 encode_text_to_words.py \
  --text path/to/diary.txt \
  --mapping path/to/char_and_text.csv
```

ファイルへ出力する:

```bash
python3 encode_text_to_words.py \
  --text path/to/diary.txt \
  --mapping path/to/char_and_text.csv \
  --output path/to/output.asm
```

変換ルール:

- 各文字は `(bank << 12) | index` の16bit値に変換します。
- `bank` は上位4bit、`index` は下位12bitとして扱います。
- テキスト中の改行 `\n` は `$FFFE` に変換します。
- テキスト末尾にはEOFとして `$FFFF` を追加します。
- 出力は `dw $0000, $0001` の形式です。

## PNGフォントからタイルセットを作る

`build_tileset_from_png_font.py` は、564x752 pxのPNGフォントからJIS X 0208区点に対応する6x8 pxの文字画像を切り出し、128x192 pxのタイルセットPNGへ配置します。

フォントデータは、6×8ドット日本語フォント「k6x8」のPNG形式を前提としています。

- 配布ページ: https://littlelimit.net/k6x8.htm
- k6x8 は6×8ドットの日本語ビットマップフォントで、JIS 第一・第二水準をサポートしています。

入力CSVには `character`, `jis_x_0208_kuten`, `bank`, `index` 列が必要です。`kuten_inspector.py` のCSV出力に `bank`, `index` を追加した `char_and_text.csv` をそのまま使えます。

```bash
python3 build_tileset_from_png_font.py \
  --font-png path/to/font.png \
  --mapping path/to/char_and_text.csv \
  --output path/to/tileset.png
```

配置ルール:

- PNGフォントは1文字6x8 px、横方向が点、縦方向が区です。
- 区点 `04-02` は、横 `(2 - 1) * 6`、縦 `(4 - 1) * 8` の位置から6x8 pxを切り出します。
- タイルセットは16列x24行の8x8タイルです。
- `index` はタイル番号として扱い、左上から右方向、次に下方向へ進みます。
- glyphは各8x8タイル内の `(1, 1)` へ貼り付けます。
- 背景色は白 `#ffffff` です。
- `index 255`、つまり0オリジンで15行15列のタイルは常に背景色だけの空白タイルとして扱います。
- 最後のタイルは制御用として、上半分を `#bfbfbf`、下半分を `#808080` で塗ります。
- 複数bankがCSVに含まれる場合は、bankごとに `tileset_bank1.png` のような別ファイルを出力します。
- `--bank 1` のように指定すると、そのbankだけを `--output` のパスへ出力します。
- 貼り付け位置は `--offset-x`, `--offset-y` で変更できます。

## Test

```bash
python3 -m unittest discover -v
```
