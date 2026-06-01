"""敵基底クラス。

EvolvedEnemy（担当①）、BossEnemy / SpecialEnemy（担当④）が継承する。
基底は拠点に向かって直進する最小実装。
"""

from __future__ import annotations

import math

import pygame as pg

from .constants import ENEMY_BASE_DAMAGE, ENEMY_BASE_HP, ENEMY_BASE_REWARD
from .fortress import Fortress
from .image_cache import load_scaled_image


class BaseEnemy:
    """敵基底クラス。拠点へ直進する。"""

    DEFAULT_RADIUS: int = 10
    DEFAULT_SPEED: float = 80.0
    CONTACT_DISTANCE: float = 32.0

    image_name: str = "enemy.png"
    image_size: tuple[int, int] = (32, 32)

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        hp: int = ENEMY_BASE_HP,
        speed: float = DEFAULT_SPEED,
        damage: int = ENEMY_BASE_DAMAGE,
        reward: int = ENEMY_BASE_REWARD,
    ) -> None:
        self._pos: tuple[float, float] = pos
        self._max_hp: int = hp
        self._hp: int = hp
        self._speed: float = speed
        self._damage: int = damage
        self._reward: int = max(0, reward)
        self._reached: bool = False
        # 速度低下バフ（担当③の氷タワー等で利用）
        self._speed_factor: float = 1.0
        self._slow_remaining: float = 0.0

        self.image: pg.Surface = load_scaled_image(self.image_name, self.image_size)
        self.rect: pg.Rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    @property
    def reward(self) -> int:
        """撃破時に得られる報酬量を返す。"""
        return self._reward

    @reward.setter
    def reward(self, value: int) -> None:
        """撃破報酬を 0 以上に丸めて設定する。"""
        self.set_reward(value)

    def get_pos(self) -> tuple[float, float]:
        """現在座標を返す。"""
        return self._pos

    def set_pos(self, x: float, y: float) -> None:
        """現在座標を設定する。"""
        self._pos = (x, y)

    def get_hp(self) -> int:
        """現在 HP を返す。"""
        return self._hp

    def get_max_hp(self) -> int:
        """最大 HP を返す。"""
        return self._max_hp

    def get_damage(self) -> int:
        """拠点到達時に与えるダメージを返す。"""
        return self._damage

    def get_reward(self) -> int:
        """撃破時に得られる報酬量を返す。"""
        return self._reward

    def set_reward(self, value: int) -> None:
        """撃破報酬を 0 以上に丸めて設定する。"""
        self._reward = max(0, value)

    def get_speed(self) -> float:
        """基礎移動速度を返す。"""
        return self._speed

    def set_speed(self, value: float) -> None:
        """基礎移動速度を 0 以上に丸めて設定する。"""
        self._speed = max(0.0, value)

    def get_effective_speed(self) -> float:
        """現在の slow バフを反映した実効速度。"""
        return self._speed * self._speed_factor

    def get_speed_factor(self) -> float:
        """氷タワーなどで適用中の速度倍率を返す。"""
        return self._speed_factor

    def get_slow_remaining(self) -> float:
        """速度低下効果の残り秒数を返す。"""
        return self._slow_remaining

    def apply_slow(self, factor: float, duration: float) -> None:
        """速度低下バフを適用する。

        既に slow 中の場合は、より強い factor を採用しつつ、残り duration は長い方を採る。
        """
        factor = max(0.0, min(1.0, float(factor)))
        duration = max(0.0, float(duration))
        if duration <= 0.0:
            return
        # より強い slow を優先（factor が小さいほど遅い）
        self._speed_factor = min(self._speed_factor, factor)
        self._slow_remaining = max(self._slow_remaining, duration)

    def has_reached_fortress(self) -> bool:
        """拠点へ到達してダメージ処理済みなら True を返す。"""
        return self._reached

    def take_damage(self, amount: int) -> None:
        """正のダメージ量だけ HP を減らし、0 未満にはしない。"""
        if amount <= 0:
            return
        self._hp = max(0, self._hp - amount)

    def is_dead(self) -> bool:
        """現在 HP が 0 以下なら True を返す。"""
        return self._hp <= 0

    def scale_hp(self, factor: float) -> None:
        """最大 HP と現在 HP を factor 倍する（最低 1 を保証）。

        ウェーブ進行に応じた難易度スケーリングで、スポーン直後の敵に適用する。
        現在 HP は最大 HP に揃える（出現直後は全快のため）。
        """
        factor = max(0.0, float(factor))
        self._max_hp = max(1, round(self._max_hp * factor))
        self._hp = self._max_hp

    def scale_damage(self, factor: float) -> None:
        """拠点到達時に与える接触ダメージを factor 倍する（最低 1 を保証）。

        ボス等のウェーブスケーリングで、スポーン直後の敵に適用する。
        """
        factor = max(0.0, float(factor))
        self._damage = max(1, round(self._damage * factor))

    def update(self, fortress: Fortress, dt: float = 1.0 / 60.0) -> None:
        """拠点方向へ直進移動し、接触時にダメージを与える。"""
        # slow バフのタイマーを進める
        if self._slow_remaining > 0.0:
            self._slow_remaining = max(0.0, self._slow_remaining - dt)
            if self._slow_remaining == 0.0:
                self._speed_factor = 1.0

        if self._reached or self.is_dead():
            return
        fx, fy = fortress.get_pos()
        x, y = self._pos
        vx, vy = fx - x, fy - y
        dist = math.hypot(vx, vy)
        if dist <= self.CONTACT_DISTANCE:
            fortress.take_damage(self._damage)
            self._reached = True
            return
        step = self.get_effective_speed() * dt
        if step >= dist - self.CONTACT_DISTANCE:
            fortress.take_damage(self._damage)
            self._reached = True
            return
        nx = x + (vx / dist) * step
        ny = y + (vy / dist) * step
        self._pos = (nx, ny)

    def draw(self, screen: pg.Surface) -> None:
        """通常敵を画像で描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)
