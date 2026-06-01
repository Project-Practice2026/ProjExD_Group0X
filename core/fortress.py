"""拠点（コア）クラス。

HP を持ち、敵が接触するとダメージを受ける。HP が 0 になると敗北判定。
"""

from __future__ import annotations

import pygame as pg

from .constants import (
    COLOR_HP_BAR_BG,
    COLOR_HP_BAR_FG,
    FORTRESS_MAX_HP,
    FORTRESS_X_RATIO,
    FORTRESS_Y_RATIO,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from .image_cache import load_scaled_image


class Fortress:
    """拠点クラス。"""

    DEFAULT_RADIUS: int = 36
    HP_BAR_WIDTH: int = 80
    HP_BAR_HEIGHT: int = 6
    HP_BAR_OFFSET: int = 12

    image_name: str = "fortress.png"
    image_size: tuple[int, int] = (96, 96)

    def __init__(
        self,
        pos: tuple[float, float] | None = None,
        max_hp: int = FORTRESS_MAX_HP,
    ) -> None:
        if pos is None:
            pos = (SCREEN_WIDTH * FORTRESS_X_RATIO, SCREEN_HEIGHT * FORTRESS_Y_RATIO)
        self._pos: tuple[float, float] = pos
        self._max_hp: int = max_hp
        self._hp: int = max_hp

        self.image: pg.Surface = load_scaled_image(self.image_name, self.image_size)
        self.rect: pg.Rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    def get_pos(self) -> tuple[float, float]:
        """Pos を返す。"""
        return self._pos

    def set_pos(self, x: float, y: float) -> None:
        """Pos を設定する。"""
        self._pos = (x, y)
        self.rect.center = (int(x), int(y))

    def get_hp(self) -> int:
        """Hp を返す。"""
        return self._hp

    def set_hp(self, value: int) -> None:
        """Hp を設定する。"""
        self._hp = max(0, min(self._max_hp, value))

    def get_max_hp(self) -> int:
        """Max_hp を返す。"""
        return self._max_hp

    def take_damage(self, amount: int) -> None:
        """ダメージを受ける（HP は 0 未満にならない）。"""
        if amount <= 0:
            return
        self._hp = max(0, self._hp - amount)

    def is_destroyed(self) -> bool:
        """Destroyed かどうかを返す。"""
        return self._hp <= 0

    def draw(self, screen: pg.Surface) -> None:
        """拠点画像と HP バーを描画する。"""
        x, y = int(self._pos[0]), int(self._pos[1])
        self.rect.center = (x, y)
        screen.blit(self.image, self.rect)

        # HP バー
        bar_x = x - self.HP_BAR_WIDTH // 2
        bar_y = y - self.image_size[1] // 2 - self.HP_BAR_OFFSET
        pg.draw.rect(
            screen,
            COLOR_HP_BAR_BG,
            (bar_x, bar_y, self.HP_BAR_WIDTH, self.HP_BAR_HEIGHT),
        )
        ratio = self._hp / self._max_hp if self._max_hp > 0 else 0.0
        fg_width = int(self.HP_BAR_WIDTH * ratio)
        if fg_width > 0:
            pg.draw.rect(
                screen,
                COLOR_HP_BAR_FG,
                (bar_x, bar_y, fg_width, self.HP_BAR_HEIGHT),
            )
