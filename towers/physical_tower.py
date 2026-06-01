"""物理タワー。

連射は遅いが単発で高火力。さらに敵の残 HP 割合に応じた追加ダメージ
（PHYSICAL_PIERCE_RATIO 倍まで）で、ボス級にも有効。
"""

from __future__ import annotations

from typing import ClassVar

import pygame as pg

from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.bullet import Bullet
from core.constants import (
    COLOR_PHYSICAL,
    PHYSICAL_COOLDOWN,
    PHYSICAL_DAMAGE,
    PHYSICAL_PIERCE_RATIO,
    PHYSICAL_RANGE,
)


class PhysicalTower(BaseTower):
    """物理タワー（高単発火力）。"""

    element: ClassVar[str] = "physical"
    image_name: ClassVar[str] = "tower_physical.png"

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        purchase_cost: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(
            pos=pos,
            range_=PHYSICAL_RANGE,
            damage=PHYSICAL_DAMAGE,
            cooldown=PHYSICAL_COOLDOWN,
            purchase_cost=purchase_cost,
            **kwargs,
        )

    def attack(self, target: BaseEnemy) -> Bullet | None:
        """残 HP 割合に応じた pierce ボーナスを加算して発射する。"""
        max_hp = target.get_max_hp() or 1
        remain_ratio = target.get_hp() / max_hp
        bonus = int(self._damage * PHYSICAL_PIERCE_RATIO * remain_ratio)
        return Bullet(pos=self._pos, target=target, damage=self._damage + bonus)

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_PHYSICAL, (x, y), 5)
