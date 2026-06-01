"""タワー基底クラス。

派生クラス（炎・氷・雷・物理）は担当③が実装する。基底は射程内の敵を見つけ
クールタイム経過ごとに弾を撃つ最小実装。
"""

from __future__ import annotations

import math
from pathlib import Path

import pygame as pg

from .base_enemy import BaseEnemy
from .bullet import Bullet
from .constants import (
    TOWER_BASE_COOLDOWN,
    TOWER_BASE_DAMAGE,
    TOWER_BASE_RANGE,
)


class BaseTower:
    """タワー基底クラス。"""

    DEFAULT_RADIUS: int = 16
    RANGE_RING_ALPHA: int = 40

    image_name: str = "tower_physical.png"
    image_size: tuple[int, int] = (48, 48)

    def __init__(  # noqa: PLR0913 - タワー初期化に必要なパラメータをすべて kwarg 化するため許容
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        range_: float = TOWER_BASE_RANGE,
        damage: int = TOWER_BASE_DAMAGE,
        cooldown: float | None = None,
        fire_cooldown: float | None = None,
        purchase_cost: int = 0,
    ) -> None:
        if cooldown is None:
            cooldown = fire_cooldown if fire_cooldown is not None else TOWER_BASE_COOLDOWN
        self._pos: tuple[float, float] = pos
        self._range: float = range_
        self._damage: int = damage
        self._cooldown: float = cooldown
        self._last_shot_tick: float = -cooldown  # 起動直後から撃てるように
        # アップグレードシステム用（担当③）
        self._level: int = 1
        self._total_invested: int = max(0, int(purchase_cost))

        image = pg.image.load(Path("assets") / "fig" / self.image_name)
        self.image = pg.transform.scale(image, self.image_size)
        self.rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    @property
    def damage(self) -> int:
        """Damage を行う。"""
        return self._damage

    @damage.setter
    def damage(self, value: int) -> None:
        """Damage を行う。"""
        self.set_damage(value)

    @property
    def range(self) -> float:
        """Range を行う。"""
        return self._range

    @range.setter  # noqa: A003
    def range(self, value: float) -> None:
        """Range を行う。"""
        self.set_range(value)

    @property
    def cooldown(self) -> float:
        """Cooldown を行う。"""
        return self._cooldown

    @cooldown.setter
    def cooldown(self, value: float) -> None:
        """Cooldown を行う。"""
        self.set_cooldown(value)

    @property
    def fire_cooldown(self) -> float:
        """Fire_cooldown を行う。"""
        return self._cooldown

    @fire_cooldown.setter
    def fire_cooldown(self, value: float) -> None:
        """Fire_cooldown を行う。"""
        self.set_cooldown(value)

    def get_pos(self) -> tuple[float, float]:
        """Pos を返す。"""
        return self._pos

    def set_pos(self, x: float, y: float) -> None:
        """Pos を設定する。"""
        self._pos = (x, y)
        self.rect.center = (int(x), int(y))

    def get_range(self) -> float:
        """Range を返す。"""
        return self._range

    def set_range(self, value: float) -> None:
        """Range を設定する。"""
        self._range = max(0.0, value)

    def get_damage(self) -> int:
        """Damage を返す。"""
        return self._damage

    def set_damage(self, value: int) -> None:
        """Damage を設定する。"""
        self._damage = max(0, value)

    def get_cooldown(self) -> float:
        """Cooldown を返す。"""
        return self._cooldown

    def set_cooldown(self, value: float) -> None:
        """Cooldown を設定する。"""
        self._cooldown = max(0.0, value)

    # --- upgrade hooks (担当③) ---

    def get_level(self) -> int:
        """Level を返す。"""
        return self._level

    def set_level(self, value: int) -> None:
        """Level を設定する。"""
        self._level = max(1, int(value))

    def get_total_invested(self) -> int:
        """Total_invested を返す。"""
        return self._total_invested

    def add_invested(self, amount: int) -> None:
        """Invested を追加する。"""
        self._total_invested = max(0, self._total_invested + int(amount))

    def find_target(self, enemies: list[BaseEnemy]) -> BaseEnemy | None:
        """射程内で最も拠点に近い（=自分から遠くで先頭の）敵を選ぶ単純戦略。

        ここでは「最も近い敵」を返す。派生クラスで上書き可能。
        """
        tx, ty = self._pos
        best: BaseEnemy | None = None
        best_dist = self._range
        for e in enemies:
            if e.is_dead():
                continue
            ex, ey = e.get_pos()
            d = math.hypot(ex - tx, ey - ty)
            if d <= best_dist:
                best = e
                best_dist = d
        return best

    def attack(self, target: BaseEnemy) -> Bullet | None:
        """発射する。クールタイム未満なら None。"""
        return Bullet(pos=self._pos, target=target, damage=self._damage)

    def update(
        self,
        enemies: list[BaseEnemy],
        now: float | None = None,
    ) -> list[Bullet]:
        """1フレーム分の動作。発射した弾のリストを返す（無ければ空）。"""
        if now is None:
            now = pg.time.get_ticks() / 1000.0
        if now - self._last_shot_tick < self._cooldown:
            return []
        target = self.find_target(enemies)
        if target is None:
            return []
        bullet = self.attack(target)
        if bullet is None:
            return []
        self._last_shot_tick = now
        return [bullet]

    def draw(self, screen: pg.Surface) -> None:
        """タワーを画像で描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)
