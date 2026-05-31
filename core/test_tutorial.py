"""チュートリアルの自動表示判定と設定永続化のテスト。

描画には依存せず、初回起動判定・表示済みフラグ保存・異常系フォールバックのみを検証する。

実行方法:
    python -m pytest core/test_tutorial.py
"""

from __future__ import annotations

from pathlib import Path

from core.settings import get_tutorial_seen, set_tutorial_seen
from main import _should_show_tutorial


def test_missing_settings_shows_tutorial(tmp_path: Path) -> None:
    """設定ファイルが無い場合は初回扱いになり、自動表示する。"""
    settings_path = tmp_path / "settings.json"

    assert _should_show_tutorial(get_tutorial_seen(settings_path))


def test_seen_tutorial_is_not_shown_automatically(tmp_path: Path) -> None:
    """tutorial_seen=True 保存後は自動表示しない。"""
    settings_path = tmp_path / "settings.json"

    set_tutorial_seen(True, settings_path)

    assert not _should_show_tutorial(get_tutorial_seen(settings_path))


def test_broken_settings_falls_back_to_first_launch(tmp_path: Path) -> None:
    """壊れた JSON でもクラッシュせず、初回扱いになる。"""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{broken", encoding="utf-8")

    assert _should_show_tutorial(get_tutorial_seen(settings_path))
