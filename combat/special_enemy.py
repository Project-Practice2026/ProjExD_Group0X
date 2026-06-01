"""特殊敵バリエーション。

- `FastEnemy`: 高速・低HP
- `ShieldedEnemy`: 盾を持ち、盾HPが残っている間はダメージを無効化する
- 旧 `SpecialEnemy` クラス名は `FastEnemy` のエイリアスとして残す（既存呼び出し互換）
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import ClassVar

import pygame as pg

try:
    from ..core.base_enemy import BaseEnemy
    from ..core.constants import (
        COLOR_SHIELD,
        FAST_ENEMY_DAMAGE,
        FAST_ENEMY_HP,
        FAST_ENEMY_REWARD,
        FAST_ENEMY_SPEED,
        SHIELDED_ENEMY_DAMAGE,
        SHIELDED_ENEMY_HP,
        SHIELDED_ENEMY_REWARD,
        SHIELDED_ENEMY_SHIELD,
        SHIELDED_ENEMY_SPEED,
        SPECIAL_FAST_PROBABILITY,
        SPECIAL_SHIELDED_PROBABILITY,
    )
except ImportError:
    from core.base_enemy import BaseEnemy
    from core.constants import (
        COLOR_SHIELD,
        FAST_ENEMY_DAMAGE,
        FAST_ENEMY_HP,
        FAST_ENEMY_REWARD,
        FAST_ENEMY_SPEED,
        SHIELDED_ENEMY_DAMAGE,
        SHIELDED_ENEMY_HP,
        SHIELDED_ENEMY_REWARD,
        SHIELDED_ENEMY_SHIELD,
        SHIELDED_ENEMY_SPEED,
        SPECIAL_FAST_PROBABILITY,
        SPECIAL_SHIELDED_PROBABILITY,
    )


class FastEnemy(BaseEnemy):
    """高速・低HP の小型敵。"""

    special_type: ClassVar[str] = "fast"

    image_name: str = "enemy_fast.png"
    image_size: tuple[int, int] = (32, 32)

    def __init__(self, pos: tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(
            pos=pos,
            hp=FAST_ENEMY_HP,
            speed=FAST_ENEMY_SPEED,
            damage=FAST_ENEMY_DAMAGE,
            reward=FAST_ENEMY_REWARD,
        )

        image = pg.image.load(Path("assets") / "fig" / self.image_name)
        self.image = pg.transform.scale(image, self.image_size)
        self.rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    def draw(self, screen: pg.Surface) -> None:
        """高速敵を画像で描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)


class ShieldedEnemy(BaseEnemy):
    """盾を持つ敵。盾HPが残っている間、ダメージはまず盾に吸収される。"""

    special_type: ClassVar[str] = "shielded"

    image_name: str = "enemy_shielded.png"
    image_size: tuple[int, int] = (32, 32)

    def __init__(self, pos: tuple[float, float] = (0.0, 0.0)) -> None:
        super().__init__(
            pos=pos,
            hp=SHIELDED_ENEMY_HP,
            speed=SHIELDED_ENEMY_SPEED,
            damage=SHIELDED_ENEMY_DAMAGE,
            reward=SHIELDED_ENEMY_REWARD,
        )
        self._shield: int = SHIELDED_ENEMY_SHIELD
        self._max_shield: int = SHIELDED_ENEMY_SHIELD

        image = pg.image.load(Path("assets") / "fig" / self.image_name)
        self.image = pg.transform.scale(image, self.image_size)
        self.rect = self.image.get_rect(center=(int(self._pos[0]), int(self._pos[1])))

    def get_shield(self) -> int:
        """現在残っている盾 HP を返す。"""
        return self._shield

    def get_max_shield(self) -> int:
        """盾 HP の初期最大値を返す。"""
        return self._max_shield

    def has_shield(self) -> bool:
        """盾 HP が 1 以上残っていれば True を返す。"""
        return self._shield > 0

    def take_damage(self, amount: int) -> None:
        """盾が残っていれば盾から先にダメージを吸収する。"""
        if amount <= 0:
            return
        if self._shield > 0:
            absorbed = min(self._shield, amount)
            self._shield -= absorbed
            amount -= absorbed
        if amount > 0:
            super().take_damage(amount)

    def draw(self, screen: pg.Surface) -> None:
        """盾持ち敵を画像で描画し、盾が残っている間だけ外周リングを描画する。"""
        self.rect.center = (
            int(self._pos[0]),
            int(self._pos[1]),
        )
        screen.blit(self.image, self.rect)

        if self._shield > 0:
            pg.draw.circle(
                screen,
                COLOR_SHIELD,
                (int(self._pos[0]), int(self._pos[1])),
                self.DEFAULT_RADIUS + 4,
                width=2,
            )


class SpecialEnemy(FastEnemy):
    """既存呼び出し互換のため `FastEnemy` のエイリアス（旧名）。"""

    special_type: ClassVar[str] = "runner"

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        hp: int = FAST_ENEMY_HP,
        speed: float = FAST_ENEMY_SPEED,
        damage: int = FAST_ENEMY_DAMAGE,
        reward: int = FAST_ENEMY_REWARD,
    ) -> None:
        BaseEnemy.__init__(
            self,
            pos=pos,
            hp=hp,
            speed=speed,
            damage=damage,
            reward=reward,
        )


def create_combat_enemy(pos: tuple[float, float], roll: float | None = None) -> BaseEnemy:
    """通常ウェーブ用に、確率で特殊敵を混ぜて生成する。"""
    value = random.random() if roll is None else roll
    if value < SPECIAL_FAST_PROBABILITY:
        return FastEnemy(pos=pos)
    if value < SPECIAL_FAST_PROBABILITY + SPECIAL_SHIELDED_PROBABILITY:
        return ShieldedEnemy(pos=pos)
    return BaseEnemy(pos=pos)


def create_special_enemy(pos: tuple[float, float], roll: float | None = None) -> BaseEnemy:
    """必ず特殊敵（FastEnemy / ShieldedEnemy）を 1 体生成する。

    出現させるかどうかの判定は呼び出し側（WaveManager のウェーブ別確率）に任せ、
    ここでは fast / shielded の内訳のみを相対確率で決める。
    """
    total = SPECIAL_FAST_PROBABILITY + SPECIAL_SHIELDED_PROBABILITY
    value = random.random() if roll is None else roll
    if total <= 0 or value < SPECIAL_FAST_PROBABILITY / total:
        return FastEnemy(pos=pos)
    return ShieldedEnemy(pos=pos)
