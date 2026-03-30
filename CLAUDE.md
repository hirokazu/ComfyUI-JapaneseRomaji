# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI custom node plugin that converts Japanese text to Hepburn romaji in prompts. Primary use case: enabling English-based video generation models (e.g. LTX-2.3) to pronounce Japanese dialogue correctly.

## Architecture

Single-file node implementation in `nodes.py`. Two ComfyUI nodes registered via `__init__.py`:

- **JapaneseRomajiConverter** — converts Japanese inside quoted strings (`"..."`) to romaji
- **JapaneseRomajiConverterAdvanced** — adds `all_japanese` mode (converts all Japanese, not just quoted) and outputs original prompt for comparison

Two conversion engines, selected at runtime:
- **fugashi** (recommended): fugashi (UniDic) for morphological analysis. Uses UniDic's `pron` (pronunciation) field for all tokens, then `_katakana_to_romaji()` for katakana→romaji conversion. pykakasi is NOT used. Spacing is controlled by `_should_join_to_prev()` based on pos1/pos2/pos3 from UniDic.
- **pykakasi** (fallback): pykakasi only, for environments where fugashi can't be installed. Uses `_apply_hepburn_fixes()` for particle corrections.

Key conversion pipeline: `_convert_prompt()` (quotes-only) / `_convert_all_japanese()` → engine function (`_japanese_to_romaji_fugashi` or `_japanese_to_romaji_pykakasi`).

The fugashi engine processes in 4 phases:
1. Tokenize, convert each morpheme's `pron` → katakana → romaji, assign spacing type
2. Prefix propagation (接頭辞 → next token joins)
3. Geminate consonant (促音ッ) repair across morpheme boundaries
4. Token joining with spacing rules

Both pykakasi and fugashi are lazy-loaded singletons (`_kks`, `_tagger`).

## Dependencies

- Required: `fugashi`, `unidic-lite`
- Optional (for pykakasi fallback engine): `pykakasi>=2.2.1`
- Install: `pip install fugashi unidic-lite`

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/test_conversion.py::TestFugashiSpacing::test_noun_particle_space -v
```

Nodes are registered under category `LTX-Video/Prompt`.

## Language

README and code comments are in Japanese. Node tooltips are in Japanese. The codebase targets Japanese-speaking ComfyUI users.
