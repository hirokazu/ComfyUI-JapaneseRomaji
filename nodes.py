"""
ComfyUI-JapaneseRomaji
======================
プロンプト内の引用符で囲まれた日本語テキストをヘボン式ローマ字に変換するノード。
LTX-2.3などの英語ベース動画生成モデルで日本語セリフを正確に発音させるために使用する。

変換エンジン:
  - "pykakasi"  : pykakasi 単体（依存が少ない・軽量）
  - "fugashi"   : fugashi + pykakasi ハイブリッド（高精度・推奨）
      fugashi (UniDic) で形態素解析 → 品詞情報でスペース制御
      → pykakasi でローマ字変換

依存ライブラリ:
  - pykakasi のみ使用する場合: pip install pykakasi
  - fugashi も使用する場合:    pip install pykakasi fugashi unidic-lite
"""

import re

# ============================================================
# 遅延インポート
# ============================================================
_kks = None
_tagger = None

def _get_kakasi():
    global _kks
    if _kks is None:
        try:
            import pykakasi
            _kks = pykakasi.kakasi()
        except ImportError:
            raise ImportError(
                "[JapaneseRomaji] pykakasi が見つかりません。\n"
                "インストール方法: pip install pykakasi"
            )
    return _kks

def _get_tagger():
    global _tagger
    if _tagger is None:
        try:
            import fugashi
            _tagger = fugashi.Tagger()
        except ImportError:
            raise ImportError(
                "[JapaneseRomaji] fugashi が見つかりません。\n"
                "インストール方法: pip install fugashi unidic-lite\n"
                "または engine='pykakasi' を使用してください。"
            )
    return _tagger


# ============================================================
# 定数
# ============================================================
JP_PUNCT_MAP = {
    '。': '. ', '、': ', ', '！': '! ', '？': '? ',
    '…': '... ', '「': '', '」': '', '『': '', '』': '',
    '・': ' ', '〜': '-', '～': '-', '\u3000': ' ',
}

# 内容語の品詞（チャンク先頭 → 前にスペース）
CONTENT_POS = {'名詞', '代名詞', '動詞', '形容詞', '形状詞', '副詞', '感動詞', '接続詞', '接頭辞'}
# 付属語の品詞（前のチャンクに結合）
PARTICLE_POS = {'助詞', '助動詞'}

# ヘボン式補正（pykakasi出力の後処理）
HEPBURN_FIX = [
    (r'\bha\b', 'wa'),   # は → wa
    (r'\bwo\b', 'o'),    # を → o
    (r'\bhe\b', 'e'),    # へ → e
]


def _apply_hepburn_fixes(text):
    for pattern, replacement in HEPBURN_FIX:
        text = re.sub(pattern, replacement, text)
    return text


# ============================================================
# pykakasi 単体エンジン
# ============================================================
def _japanese_to_romaji_pykakasi(text):
    kks = _get_kakasi()
    result = kks.convert(text)
    parts = []

    for item in result:
        orig = item['orig']
        hepburn = item['hepburn']
        if orig in JP_PUNCT_MAP:
            parts.append(('punct', JP_PUNCT_MAP[orig]))
        elif re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', orig):
            parts.append(('jp', hepburn if hepburn else orig))
        else:
            parts.append(('other', orig))

    out = ''
    for i, (kind, token) in enumerate(parts):
        if i == 0:
            out = token
            continue
        prev_kind = parts[i-1][0]
        if kind == 'punct':
            out = out.rstrip() + token
        elif kind == 'jp' and prev_kind == 'jp':
            out += ' ' + token
        else:
            out += token

    out = re.sub(r'  +', ' ', out)
    out = re.sub(r'\s+([.,!?])', r'\1', out)
    out = _apply_hepburn_fixes(out.strip())
    return out


