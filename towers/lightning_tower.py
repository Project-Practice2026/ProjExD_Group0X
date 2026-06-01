"""雷タワー。

最初の敵から半径 LIGHTNING_CHAIN_RADIUS 内の別の敵へ最大 LIGHTNING_CHAIN_COUNT
体までチェインしてダメージを与える。チェインごとにダメージ係数
LIGHTNING_CHAIN_FALLOFF が掛かる。視覚は LightningBolt（短時間のライン）。
"""

from __future__ import annotations

import math
from typing import ClassVar

import pygame as pg

from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.bullet import Bullet
from core.constants import (
    COLOR_LIGHTNING,
    LIGHTNING_CHAIN_COUNT,
    LIGHTNING_CHAIN_FALLOFF,
    LIGHTNING_CHAIN_RADIUS,
    LIGHTNING_COOLDOWN,
    LIGHTNING_DAMAGE,
    LIGHTNING_RANGE,
    LIGHTNING_VISUAL_DURATION,
)


class LightningBolt(Bullet):
    """稲妻の視覚のみを担う「弾」。ダメージは生成時に既に適用済み。

    Bullet を継承する理由は World._bullets リストでまとめて update/draw できる
    ようにするため。check_hit は何もしない（ダメージは LightningTower.update
    で即時適用済み）。
    """

    def __init__(
        self,
        chain_points: list[tuple[float, float]],
        duration: float = LIGHTNING_VISUAL_DURATION,
    ) -> None:
        # ダミー target が必要なため、最後の点に向かう非実体 Bullet とする
        anchor = chain_points[-1] if chain_points else (0.0, 0.0)
        super().__init__(
            pos=chain_points[0] if chain_points else (0.0, 0.0),
            target=_NullTarget(anchor),
            damage=0,
        )
        self._chain_points: list[tuple[float, float]] = list(chain_points)
        self._remaining: float = max(0.0, float(duration))

    def get_chain_points(self) -> list[tuple[float, float]]:
        """Chain_points を返す。"""
        return list(self._chain_points)

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """1 フレーム分の状態を更新する。"""
        self._remaining = max(0.0, self._remaining - dt)
        if self._remaining <= 0.0:
            self._consumed = True

    def check_hit(self, enemies: list[BaseEnemy] | None = None) -> bool:
        """Hit を判定する。"""
        _ = enemies
        return False  # ダメージは生成時に適用済み

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        if len(self._chain_points) < 2:
            return
        for prev, nxt in zip(self._chain_points[:-1], self._chain_points[1:], strict=True):
            pg.draw.line(
                screen,
                COLOR_LIGHTNING,
                (int(prev[0]), int(prev[1])),
                (int(nxt[0]), int(nxt[1])),
                width=3,
            )


class _NullTarget:
    """LightningBolt の Bullet 親クラスを満足させるためのダミー target。"""

    def __init__(self, pos: tuple[float, float]) -> None:
        self._pos = pos

    def get_pos(self) -> tuple[float, float]:
        """Pos を返す。"""
        return self._pos

    def is_dead(self) -> bool:
        """Dead かどうかを返す。"""
        return True

    def take_damage(self, amount: int) -> None:
        """Take_damage を行う。"""
        _ = amount


class LightningTower(BaseTower):
    """雷タワー（チェイン攻撃）。"""

    element: ClassVar[str] = "lightning"
    image_name: ClassVar[str] = "tower_lightning.png"

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        purchase_cost: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(
            pos=pos,
            range_=LIGHTNING_RANGE,
            damage=LIGHTNING_DAMAGE,
            cooldown=LIGHTNING_COOLDOWN,
            purchase_cost=purchase_cost,
            **kwargs,
        )

    def update(
        self,
        enemies: list[BaseEnemy],
        now: float | None = None,
    ) -> list[Bullet]:
        """通常の update をオーバーライド。チェインダメージを即時適用し、視覚 Bolt を返す。"""
        if now is None:
            now = pg.time.get_ticks() / 1000.0
        if now - self._last_shot_tick < self._cooldown:
            return []
        primary = self.find_target(enemies)
        if primary is None:
            return []

        # チェイン処理
        hit_chain: list[BaseEnemy] = [primary]
        damage_now = float(self._damage)
        primary.take_damage(int(damage_now))
        for _ in range(LIGHTNING_CHAIN_COUNT - 1):
            last = hit_chain[-1]
            nxt = self._find_chain_target(last, enemies, exclude=hit_chain)
            if nxt is None:
                break
            damage_now *= LIGHTNING_CHAIN_FALLOFF
            nxt.take_damage(max(1, int(damage_now)))
            hit_chain.append(nxt)

        self._last_shot_tick = now
        # 視覚：タワー位置→primary→チェインの順に結ぶ
        points: list[tuple[float, float]] = [self._pos]
        points.extend(e.get_pos() for e in hit_chain)
        return [LightningBolt(chain_points=points)]

    def _find_chain_target(
        self,
        center: BaseEnemy,
        enemies: list[BaseEnemy],
        exclude: list[BaseEnemy],
    ) -> BaseEnemy | None:
        cx, cy = center.get_pos()
        best: BaseEnemy | None = None
        best_dist = LIGHTNING_CHAIN_RADIUS
        for e in enemies:
            if e in exclude or e.is_dead():
                continue
            ex, ey = e.get_pos()
            d = math.hypot(ex - cx, ey - cy)
            if d <= best_dist:
                best_dist = d
                best = e
        return best

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.circle(screen, COLOR_LIGHTNING, (x, y), 5)
