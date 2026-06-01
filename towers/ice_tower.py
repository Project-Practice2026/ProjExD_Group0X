"""氷タワー。

命中した敵にダメージを与えつつ、ICE_SLOW_FACTOR で ICE_SLOW_DURATION 秒間
速度を低下させる（重ね掛け時はより強い slow を優先）。
"""

from __future__ import annotations

from typing import ClassVar

import pygame as pg

from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.bullet import Bullet
from core.constants import (
    COLOR_ICE,
    ICE_COOLDOWN,
    ICE_DAMAGE,
    ICE_RANGE,
    ICE_SLOW_DURATION,
    ICE_SLOW_FACTOR,
)


class IceBullet(Bullet):
    """命中時に速度低下バフを与える弾。"""

    def __init__(
        self,
        pos: tuple[float, float],
        target: BaseEnemy,
        damage: int = ICE_DAMAGE,
        slow_factor: float = ICE_SLOW_FACTOR,
        slow_duration: float = ICE_SLOW_DURATION,
    ) -> None:
        super().__init__(pos=pos, target=target, damage=damage)
        self._slow_factor: float = max(0.0, min(1.0, float(slow_factor)))
        self._slow_duration: float = max(0.0, float(slow_duration))

    def get_slow_factor(self) -> float:
        """Slow_factor を返す。"""
        return self._slow_factor

    def get_slow_duration(self) -> float:
        """Slow_duration を返す。"""
        return self._slow_duration

    def check_hit(self, enemies: list[BaseEnemy] | None = None) -> bool:
        """Hit を判定する。"""
        _ = enemies
        hit = super().check_hit()
        if hit:
            # 親クラスが target.take_damage を呼んだ後に slow を追加適用
            self._target.apply_slow(self._slow_factor, self._slow_duration)
        return hit

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_ICE, (x, y), self.DEFAULT_RADIUS + 1)


class IceTower(BaseTower):
    """氷タワー（速度低下）。"""

    element: ClassVar[str] = "ice"
    image_name: ClassVar[str] = "tower_ice.png"

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        purchase_cost: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(
            pos=pos,
            range_=ICE_RANGE,
            damage=ICE_DAMAGE,
            cooldown=ICE_COOLDOWN,
            purchase_cost=purchase_cost,
            **kwargs,
        )

    def attack(self, target: BaseEnemy) -> Bullet | None:
        """攻撃を行う。"""
        return IceBullet(pos=self._pos, target=target, damage=self._damage)

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_ICE, (x, y), 5)