# ============================================================
# fugashi + pykakasi ハイブリッドエンジン
# ============================================================
def _japanese_to_romaji_fugashi(text):
    """
    fugashi で形態素解析して品詞情報を取得し、
    pykakasi で各形態素をローマ字変換してから品詞に基づいてスペースを制御する。

    スペース制御の方針:
    - 内容語（名詞・動詞・形容詞等）の前にスペースを入れる
    - 助詞・助動詞は前の語に直結（スペースなし）
    - ただし前の語が 'n' で終わる場合はスペースを入れる（n'o 問題の回避）
    - 句読点は前後のスペースを制御
    """
    tagger = _get_tagger()
    kks = _get_kakasi()
    words = tagger(text)
    tokens = []  # (pos_class, romaji)

    for word in words:
        surface = word.surface
        if surface in JP_PUNCT_MAP:
            tokens.append(('punct', JP_PUNCT_MAP[surface]))
            continue

        try:
            pos1 = word.feature.pos1
            pron = word.feature.pron  # UniDicの発音フィールド（助詞の実際の発音を取得）
        except AttributeError:
            pos1 = 'unknown'
            pron = None

        if not re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', surface):
            tokens.append(('other', surface))
            continue

        # 助詞・助動詞はUniDicのpron（発音）フィールドを優先使用
        # これにより「は」→ワ(wa)、「を」→オ(o)、「へ」→エ(e) が正確に変換される
        if pos1 in PARTICLE_POS and pron and pron != '*':
            # カタカナの発音をpykakasiでローマ字変換
            converted = kks.convert(pron)
            romaji = ''.join(item['hepburn'] or item['orig'] for item in converted)
        else:
            # 内容語はsurfaceをpykakasiで変換
            converted = kks.convert(surface)
            romaji = ''.join(item['hepburn'] or item['orig'] for item in converted)

        # 句読点が混入した場合は除去
        romaji = ''.join(c for c in romaji if c not in JP_PUNCT_MAP)
        romaji = romaji.strip()
        if not romaji:
            continue

        if pos1 in CONTENT_POS:
            tokens.append(('content', romaji))
        elif pos1 in PARTICLE_POS:
            tokens.append(('particle', romaji))
        else:
            tokens.append(('other', romaji))

    # 結合
    result = ''
    for i, (kind, token) in enumerate(tokens):
        if not token:
            continue
        if i == 0:
            result = token
            continue

        if kind == 'punct':
            result = result.rstrip() + token
        elif kind == 'particle':
            # 前の語が 'n' で終わる場合はスペースを挿入（n'o 問題回避）
            stripped = result.rstrip()
            if stripped.endswith('n'):
                result = stripped + ' ' + token
            else:
                result = stripped + token
        elif kind in ('content', 'other'):
            result = result.rstrip() + ' ' + token

    result = re.sub(r'  +', ' ', result)
    result = re.sub(r'\s+([.,!?])', r'\1', result)
    result = _apply_hepburn_fixes(result.strip())
    return result


# ============================================================
# 共通: プロンプト変換
# ============================================================
def _convert_prompt(prompt, remove_translations, engine):
    """引用符内の日本語をローマ字に変換する"""
    if remove_translations:
        prompt = re.sub(r'\s*\([^)]*[a-zA-Z][^)]*\)', '', prompt)

    converter = (
        _japanese_to_romaji_fugashi
        if engine == 'fugashi'
        else _japanese_to_romaji_pykakasi
    )

    def replace_in_quotes(match):
        content = match.group(1)
        if not re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', content):
            return match.group(0)
        romaji = converter(content).strip()
        if romaji:
            romaji = romaji[0].upper() + romaji[1:]
        return f'"{romaji}"'

    result = re.sub(r'"((?:[^"\\]|\\.)*?)"', replace_in_quotes, prompt)
    result = re.sub(r'"\.\s*\.', '".', result)
    return result


def _convert_all_japanese(prompt, remove_translations, engine):
    """プロンプト内の全日本語をローマ字に変換する"""
    if remove_translations:
        prompt = re.sub(r'\s*\([^)]*[a-zA-Z][^)]*\)', '', prompt)

    converter = (
        _japanese_to_romaji_fugashi
        if engine == 'fugashi'
        else _japanese_to_romaji_pykakasi
    )

    def replace_jp(match):
        return converter(match.group(0))

    return re.sub(
        r'[\u3040-\u9fff\u30a0-\u30ff\u4e00-\u9fff]+(?:[^\u0000-\u007f]*[\u3040-\u9fff\u30a0-\u30ff\u4e00-\u9fff]+)*',
        replace_jp, prompt
    )


