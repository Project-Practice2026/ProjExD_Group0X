"""プロジェクト共通のフォントローダ。"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

import pygame as pg

# GitHub CI環境（画面なし）での強制終了(exit code 139)を防ぐためのダミードライバ設定
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# フォントモジュールが未初期化の場合の安全装置
if not pg.font.get_init():
    pg.font.init()

FONT_DIR = Path(__file__).parent.parent / "assets" / "font"
FONT_DEFAULT = FONT_DIR / "NotoSansJP-Regular.ttf"


@cache
def get_font(size: int, path: Path = FONT_DEFAULT) -> pg.font.Font:
    """指定サイズのフォントを返す（同サイズはキャッシュ）。"""
    return pg.font.Font(str(path), size)
