"""HUD 基底クラス。

拠点HP、リソース、ウェーブ番号、世代番号などを画面に表示する。担当⑤の
ExtendedHud が継承する想定。
"""

from __future__ import annotations

import pygame as pg

from core.fonts import get_font

from .constants import (
    COLOR_HP_BAR_BG,
    COLOR_HP_BAR_FG,
    COLOR_TEXT,
    FORTRESS_MAX_HP,
    SCREEN_WIDTH,
)


class BaseHud:
    """HUD 基底クラス。"""

    MARGIN: int = 10
    LINE_HEIGHT: int = 22
    HP_BAR_WIDTH: int = 220
    HP_BAR_HEIGHT: int = 14
    FONT_SIZE: int = 18

    def __init__(self) -> None:
        # フォントが未初期化なら初期化（pg.init 済みなら no-op）
        if not pg.font.get_init():
            pg.font.init()
        self._font: pg.font.Font = get_font(self.FONT_SIZE)
        self._max_hp: int = FORTRESS_MAX_HP

    def set_max_hp(self, value: int) -> None:
        """Max_hp を設定する。"""
        self._max_hp = max(1, value)

    def draw(self, screen: pg.Surface, game_state: dict) -> None:
        """画面上部に各種情報を描画する。

        game_state の想定キー：
            - core_hp (int): 拠点の現在HP
            - core_max_hp (int): 拠点の最大HP（省略可）
            - resource (int): 現在の共有リソース
            - wave (int): 現在のウェーブ番号
            - generation (int): 進化AIの世代番号
        """
        core_hp = int(game_state.get("core_hp", 0))
        max_hp = int(game_state.get("core_max_hp", self._max_hp))
        resource = int(game_state.get("resource", 0))
        wave = int(game_state.get("wave", 0))
        generation = int(game_state.get("generation", 0))

        # 拠点HPバー（左上）
        bar_x, bar_y = self.MARGIN, self.MARGIN
        pg.draw.rect(
            screen,
            COLOR_HP_BAR_BG,
            (bar_x, bar_y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT),
        )
        ratio = core_hp / max_hp if max_hp > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))
        fg_width = int(self.HP_BAR_WIDTH * ratio)
        if fg_width > 0:
            pg.draw.rect(
                screen,
                COLOR_HP_BAR_FG,
                (bar_x, bar_y, fg_width, self.HP_BAR_HEIGHT),
            )

        # ラベル
        self._blit_text(
            screen,
            f"Core HP {core_hp}/{max_hp}",
            (bar_x + self.HP_BAR_WIDTH + 8, bar_y - 2),
        )

        # 右上：リソース / ウェーブ / 世代
        right_x = SCREEN_WIDTH - self.MARGIN
        line_y = self.MARGIN
        for text in (
            f"Resource: {resource}",
            f"Wave: {wave}",
            f"Generation: {generation}",
        ):
            self._blit_text_right(screen, text, (right_x, line_y))
            line_y += self.LINE_HEIGHT

    def _blit_text(
        self,
        screen: pg.Surface,
        text: str,
        pos: tuple[int, int],
    ) -> None:
        surface = self._font.render(text, True, COLOR_TEXT)
        screen.blit(surface, pos)

    def _blit_text_right(
        self,
        screen: pg.Surface,
        text: str,
        right_top: tuple[int, int],
    ) -> None:
        surface = self._font.render(text, True, COLOR_TEXT)
        rect = surface.get_rect(topright=right_top)
        screen.blit(surface, rect)