# ============================================================
# ComfyUI ノード定義
# ============================================================

class JapaneseRomajiConverter:
    """
    プロンプト内の引用符で囲まれた日本語テキストをヘボン式ローマ字に変換するノード。

    用途:
    - LTX-2.3などの英語ベース動画生成モデルで日本語セリフを正確に発音させる
    - 3段階プロンプトパイプラインのStage 2として使用

    動作:
    - 入力プロンプト内の "日本語テキスト" を "Romaji text" に変換
    - 英語部分は一切変更しない
    - 括弧内の英語翻訳 (English translation) をオプションで削除

    エンジン選択:
    - pykakasi: 軽量・依存が少ない（pip install pykakasi のみ）
    - fugashi:  高精度・推奨（pip install fugashi unidic-lite pykakasi）
                fugashiの品詞情報でスペース制御 + pykakasiでローマ字変換
    """

    ENGINES = ["fugashi", "pykakasi"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "変換対象のプロンプト。引用符(\"\")で囲まれた日本語テキストがローマ字に変換されます。"
                }),
                "engine": (cls.ENGINES, {
                    "default": "fugashi",
                    "tooltip": "fugashi: 高精度（推奨）/ pykakasi: 軽量"
                }),
            },
            "optional": {
                "remove_english_translations": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "括弧内の英語翻訳 (English translation) を削除するかどうか"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("converted_prompt",)
    FUNCTION = "convert"
    CATEGORY = "LTX-Video/Prompt"
    OUTPUT_NODE = False

    def convert(self, prompt, engine="fugashi", remove_english_translations=True):
        if not prompt or not prompt.strip():
            return (prompt,)
        if not re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', prompt):
            return (prompt,)
        converted = _convert_prompt(prompt, remove_english_translations, engine)
        return (converted,)


class JapaneseRomajiConverterAdvanced:
    """
    高度な設定が可能なローマ字変換ノード。
    変換前後のプレビューや、変換モードの選択が可能。
    """

    ENGINES = ["fugashi", "pykakasi"]
    CONVERSION_MODES = ["quotes_only", "all_japanese"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "変換対象のプロンプト"
                }),
                "engine": (cls.ENGINES, {
                    "default": "fugashi",
                    "tooltip": "fugashi: 高精度（推奨）/ pykakasi: 軽量"
                }),
                "conversion_mode": (cls.CONVERSION_MODES, {
                    "default": "quotes_only",
                    "tooltip": "quotes_only: 引用符内のみ変換 / all_japanese: 全日本語を変換"
                }),
                "remove_english_translations": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "括弧内の英語翻訳を削除するかどうか"
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("converted_prompt", "original_prompt")
    FUNCTION = "convert"
    CATEGORY = "LTX-Video/Prompt"
    OUTPUT_NODE = False

    def convert(self, prompt, engine="fugashi", conversion_mode="quotes_only",
                remove_english_translations=True):
        if not prompt or not prompt.strip():
            return (prompt, prompt)

        original = prompt

        if conversion_mode == "quotes_only":
            if not re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', prompt):
                return (prompt, original)
            converted = _convert_prompt(prompt, remove_english_translations, engine)
        else:  # all_japanese
            converted = _convert_all_japanese(prompt, remove_english_translations, engine)

        return (converted, original)


# ============================================================
# ノード登録
# ============================================================

NODE_CLASS_MAPPINGS = {
    "JapaneseRomajiConverter": JapaneseRomajiConverter,
    "JapaneseRomajiConverterAdvanced": JapaneseRomajiConverterAdvanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JapaneseRomajiConverter": "Japanese Romaji Converter",
    "JapaneseRomajiConverterAdvanced": "Japanese Romaji Converter (Advanced)",
}
