"""チュートリアルの自動表示判定と設定永続化のテスト。

描画には依存せず、初回起動判定・表示済みフラグ保存・異常系フォールバックのみを検証する。

実行方法:
    python -m pytest core/test_tutorial.py
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from core.settings import get_tutorial_seen, set_tutorial_seen
from main import _should_show_tutorial


@contextmanager
def _settings_path(tmp_path: Path | None) -> Iterator[Path]:
    """Pytest と引数なし実行の両方で一時設定ファイルのパスを返す。"""
    if tmp_path is not None:
        yield tmp_path / "settings.json"
        return
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "settings.json"


def test_missing_settings_shows_tutorial(tmp_path: Path | None = None) -> None:
    """設定ファイルが無い場合は初回扱いになり、自動表示する。"""
    with _settings_path(tmp_path) as settings_path:
        assert _should_show_tutorial(get_tutorial_seen(settings_path))


def test_seen_tutorial_is_not_shown_automatically(tmp_path: Path | None = None) -> None:
    """tutorial_seen=True 保存後は自動表示しない。"""
    with _settings_path(tmp_path) as settings_path:
        set_tutorial_seen(True, settings_path)

        assert not _should_show_tutorial(get_tutorial_seen(settings_path))


def test_broken_settings_falls_back_to_first_launch(tmp_path: Path | None = None) -> None:
    """壊れた JSON でもクラッシュせず、初回扱いになる。"""
    with _settings_path(tmp_path) as settings_path:
        settings_path.write_text("{broken", encoding="utf-8")

        assert _should_show_tutorial(get_tutorial_seen(settings_path))
