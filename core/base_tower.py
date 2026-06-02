"""タワー基底クラス。

派生クラス（炎・氷・雷・物理）は担当③が実装する。基底は射程内の敵を見つけ
クールタイム経過ごとに弾を撃つ最小実装。
"""

from __future__ import annotations

import math

import pygame as pg

from .base_enemy import BaseEnemy
from .bullet import Bullet
from .constants import (
    COLOR_HP_BAR_BG,
    COLOR_HP_BAR_FG,
    COLOR_TOWER,
    TOWER_BASE_COOLDOWN,
    TOWER_BASE_DAMAGE,
    TOWER_BASE_RANGE,
    TOWER_MAX_HP,
)
from .image_cache import load_scaled_image


class BaseTower:
    """タワー基底クラス。"""

    DEFAULT_RADIUS: int = 16
    RANGE_RING_ALPHA: int = 40
    HP_BAR_WIDTH: int = 44
    HP_BAR_HEIGHT: int = 5
    HP_BAR_OFFSET: int = 8

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
        max_hp: int = TOWER_MAX_HP,
    ) -> None:
        if cooldown is None:
            cooldown = fire_cooldown if fire_cooldown is not None else TOWER_BASE_COOLDOWN
        self._pos: tuple[float, float] = pos
        self._range: float = range_
        self._damage: int = damage
        self._cooldown: float = cooldown
        self._last_shot_tick: float = -cooldown  # 起動直後から撃てるように
        # 耐久（敵の体当たりで減る）。0 で破壊され World から取り除かれる。
        self._max_hp: int = max(1, int(max_hp))
        self._hp: int = self._max_hp
        # アップグレードシステム用（担当③）
        self._level: int = 1
        self._total_invested: int = max(0, int(purchase_cost))

        self.image: pg.Surface = load_scaled_image(self.image_name, self.image_size)
        self.rect: pg.Rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

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

    # --- 耐久（敵の体当たり） ---

    def get_hp(self) -> int:
        """現在 HP を返す。"""
        return self._hp

    def get_max_hp(self) -> int:
        """最大 HP を返す。"""
        return self._max_hp

    def set_hp(self, value: int) -> None:
        """HP を 0〜最大 HP の範囲に丸めて設定する。"""
        self._hp = max(0, min(self._max_hp, int(value)))

    def take_damage(self, amount: int) -> None:
        """敵の体当たりなどでダメージを受ける（HP は 0 未満にならない）。"""
        if amount <= 0:
            return
        self._hp = max(0, self._hp - int(amount))

    def is_destroyed(self) -> bool:
        """HP が 0 以下なら True（World から取り除かれる対象）。"""
        return self._hp <= 0

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
        x, y = int(self._pos[0]), int(self._pos[1])
        self._draw_range_ring(screen, x, y)
        self.rect.center = (x, y)
        screen.blit(self.image, self.rect)
        self._draw_hp_bar(screen, x, y)

    def _draw_hp_bar(self, screen: pg.Surface, x: int, y: int) -> None:
        """被ダメージ時のみ、タワー上部に残り HP バーを描く。"""
        if self._hp >= self._max_hp:
            return
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

    def _draw_range_ring(self, screen: pg.Surface, x: int, y: int) -> None:
        try:
            ring = pg.Surface(
                (int(self._range * 2), int(self._range * 2)),
                flags=pg.SRCALPHA,
            )
            pg.draw.circle(
                ring,
                (*COLOR_TOWER, self.RANGE_RING_ALPHA),
                (int(self._range), int(self._range)),
                int(self._range),
            )
            screen.blit(ring, (x - int(self._range), y - int(self._range)))
        except (pg.error, ValueError):
            pass
