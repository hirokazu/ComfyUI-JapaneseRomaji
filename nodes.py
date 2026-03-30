"""
ComfyUI-JapaneseRomaji
======================
プロンプト内の引用符で囲まれた日本語テキストをヘボン式ローマ字に変換するノード。
LTX-2.3などの英語ベース動画生成モデルで日本語セリフを正確に発音させるために使用する。

変換エンジン:
  - "fugashi"   : fugashi (UniDic) で形態素解析 → pron(発音)フィールドから
                   自前のカタカナ→ローマ字変換でヘボン式に変換（推奨）
  - "pykakasi"  : pykakasi 単体（フォールバック用・軽量）

依存ライブラリ:
  - fugashi エンジン: pip install fugashi unidic-lite
  - pykakasi エンジン: pip install pykakasi
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

# ヘボン式補正（pykakasi単体エンジン用）
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
# カタカナ → ヘボン式ローマ字変換
# ============================================================

# 拗音（2文字組）— 先にマッチさせる
_KANA_DIGRAPHS = {
    'キャ': 'kya', 'キュ': 'kyu', 'キョ': 'kyo',
    'シャ': 'sha', 'シュ': 'shu', 'ショ': 'sho',
    'チャ': 'cha', 'チュ': 'chu', 'チョ': 'cho',
    'ニャ': 'nya', 'ニュ': 'nyu', 'ニョ': 'nyo',
    'ヒャ': 'hya', 'ヒュ': 'hyu', 'ヒョ': 'hyo',
    'ミャ': 'mya', 'ミュ': 'myu', 'ミョ': 'myo',
    'リャ': 'rya', 'リュ': 'ryu', 'リョ': 'ryo',
    'ギャ': 'gya', 'ギュ': 'gyu', 'ギョ': 'gyo',
    'ジャ': 'ja',  'ジュ': 'ju',  'ジョ': 'jo',
    'ヂャ': 'ja',  'ヂュ': 'ju',  'ヂョ': 'jo',
    'ビャ': 'bya', 'ビュ': 'byu', 'ビョ': 'byo',
    'ピャ': 'pya', 'ピュ': 'pyu', 'ピョ': 'pyo',
    # 外来語
    'ティ': 'ti',  'ディ': 'di',  'トゥ': 'tu',  'ドゥ': 'du',
    'ファ': 'fa',  'フィ': 'fi',  'フェ': 'fe',  'フォ': 'fo', 'フュ': 'fyu',
    'ウィ': 'wi',  'ウェ': 'we',  'ウォ': 'wo',
    'ヴァ': 'va',  'ヴィ': 'vi',  'ヴェ': 've',  'ヴォ': 'vo',
    'ツァ': 'tsa', 'ツィ': 'tsi', 'ツェ': 'tse', 'ツォ': 'tso',
    'シェ': 'she', 'ジェ': 'je',  'チェ': 'che',
    'テュ': 'tyu', 'デュ': 'dyu',
}

# 単独カタカナ
_KANA_SINGLES = {
    'ア': 'a',  'イ': 'i',  'ウ': 'u',  'エ': 'e',  'オ': 'o',
    'カ': 'ka', 'キ': 'ki', 'ク': 'ku', 'ケ': 'ke', 'コ': 'ko',
    'サ': 'sa', 'シ': 'shi', 'ス': 'su', 'セ': 'se', 'ソ': 'so',
    'タ': 'ta', 'チ': 'chi', 'ツ': 'tsu', 'テ': 'te', 'ト': 'to',
    'ナ': 'na', 'ニ': 'ni', 'ヌ': 'nu', 'ネ': 'ne', 'ノ': 'no',
    'ハ': 'ha', 'ヒ': 'hi', 'フ': 'fu', 'ヘ': 'he', 'ホ': 'ho',
    'マ': 'ma', 'ミ': 'mi', 'ム': 'mu', 'メ': 'me', 'モ': 'mo',
    'ヤ': 'ya',              'ユ': 'yu',              'ヨ': 'yo',
    'ラ': 'ra', 'リ': 'ri', 'ル': 'ru', 'レ': 're', 'ロ': 'ro',
    'ワ': 'wa',                                       'ヲ': 'o',
    'ン': 'n',
    'ガ': 'ga', 'ギ': 'gi', 'グ': 'gu', 'ゲ': 'ge', 'ゴ': 'go',
    'ザ': 'za', 'ジ': 'ji', 'ズ': 'zu', 'ゼ': 'ze', 'ゾ': 'zo',
    'ダ': 'da', 'ヂ': 'ji', 'ヅ': 'zu', 'デ': 'de', 'ド': 'do',
    'バ': 'ba', 'ビ': 'bi', 'ブ': 'bu', 'ベ': 'be', 'ボ': 'bo',
    'パ': 'pa', 'ピ': 'pi', 'プ': 'pu', 'ペ': 'pe', 'ポ': 'po',
    'ヴ': 'vu',
    # 小書きカタカナ（単独出現時）
    'ァ': 'a',  'ィ': 'i',  'ゥ': 'u',  'ェ': 'e',  'ォ': 'o',
    'ャ': 'ya',              'ュ': 'yu',              'ョ': 'yo',
    'ヮ': 'wa',
}


def _katakana_to_romaji(text):
    """カタカナ文字列をヘボン式ローマ字に変換する。"""
    parts = []
    i = 0
    while i < len(text):
        # 2文字拗音を先にチェック
        if i + 1 < len(text):
            digraph = text[i:i + 2]
            if digraph in _KANA_DIGRAPHS:
                parts.append(_KANA_DIGRAPHS[digraph])
                i += 2
                continue

        ch = text[i]

        if ch == 'ー':
            # 長音: 直前のローマ字の末尾母音を繰り返す
            if parts:
                for c in reversed(parts[-1]):
                    if c in 'aiueo':
                        parts.append(c)
                        break
            i += 1
        elif ch == 'ッ':
            # 促音: 次の音の先頭子音を重ねる
            next_rom = ''
            if i + 1 < len(text):
                if i + 2 < len(text) and text[i + 1:i + 3] in _KANA_DIGRAPHS:
                    next_rom = _KANA_DIGRAPHS[text[i + 1:i + 3]]
                elif text[i + 1] in _KANA_SINGLES:
                    next_rom = _KANA_SINGLES[text[i + 1]]
            if next_rom and next_rom[0] not in 'aiueon':
                parts.append(next_rom[0])
            else:
                # 末尾のッ（形態素境界） → tsu を出力し Phase 3 で修正
                parts.append('tsu')
            i += 1
        elif ch in _KANA_SINGLES:
            parts.append(_KANA_SINGLES[ch])
            i += 1
        else:
            # 非カタカナ（句読点等）はそのまま
            parts.append(ch)
            i += 1

    return ''.join(parts)


# ============================================================
# スペース制御
# ============================================================

def _should_join_to_prev(pos1, pos2, prev_spacing='space', prev_pos1='',
                         prev_is_sahen=False, surface=''):
    """
    品詞情報から、このトークンを前のトークンにスペースなしで結合すべきか判定する。

    結合する品詞:
    - 助動詞（ます、です、た、ない、だ等）
    - 接尾辞（さ、的、化等）
    - 接続助詞（て、で、ながら、ば等 — 動詞活用の一部）
    - 非自立動詞・形容詞（ている/てある等の補助用法）
      ただし、前のトークンが結合型（join/prefix）か、
      サ変可能名詞（勉強+する、散歩+する等）の場合のみ。
    - 1文字名詞で前が名詞の場合（複合語: 日本+語、東京+都等）
    """
    if pos1 == '助動詞':
        return True
    if pos1 == '接尾辞':
        return True
    if pos1 == '助詞' and pos2 == '接続助詞':
        return True
    if pos1 in ('動詞', '形容詞') and pos2 == '非自立可能':
        return prev_spacing in ('join', 'prefix') or prev_is_sahen
    if pos1 == '名詞' and prev_pos1 == '名詞' and len(surface) == 1:
        return True
    return False


# ============================================================
# pykakasi 単体エンジン（フォールバック）
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
# fugashi エンジン（推奨）
# ============================================================
def _japanese_to_romaji_fugashi(text):
    """
    fugashi (UniDic) で形態素解析し、全トークンの pron (発音) フィールドから
    自前のカタカナ→ローマ字変換を行う。品詞情報でスペースを制御する。

    pykakasi 不要。UniDic の pron が実際の発音を正確に反映するため、
    は→wa, を→o, こんにちは→konnichiwa 等が自然に処理される。
    """
    tagger = _get_tagger()
    words = tagger(text)

    # Phase 1: 各形態素をローマ字に変換し、スペース種別を付与
    tokens = []    # [(romaji, spacing, has_geminate)]
    prev_spacing = 'space'
    prev_pos1 = ''
    prev_is_sahen = False

    for word in words:
        surface = word.surface

        # 句読点
        if surface in JP_PUNCT_MAP:
            tokens.append((JP_PUNCT_MAP[surface], 'punct', False))
            continue

        # 品詞情報を取得
        pos1 = pos2 = pos3 = ''
        pron = None
        try:
            pos1 = word.feature.pos1
            pos2 = word.feature.pos2
            pos3 = word.feature.pos3
            pron = word.feature.pron
        except AttributeError:
            pass

        # 非日本語テキストはそのまま
        if not re.search(r'[\u3040-\u9fff\u30a0-\u30ff]', surface):
            tokens.append((surface, 'other', False))
            prev_spacing = 'other'
            continue

        # ローマ字変換: UniDic pron → カタカナ → ローマ字
        if pron and pron != '*':
            romaji = _katakana_to_romaji(pron)
        else:
            # pron が無い場合はsurfaceをそのまま出力（通常発生しない）
            romaji = surface

        romaji = romaji.strip()
        if not romaji:
            continue

        # pron が「ッ」で終わる = 促音が形態素末尾にある
        has_geminate = bool(pron and pron.endswith('ッ'))

        # スペース種別を判定
        if pos1 == '接頭辞':
            spacing = 'prefix'
        elif _should_join_to_prev(pos1, pos2, prev_spacing, prev_pos1,
                                  prev_is_sahen, surface):
            spacing = 'join'
        else:
            spacing = 'space'

        tokens.append((romaji, spacing, has_geminate))
        prev_spacing = spacing
        prev_pos1 = pos1
        prev_is_sahen = (pos3 == 'サ変可能')

    # Phase 2: 接頭辞の後続トークンを結合に変更
    for i in range(len(tokens) - 1):
        if tokens[i][1] == 'prefix':
            tokens[i] = (tokens[i][0], 'space', tokens[i][2])
            for j in range(i + 1, len(tokens)):
                if tokens[j][1] != 'punct':
                    tokens[j] = (tokens[j][0], 'join', tokens[j][2])
                    break

    # Phase 3: 促音処理 — 形態素末尾の "tsu" を次のトークンの先頭子音で置換
    # 例: 向かっ(mukatsu) + て(te) → mukatte
    for i in range(len(tokens) - 1):
        romaji, spacing, has_gem = tokens[i]
        if has_gem and romaji.endswith('tsu'):
            for j in range(i + 1, len(tokens)):
                next_romaji, next_sp, _ = tokens[j]
                if next_sp == 'punct':
                    continue
                if next_romaji and next_romaji[0].isalpha():
                    tokens[i] = (romaji[:-3] + next_romaji[0], spacing, False)
                break

    # Phase 4: トークンを結合
    result = ''
    for romaji, spacing, _ in tokens:
        if not romaji:
            continue
        if not result:
            result = romaji
            continue

        if spacing == 'punct':
            result = result.rstrip() + romaji
        elif spacing == 'join':
            result = result.rstrip() + romaji
        else:
            result = result.rstrip() + ' ' + romaji

    result = re.sub(r'  +', ' ', result)
    result = re.sub(r'\s+([.,!?])', r'\1', result)
    return result.strip()


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

    エンジン選択:
    - fugashi: 高精度・推奨（pip install fugashi unidic-lite）
    - pykakasi: 軽量・フォールバック（pip install pykakasi）
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
