"""マップとフィールドの状態。

背景描画、敵の出現口、タワー設置可否判定を担当する。エンティティの一覧
（プレイヤー / 敵 / タワー / 弾）も保持する。
"""

from __future__ import annotations

import contextlib
import math
from typing import Protocol

import pygame as pg

from .base_enemy import BaseEnemy
from .base_player import BasePlayer
from .base_tower import BaseTower
from .bullet import Bullet
from .constants import (
    COLOR_BG,
    COLOR_EFFECT_EXPLOSION,
    COLOR_EFFECT_HIT,
    COLOR_EFFECT_SHOCKWAVE,
    COLOR_TEXT,
    EFFECT_EXPLOSION_PARTICLES,
    EFFECT_HIT_PARTICLES,
    EFFECT_MUZZLE_PARTICLES,
    EFFECT_SHOCKWAVE_DURATION,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SE_ENEMY_DIE,
    SE_HIT,
    SE_TOWER_FIRE,
)
from .fortress import Fortress


class EffectSink(Protocol):
    """エフェクト発火点の最小プロトコル（実体は combat.EffectManager）。"""

    def update(self, dt: float) -> None:
        """1 フレーム分のパーティクル更新。"""

    def draw(self, screen: pg.Surface) -> None:
        """全パーティクルを描画。"""

    def spawn_explosion(
        self,
        pos: tuple[float, float],
        count: int = EFFECT_EXPLOSION_PARTICLES,
        color: tuple[int, int, int] = COLOR_EFFECT_EXPLOSION,
    ) -> None:
        """敵撃破などの爆発エフェクト。"""

    def spawn_hit(
        self,
        pos: tuple[float, float],
        count: int = EFFECT_HIT_PARTICLES,
        color: tuple[int, int, int] = COLOR_EFFECT_HIT,
    ) -> None:
        """ヒット時のフラッシュ。"""

    def spawn_muzzle_flash(
        self,
        pos: tuple[float, float],
        direction: tuple[float, float],
        count: int = EFFECT_MUZZLE_PARTICLES,
    ) -> None:
        """発射時のマズルフラッシュ。"""

    def spawn_shockwave(
        self,
        pos: tuple[float, float],
        radius: float,
        color: tuple[int, int, int] = COLOR_EFFECT_SHOCKWAVE,
        duration: float = EFFECT_SHOCKWAVE_DURATION,
    ) -> None:
        """範囲攻撃の波紋。"""


class _NullEffects:
    """EffectSink を未注入時のフォールバック（全 no-op）。"""

    def update(self, dt: float) -> None:
        """1 フレーム分の状態を更新する。"""
        _ = dt

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        _ = screen

    def spawn_explosion(
        self,
        pos: tuple[float, float],
        count: int = EFFECT_EXPLOSION_PARTICLES,
        color: tuple[int, int, int] = COLOR_EFFECT_EXPLOSION,
    ) -> None:
        """Explosion エフェクトをスポーンする。"""
        _ = pos, count, color

    def spawn_hit(
        self,
        pos: tuple[float, float],
        count: int = EFFECT_HIT_PARTICLES,
        color: tuple[int, int, int] = COLOR_EFFECT_HIT,
    ) -> None:
        """Hit エフェクトをスポーンする。"""
        _ = pos, count, color

    def spawn_muzzle_flash(
        self,
        pos: tuple[float, float],
        direction: tuple[float, float],
        count: int = EFFECT_MUZZLE_PARTICLES,
    ) -> None:
        """Muzzle_flash エフェクトをスポーンする。"""
        _ = pos, direction, count

    def spawn_shockwave(
        self,
        pos: tuple[float, float],
        radius: float,
        color: tuple[int, int, int] = COLOR_EFFECT_SHOCKWAVE,
        duration: float = EFFECT_SHOCKWAVE_DURATION,
    ) -> None:
        """Shockwave エフェクトをスポーンする。"""
        _ = pos, radius, color, duration


class SoundSink(Protocol):
    """BGM・SE 再生の最小プロトコル（実体は presentation.SoundManager）。"""

    def play_se(self, name: str) -> None:
        """効果音を 1 回再生する。"""

    def play_bgm(self, name: str, loops: int = -1) -> None:
        """BGM を再生する（loops=-1 で無限ループ）。"""

    def stop_bgm(self) -> None:
        """BGM を停止する。"""


class _NullSound:
    """SoundSink を未注入時のフォールバック（全 no-op）。"""

    def play_se(self, name: str) -> None:
        """Se を再生する。"""
        _ = name

    def play_bgm(self, name: str, loops: int = -1) -> None:
        """Bgm を再生する。"""
        _ = name, loops

    def stop_bgm(self) -> None:
        """Bgm を停止する。"""
        pass


