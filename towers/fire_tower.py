"""火炎タワー。

着弾点を中心に半径 FIRE_EXPLOSION_RADIUS 内の敵全員にダメージを与える。
中心からの距離に応じた減衰係数 FIRE_EXPLOSION_FALLOFF を掛ける。
"""

from __future__ import annotations

import math
from typing import ClassVar

import pygame as pg

from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.bullet import Bullet
from core.constants import (
    COLOR_FIRE,
    FIRE_COOLDOWN,
    FIRE_DAMAGE,
    FIRE_EXPLOSION_FALLOFF,
    FIRE_EXPLOSION_RADIUS,
    FIRE_RANGE,
)


class FireBullet(Bullet):
    """着弾時に範囲ダメージを与える弾。"""

    def __init__(
        self,
        pos: tuple[float, float],
        target: BaseEnemy,
        damage: int = FIRE_DAMAGE,
        explosion_radius: float = FIRE_EXPLOSION_RADIUS,
        falloff: float = FIRE_EXPLOSION_FALLOFF,
    ) -> None:
        super().__init__(pos=pos, target=target, damage=damage)
        self._explosion_radius: float = max(0.0, float(explosion_radius))
        self._falloff: float = max(0.0, min(1.0, float(falloff)))
        self._explosion_drawn_at: tuple[float, float] | None = None
        self._explosion_remaining: float = 0.0

    def get_explosion_radius(self) -> float:
        """Explosion_radius を返す。"""
        return self._explosion_radius

    def update(self, dt: float = 1.0 / 60.0) -> None:
        # 爆発描画のタイマーを進める
        """1 フレーム分の状態を更新する。"""
        if self._explosion_remaining > 0.0:
            self._explosion_remaining = max(0.0, self._explosion_remaining - dt)
        super().update(dt)

    def check_hit(self, enemies: list[BaseEnemy] | None = None) -> bool:
        """Hit を判定する。"""
        if self._consumed:
            return False
        if self._target.is_dead():
            self._consumed = True
            return False
        tx, ty = self._target.get_pos()
        x, y = self._pos
        if math.hypot(tx - x, ty - y) > self.HIT_DISTANCE:
            return False

        # 爆発：射程内の敵全員にダメージ（距離による減衰）
        center = (tx, ty)
        if enemies:
            for enemy in enemies:
                if enemy.is_dead():
                    continue
                ex, ey = enemy.get_pos()
                dist = math.hypot(ex - center[0], ey - center[1])
                if dist > self._explosion_radius:
                    continue
                # 距離 0 で 100%、半径端で _falloff 倍まで線形に減衰
                ratio = 1.0 if self._explosion_radius == 0 else dist / self._explosion_radius
                damage_mult = 1.0 - (1.0 - self._falloff) * ratio
                damage = max(1, int(self._damage * damage_mult))
                enemy.take_damage(damage)
        else:
            # 範囲効果が使えないフォールバック：単体ダメージ
            self._target.take_damage(self._damage)

        self._consumed = True
        # 爆発の可視化を 0.1 秒だけ残すためのフラグ（is_consumed で考慮）
        self._explosion_drawn_at = center
        self._explosion_remaining = 0.1
        return True

    def is_consumed(self) -> bool:
        # 爆発の演出が残っているうちは "consumed" にしない
        """Consumed かどうかを返す。"""
        if self._consumed and self._explosion_remaining > 0:
            return False
        return self._consumed

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        if self._explosion_remaining > 0 and self._explosion_drawn_at is not None:
            cx, cy = int(self._explosion_drawn_at[0]), int(self._explosion_drawn_at[1])
            pg.draw.circle(
                screen,
                COLOR_FIRE,
                (cx, cy),
                int(self._explosion_radius),
                width=2,
            )
            return
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_FIRE, (x, y), self.DEFAULT_RADIUS + 1)


class FireTower(BaseTower):
    """火炎タワー（範囲ダメージ）。"""

    element: ClassVar[str] = "fire"
    image_name: ClassVar[str] = "tower_fire.png"

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        purchase_cost: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(
            pos=pos,
            range_=FIRE_RANGE,
            damage=FIRE_DAMAGE,
            cooldown=FIRE_COOLDOWN,
            purchase_cost=purchase_cost,
            **kwargs,
        )

    def attack(self, target: BaseEnemy) -> Bullet | None:
        """攻撃を行う。"""
        return FireBullet(pos=self._pos, target=target, damage=self._damage)

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        # 中央に小さな火マーク（属性識別用）
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_FIRE, (x, y), 5)
