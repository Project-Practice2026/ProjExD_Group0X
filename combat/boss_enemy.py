"""ボス敵。

通常敵の `BOSS_HP_MULTIPLIER` 倍の HP を持ち、`BOSS_SPECIAL_INTERVAL` 秒ごとに
周囲に範囲ダメージ（playerにダメージ）を出す。撃破時に派手な爆発演出。
"""

from __future__ import annotations

import math

import pygame as pg

try:
    from ..core.base_enemy import BaseEnemy
    from ..core.base_player import BasePlayer
    from ..core.constants import (
        BOSS_DAMAGE,
        BOSS_HP_MULTIPLIER,
        BOSS_REWARD,
        BOSS_SPECIAL_DAMAGE,
        BOSS_SPECIAL_INTERVAL,
        BOSS_SPECIAL_RADIUS,
        BOSS_SPEED,
        COLOR_EFFECT_BOSS_DEATH,
        COLOR_EFFECT_SHOCKWAVE,
        ENEMY_BASE_HP,
        SE_BOSS_DIE,
        SE_BOSS_SPECIAL,
    )
    from ..core.fortress import Fortress
    from ..core.world import World
except ImportError:
    from core.base_enemy import BaseEnemy
    from core.base_player import BasePlayer
    from core.constants import (
        BOSS_DAMAGE,
        BOSS_HP_MULTIPLIER,
        BOSS_REWARD,
        BOSS_SPECIAL_DAMAGE,
        BOSS_SPECIAL_INTERVAL,
        BOSS_SPECIAL_RADIUS,
        BOSS_SPEED,
        COLOR_EFFECT_BOSS_DEATH,
        COLOR_EFFECT_SHOCKWAVE,
        ENEMY_BASE_HP,
        SE_BOSS_DIE,
        SE_BOSS_SPECIAL,
    )
    from core.fortress import Fortress
    from core.world import World


class BossEnemy(BaseEnemy):
    """ボス敵。"""

    BOSS_HP: int = ENEMY_BASE_HP * BOSS_HP_MULTIPLIER
    image_name: str = "boss.png"
    image_size: tuple[int, int] = (64, 64)

    def __init__(
        self,
        pos: tuple[float, float] = (0.0, 0.0),
        hp: int | None = None,
    ) -> None:
        super().__init__(
            pos=pos,
            hp=hp if hp is not None else self.BOSS_HP,
            speed=BOSS_SPEED,
            damage=BOSS_DAMAGE,
            reward=BOSS_REWARD,
        )
        self._special_timer: float = BOSS_SPECIAL_INTERVAL
        self._death_announced: bool = False

    def get_special_timer(self) -> float:
        """次の特殊範囲攻撃までの残り秒数を返す。"""
        return self._special_timer

    def trigger_death_effect(self, world: World) -> None:
        """撃破時に派手な演出を出す。SoloGame / 敵管理層から呼び出される想定。"""
        if self._death_announced:
            return
        self._death_announced = True
        effects = world.get_effects()
        # 大きな爆発＋赤い波紋を重ねる
        effects.spawn_explosion(self._pos, count=60, color=COLOR_EFFECT_BOSS_DEATH)
        effects.spawn_shockwave(
            self._pos,
            radius=BOSS_SPECIAL_RADIUS,
            color=COLOR_EFFECT_BOSS_DEATH,
        )
        world.get_sound().play_se(SE_BOSS_DIE)

    def update_with_world(self, dt: float, world: World) -> None:
        """World 連携が必要な特殊行動（周囲AOE）だけを処理する。"""
        if self.is_dead() or self.has_reached_fortress():
            return
        self._special_timer = max(0.0, self._special_timer - dt)
        if self._special_timer > 0:
            return
        self._special_timer = BOSS_SPECIAL_INTERVAL
        # 周囲のプレイヤーにダメージ
        self._burst_damage_players(world.get_players())
        # 視覚エフェクト＋ SE
        world.get_effects().spawn_shockwave(
            self._pos,
            radius=BOSS_SPECIAL_RADIUS,
            color=COLOR_EFFECT_SHOCKWAVE,
        )
        world.get_sound().play_se(SE_BOSS_SPECIAL)

    def _burst_damage_players(self, players: list[BasePlayer]) -> None:
        x, y = self._pos
        for player in players:
            px, py = player.get_pos()
            if math.hypot(px - x, py - y) > BOSS_SPECIAL_RADIUS:
                continue
            is_invincible = getattr(player, "is_invincible", None)
            if callable(is_invincible) and is_invincible():
                continue
            take = getattr(player, "set_hp", None)
            current = player.get_hp() if hasattr(player, "get_hp") else None
            if callable(take) and current is not None:
                take(current - BOSS_SPECIAL_DAMAGE)

    def update(self, fortress: Fortress, dt: float = 1.0 / 60.0) -> None:
        """BaseEnemy 互換のシグネチャ。World 連携が必要なときは update_with_world を使う。"""
        super().update(fortress, dt)

    def draw(self, screen: pg.Surface) -> None:
        """ボス本体画像と頭上の HP バーを描画する。"""
        x, y = int(self._pos[0]), int(self._pos[1])
        self.rect.center = (x, y)
        screen.blit(self.image, self.rect)

        # HP バー
        ratio = self._hp / self._max_hp if self._max_hp > 0 else 0
        bar_w = 50
        bar_h = 5
        bar_y = y - self.image_size[1] // 2 - 10
        pg.draw.rect(screen, (60, 60, 60), (x - bar_w // 2, bar_y, bar_w, bar_h))
        pg.draw.rect(
            screen,
            COLOR_EFFECT_BOSS_DEATH,
            (x - bar_w // 2, bar_y, int(bar_w * ratio), bar_h),
        )
