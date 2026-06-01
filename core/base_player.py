"""プレイヤー基底クラス。

Builder（建築役）と Fighter（前線役）が継承する共通基底。
"""

from __future__ import annotations

from pathlib import Path

import pygame as pg

from .constants import (
    PLAYER_MAX_HP,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


class BasePlayer:
    """プレイヤー基底クラス。"""

    DEFAULT_RADIUS: int = 14
    DEFAULT_SPEED: float = 220.0

    image_name: str = "player_fighter.png"
    image_size: tuple[int, int] = (32, 32)

    def __init__(
        self,
        player_id: int,
        pos: tuple[float, float] | None = None,
        max_hp: int = PLAYER_MAX_HP,
    ) -> None:
        if pos is None:
            pos = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self._player_id: int = player_id
        self._pos: tuple[float, float] = pos
        self._max_hp: int = max_hp
        self._hp: int = max_hp
        self._speed: float = self.DEFAULT_SPEED

        image = pg.image.load(Path("assets") / "fig" / self.image_name)
        self.image = pg.transform.scale(image, self.image_size)
        self.rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    def get_player_id(self) -> int:
        """ネットワーク入力の紐付けに使うプレイヤー ID を返す。"""
        return self._player_id

    def get_pos(self) -> tuple[float, float]:
        """現在座標を返す。"""
        return self._pos

    def set_pos(self, x: float, y: float) -> None:
        """現在座標を設定する。"""
        self._pos = (x, y)
        self.rect.center = (int(x), int(y))

    def get_hp(self) -> int:
        """現在 HP を返す。"""
        return self._hp

    def set_hp(self, value: int) -> None:
        """HP を 0 以上最大 HP 以下に丸めて設定する。"""
        self._hp = max(0, min(self._max_hp, value))

    def update(self, input_state: dict) -> None:
        """入力に応じて状態を更新する。

        入力フォーマットは network/net_protocol.py のメッセージと整合性を保つ
        想定。基底では move 指示の dx/dy を 1 フレームぶん反映するに留める。
        """
        dt = float(input_state.get("dt", 0.0))
        dx = float(input_state.get("dx", 0.0))
        dy = float(input_state.get("dy", 0.0))
        x, y = self._pos
        new_x = max(0.0, min(float(SCREEN_WIDTH), x + dx * self._speed * dt))
        new_y = max(0.0, min(float(SCREEN_HEIGHT), y + dy * self._speed * dt))
        self._pos = (new_x, new_y)
        self.rect.center = (int(new_x), int(new_y))

    def draw(self, screen: pg.Surface) -> None:
        """プレイヤーを画像で描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)