class World:
    """ワールド（マップ + エンティティ）。"""

    SPAWN_MARKER_RADIUS: int = 8
    TOWER_PLACEMENT_MARGIN: float = 24.0
    FORTRESS_PLACEMENT_MARGIN: float = 60.0

    def __init__(
        self,
        spawn_points: list[tuple[float, float]] | None = None,
        fortress: Fortress | None = None,
        effects: EffectSink | None = None,
        sound: SoundSink | None = None,
    ) -> None:
        if spawn_points is None:
            spawn_points = [
                (40.0, SCREEN_HEIGHT * 0.25),
                (40.0, SCREEN_HEIGHT * 0.50),
                (40.0, SCREEN_HEIGHT * 0.75),
            ]
        self._spawn_points: list[tuple[float, float]] = spawn_points
        self._fortress: Fortress = fortress if fortress is not None else Fortress()
        self._players: list[BasePlayer] = []
        self._enemies: list[BaseEnemy] = []
        self._towers: list[BaseTower] = []
        self._bullets: list[Bullet] = []
        self._effects: EffectSink = effects if effects is not None else _NullEffects()
        self._sound: SoundSink = sound if sound is not None else _NullSound()

    # ----- accessors -----

    def get_fortress(self) -> Fortress:
        """Fortress を返す。"""
        return self._fortress

    def get_effects(self) -> EffectSink:
        """Effects を返す。"""
        return self._effects

    def get_sound(self) -> SoundSink:
        """Sound を返す。"""
        return self._sound

    def get_spawn_points(self) -> list[tuple[float, float]]:
        """Spawn_points を返す。"""
        return list(self._spawn_points)

    def get_players(self) -> list[BasePlayer]:
        """Players を返す。"""
        return self._players

    def get_enemies(self) -> list[BaseEnemy]:
        """Enemies を返す。"""
        return self._enemies

    def get_towers(self) -> list[BaseTower]:
        """Towers を返す。"""
        return self._towers

    def get_bullets(self) -> list[Bullet]:
        """Bullets を返す。"""
        return self._bullets

    # ----- mutators -----

    def add_player(self, player: BasePlayer) -> None:
        """Player を追加する。"""
        self._players.append(player)

    def add_enemy(self, enemy: BaseEnemy) -> None:
        """Enemy を追加する。"""
        self._enemies.append(enemy)

    def add_tower(self, tower: BaseTower) -> None:
        """Tower を追加する。"""
        self._towers.append(tower)

    def add_bullet(self, bullet: Bullet) -> None:
        """Bullet を追加する。"""
        self._bullets.append(bullet)

    def add_bullets(self, bullets: list[Bullet]) -> None:
        """Bullets を追加する。"""
        self._bullets.extend(bullets)

    # ----- queries -----

    def can_place_tower(self, pos: tuple[float, float]) -> bool:
        """タワーを置けるかどうか。既存タワーとの重なりと拠点との近接を禁止。"""
        x, y = pos
        if x < 0 or x > SCREEN_WIDTH or y < 0 or y > SCREEN_HEIGHT:
            return False
        fx, fy = self._fortress.get_pos()
        if math.hypot(fx - x, fy - y) < self.FORTRESS_PLACEMENT_MARGIN:
            return False
        for t in self._towers:
            tx, ty = t.get_pos()
            if math.hypot(tx - x, ty - y) < self.TOWER_PLACEMENT_MARGIN:
                return False
        return True

    # ----- per-frame -----

    def _resolve_tower_collisions(self, dt: float) -> None:
        """敵の体当たりでタワーの HP を削り、破壊されたタワーを取り除く。"""
        for enemy in self._enemies:
            collide = getattr(enemy, "collide_with_towers", None)
            if callable(collide):
                collide(self._towers, dt)
        self._towers = [t for t in self._towers if not t.is_destroyed()]

    def update(self, dt: float) -> None:
        """エンティティを 1 フレーム分進める。"""
        for player in self._players:
            # 派生クラスが入力を反映する想定。基底では何もしない呼び出しでも可。
            update = getattr(player, "update", None)
            if callable(update):
                # 入力辞書を受けないシグネチャの派生にも備える
                with contextlib.suppress(TypeError):
                    update({"dt": dt})

        for enemy in list(self._enemies):
            update_with_towers = getattr(enemy, "update_with_towers", None)
            if callable(update_with_towers):
                update_with_towers(self._fortress, self._towers, dt)
            else:
                enemy.update(self._fortress, dt)
        # 敵の体当たりでタワーの HP を削り、破壊されたタワーを取り除く。
        self._resolve_tower_collisions(dt)
        # 撃破・到達した敵を弾く前に撃破位置のエフェクト＋SE を焚く
        for dead in (e for e in self._enemies if e.is_dead()):
            death_hook = getattr(dead, "trigger_death_effect", None)
            if callable(death_hook):
                death_hook(self)
                continue
            self._effects.spawn_explosion(dead.get_pos())
            self._sound.play_se(SE_ENEMY_DIE)
        self._enemies = [
            e for e in self._enemies if not e.is_dead() and not e.has_reached_fortress()
        ]

        new_bullets: list[Bullet] = []
        for tower in self._towers:
            new_bullets.extend(tower.update(self._enemies))
        if new_bullets:
            self._sound.play_se(SE_TOWER_FIRE)
        self._bullets.extend(new_bullets)

        # 命中したフレームを検知して SE
        for bullet in self._bullets:
            bullet.update(dt)
            was_consumed_after_update = bullet.is_consumed()
            bullet.check_hit(self._enemies)
            if not was_consumed_after_update and bullet.is_consumed():
                self._sound.play_se(SE_HIT)
        self._bullets = [b for b in self._bullets if not b.is_consumed()]

        # エフェクトのタイムステップ
        self._effects.update(dt)

    def draw(self, screen: pg.Surface) -> None:
        """背景・出現口・エンティティを描画する。"""
        screen.fill(COLOR_BG)
        for sp in self._spawn_points:
            pg.draw.circle(
                screen,
                COLOR_TEXT,
                (int(sp[0]), int(sp[1])),
                self.SPAWN_MARKER_RADIUS,
                width=1,
            )
        self._fortress.draw(screen)
        for tower in self._towers:
            tower.draw(screen)
        for enemy in self._enemies:
            enemy.draw(screen)
        for bullet in self._bullets:
            bullet.draw(screen)
        for player in self._players:
            draw = getattr(player, "draw", None)
            if callable(draw):
                draw(screen)
        self._effects.draw(screen)
