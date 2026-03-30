# ComfyUI Japanese Romaji Converter

LTX-2.3などの英語ベース動画生成モデルで**日本語セリフを正確に発音させる**ためのComfyUIカスタムノードです。

プロンプト内の引用符 `"..."` で囲まれた日本語テキストを、**ヘボン式ローマ字**に自動変換します。英語部分は一切変更しません。

## 変換例

```
入力: He says, "コーヒーの香りは、私の心を落ち着かせます。" The camera zooms in.
出力: He says, "Koohii no kaori wa, watashi no kokoro wo ochitsukasemasu." The camera zooms in.
```

括弧内の英語翻訳も自動削除します：

```
入力: She says, "ありがとう！" (Thank you!)
出力: She says, "Arigatou!"
```

## インストール

### 方法1: ComfyUI Manager（推奨）
ComfyUI Managerから `ComfyUI Japanese Romaji Converter` を検索してインストール。

### 方法2: 手動インストール
```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/your-username/ComfyUI-JapaneseRomaji
pip install pykakasi
```

## ノード一覧

### Japanese Romaji Converter（標準版）
シンプルな変換ノード。3段階パイプラインのStage 2として使用。

| 入力 | 型 | 説明 |
|:---|:---|:---|
| `prompt` | STRING | 変換対象のプロンプト |
| `remove_english_translations` | BOOLEAN | 括弧内の英語翻訳を削除するか（デフォルト: True） |

| 出力 | 型 | 説明 |
|:---|:---|:---|
| `converted_prompt` | STRING | 変換後のプロンプト |

### Japanese Romaji Converter (Advanced)（高度版）
変換モードの選択や、変換前後の比較が可能な高度版ノード。

| 入力 | 型 | 説明 |
|:---|:---|:---|
| `prompt` | STRING | 変換対象のプロンプト |
| `conversion_mode` | COMBO | `quotes_only`（引用符内のみ）/ `all_japanese`（全日本語） |
| `remove_english_translations` | BOOLEAN | 括弧内の英語翻訳を削除するか |
| `capitalize_first` | BOOLEAN | ローマ字の先頭を大文字にするか |

| 出力 | 型 | 説明 |
|:---|:---|:---|
| `converted_prompt` | STRING | 変換後のプロンプト |
| `original_prompt` | STRING | 変換前の元のプロンプト（デバッグ用） |

## 推奨ワークフロー（LTX-2.3 3段階パイプライン）

```
[ユーザー入力（日本語）]
        ↓
[Stage 1: TextGenerateGemma3Prompt]
  シナリオ生成（セリフは日本語のまま引用符で出力）
        ↓
[Stage 2: Japanese Romaji Converter]  ← このノード
  "日本語セリフ" → "Romaji speech"
  括弧内の英語翻訳を削除
        ↓
[Stage 3: TextGenerateLTX2Prompt]
  LTX-2.3専用フォーマットに最終整形
        ↓
[LTX-2.3 動画生成]
```

## 変換精度について

| ケース | 変換例 | 備考 |
|:---|:---|:---|
| 一般的な文 | `こんにちは` → `Konnichiwa` | ✅ |
| 長音 | `コーヒー` → `Koohii` | ✅ |
| 助詞は/を/へ | `は` → `wa`, `を` → `o`, `へ` → `e` | ✅ ヘボン式補正済み |
| 句読点 | `。` → `.`, `、` → `,`, `！` → `!` | ✅ |
| 複合語 | `ものづくり` → `monozukuri` | ✅ |

## 依存ライブラリ

- [pykakasi](https://github.com/miurahr/pykakasi) >= 2.2.1

## ライセンス

MIT License
