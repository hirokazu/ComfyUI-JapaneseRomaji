"""
ComfyUI-JapaneseRomaji 変換テスト

使用方法:
    pip install fugashi unidic-lite pytest
    python -m pytest tests/test_conversion.py -v
"""

import pytest
from nodes import (
    _japanese_to_romaji_fugashi,
    _katakana_to_romaji,
    _convert_prompt,
    _convert_all_japanese,
)


# ============================================================
# カタカナ → ローマ字変換の単体テスト
# ============================================================

class TestKatakanaToRomaji:
    """_katakana_to_romaji: カタカナ→ヘボン式ローマ字"""

    def test_basic_vowels(self):
        assert _katakana_to_romaji("アイウエオ") == "aiueo"

    def test_basic_consonants(self):
        assert _katakana_to_romaji("カキクケコ") == "kakikukeko"
        assert _katakana_to_romaji("サシスセソ") == "sashisuseso"

    def test_long_vowel(self):
        assert _katakana_to_romaji("コーヒー") == "koohii"
        assert _katakana_to_romaji("トーキョー") == "tookyoo"

    def test_geminate_mid_word(self):
        """中間の促音: 次の子音を重ねる"""
        assert _katakana_to_romaji("ラッキー") == "rakkii"
        assert _katakana_to_romaji("サッカー") == "sakkaa"

    def test_geminate_end(self):
        """末尾の促音: tsu にフォールバック（Phase 3で修正）"""
        assert _katakana_to_romaji("ムカッ") == "mukatsu"

    def test_digraphs(self):
        """拗音"""
        assert _katakana_to_romaji("シャチョー") == "shachoo"
        assert _katakana_to_romaji("キョート") == "kyooto"

    def test_foreign_kana(self):
        """外来語用カタカナ"""
        assert _katakana_to_romaji("ファイル") == "fairu"
        assert _katakana_to_romaji("ティー") == "tii"

    def test_n_standalone(self):
        """ン"""
        assert _katakana_to_romaji("コンニチワ") == "konnichiwa"
        assert _katakana_to_romaji("ベンキョー") == "benkyoo"


# ============================================================
# fugashi エンジン: スペース制御テスト
# ============================================================

class TestFugashiSpacing:
    """名詞+助詞はスペース区切り、動詞+助動詞は結合"""

    def test_noun_particle_space(self):
        assert _japanese_to_romaji_fugashi("コーヒーの香りは") == "koohii no kaori wa"

    def test_noun_case_particle(self):
        assert _japanese_to_romaji_fugashi("東京に行きました") == "tookyoo ni ikimashita"

    def test_object_particle(self):
        assert _japanese_to_romaji_fugashi("お茶を飲みました") == "ocha o nomimashita"

    def test_subject_particle(self):
        assert _japanese_to_romaji_fugashi("天気がいいですね") == "tenki ga iidesu ne"

    def test_verb_auxiliary_join(self):
        assert _japanese_to_romaji_fugashi("食べています") == "tabeteimasu"

    def test_te_form_join(self):
        assert _japanese_to_romaji_fugashi("走っている") == "hashitteiru"

    def test_suru_verb_join(self):
        assert _japanese_to_romaji_fugashi("勉強しています") == "benkyooshiteimasu"
        assert _japanese_to_romaji_fugashi("散歩しました") == "sanposhimashita"

    def test_prefix_join(self):
        assert _japanese_to_romaji_fugashi("よろしくお願いします") == "yoroshiku onegaishimasu"

    def test_compound_noun_join(self):
        assert _japanese_to_romaji_fugashi("日本語を勉強しています") == "nippongo o benkyooshiteimasu"
        assert _japanese_to_romaji_fugashi("東京都に住んでいます") == "tookyooto ni sundeimasu"


# ============================================================
# fugashi エンジン: 促音テスト
# ============================================================

class TestFugashiGeminate:
    def test_geminate_te(self):
        assert _japanese_to_romaji_fugashi("向かっています") == "mukatteimasu"

    def test_geminate_te2(self):
        assert _japanese_to_romaji_fugashi("作ってください") == "tsukuttekudasai"


# ============================================================
# fugashi エンジン: 発音テスト（pron ベース）
# ============================================================

class TestFugashiPronunciation:
    """UniDic pron フィールドによる発音の正確性"""

    def test_wa_particle(self):
        """は(助詞) → pron=ワ → wa"""
        result = _japanese_to_romaji_fugashi("彼は学生です")
        assert " wa " in result

    def test_wo_particle(self):
        """を(助詞) → pron=オ → o"""
        result = _japanese_to_romaji_fugashi("私の心を落ち着かせます")
        assert " o " in result

    def test_konnichiwa(self):
        """こんにちは → pron=コンニチワ → konnichiwa"""
        assert _japanese_to_romaji_fugashi("こんにちは") == "konnichiwa"

    def test_long_vowel(self):
        """長音: pron の長音記号ーが母音繰り返しに"""
        result = _japanese_to_romaji_fugashi("コーヒー")
        assert result == "koohii"

    def test_arigatou(self):
        """ありがとう → pron=アリガトー → arigatoo"""
        assert _japanese_to_romaji_fugashi("ありがとうございます") == "arigatoo gozaimasu"

    def test_tokyo(self):
        """東京 → pron=トーキョー → tookyoo"""
        result = _japanese_to_romaji_fugashi("東京に行きました")
        assert result.startswith("tookyoo")


# ============================================================
# fugashi エンジン: 句読点テスト
# ============================================================

class TestFugashiPunctuation:
    def test_period_comma(self):
        result = _japanese_to_romaji_fugashi("コーヒーの香りは、私の心を落ち着かせます。")
        assert result.endswith(".")
        assert "," in result


# ============================================================
# プロンプト変換テスト（引用符内のみ）
# ============================================================

class TestConvertPrompt:
    def test_basic_prompt(self):
        result = _convert_prompt(
            'He says, "コーヒーの香りは、私の心を落ち着かせます。" The camera zooms in.',
            True, "fugashi"
        )
        assert result.startswith('He says, "')
        assert result.endswith('" The camera zooms in.')
        assert "Koohii no kaori wa" in result

    def test_english_translation_removal(self):
        result = _convert_prompt(
            'She says, "ありがとう！" (Thank you!)',
            True, "fugashi"
        )
        assert "(Thank you!)" not in result
        assert "Arigatoo!" in result

    def test_english_preserved(self):
        result = _convert_prompt(
            'The camera zooms in. He says, "こんにちは。" She smiles.',
            True, "fugashi"
        )
        assert result.startswith("The camera zooms in.")
        assert result.endswith("She smiles.")

    def test_no_japanese(self):
        prompt = 'He says, "Hello!" The camera zooms in.'
        result = _convert_prompt(prompt, True, "fugashi")
        assert result == prompt

    def test_keep_english_translations(self):
        result = _convert_prompt(
            'She says, "ありがとう！" (Thank you!)',
            False, "fugashi"
        )
        assert "(Thank you!)" in result


# ============================================================
# 全日本語変換テスト
# ============================================================

class TestConvertAllJapanese:
    def test_all_japanese(self):
        result = _convert_all_japanese("彼はコーヒーを飲む", False, "fugashi")
        # 日本語文字が残っていないこと
        assert not any('\u3040' <= c <= '\u9fff' for c in result)
