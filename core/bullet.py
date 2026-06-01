"""弾クラス。

BaseTower から発射され、対象の BaseEnemy に向かって移動する。命中で HP を削る。
"""

from __future__ import annotations

import math

import pygame as pg

from .base_enemy import BaseEnemy
from .constants import BULLET_SPEED, TOWER_BASE_DAMAGE
from .image_cache import load_scaled_image

BULLET_SIZE: tuple[int, int] = (8, 8)


class Bullet:
    """単一の弾。"""

    DEFAULT_RADIUS: int = 4
    HIT_DISTANCE: float = 10.0

    image_name: str = "bullet.png"
    image_size: tuple[int, int] = BULLET_SIZE

    def __init__(
        self,
        pos: tuple[float, float],
        target: BaseEnemy,
        speed: float = BULLET_SPEED,
        damage: int = TOWER_BASE_DAMAGE,
    ) -> None:
        self._pos: tuple[float, float] = pos
        self._target: BaseEnemy = target
        self._speed: float = speed
        self._damage: int = damage
        self._consumed: bool = False

        self.image: pg.Surface = load_scaled_image(self.image_name, self.image_size)
        self.rect: pg.Rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    def get_pos(self) -> tuple[float, float]:
        """Pos を返す。"""
        return self._pos

    def get_damage(self) -> int:
        """Damage を返す。"""
        return self._damage

    def get_target(self) -> BaseEnemy:
        """Target を返す。"""
        return self._target

    def is_consumed(self) -> bool:
        """命中済み、または対象が消滅して残骸になった場合 True。"""
        return self._consumed

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """対象方向へ移動する。"""
        if self._consumed:
            return
        if self._target.is_dead():
            self._consumed = True
            return
        tx, ty = self._target.get_pos()
        x, y = self._pos
        vx, vy = tx - x, ty - y
        dist = math.hypot(vx, vy)
        if dist == 0:
            self._consumed = True
            return
        step = self._speed * dt
        if step >= dist:
            self._pos = (tx, ty)
        else:
            self._pos = (x + vx / dist * step, y + vy / dist * step)

        self.rect.center = (int(self._pos[0]), int(self._pos[1]))

    def check_hit(self, enemies: list[BaseEnemy] | None = None) -> bool:
        """命中判定。命中したら対象にダメージを与え、True を返す。

        Args:
            enemies: 周囲を巻き込む派生 Bullet（FireBullet 等）が利用する全敵リスト。
                基底実装では使用しないが、World からは常に渡される。
        """
        _ = enemies
        if self._consumed:
            return False
        if self._target.is_dead():
            self._consumed = True
            return False
        tx, ty = self._target.get_pos()
        x, y = self._pos
        if math.hypot(tx - x, ty - y) <= self.HIT_DISTANCE:
            self._target.take_damage(self._damage)
            self._consumed = True
            return True
        return False

    def draw(self, screen: pg.Surface) -> None:
        """弾を画像で描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)
