"""前線役（プレイヤー2）。

WASDで移動、Shiftでダッシュ、Jで通常攻撃（現在の武器を発射）、Kでスキル発動、
Q/Eで武器切替、5/6でスキル切替、Lで近接タワー修理枠。

武器・スキルは外部から注入する（`combat.weapons` / `combat.fighter_skills` の
インスタンス）ことで `core → combat` の循環を回避している。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, ClassVar

import pygame as pg

from .base_player import BasePlayer
from .base_tower import BaseTower
from .bullet import Bullet
from .constants import (
    COLOR_PLAYER,
    PLAYER_FIGHTER_ID,
    PLAYER_MAX_HP,
    SE_WEAPON_FIRE,
    WEAPON_SWITCH_COOLDOWN,
)
from .world import World

if TYPE_CHECKING:
    from combat.fighter_skills import BaseSkill
    from combat.weapons import BaseWeapon


class Fighter(BasePlayer):
    """前線役プレイヤー。"""

    BASE_SPEED: float = 220.0
    DASH_MULTIPLIER: float = 1.8
    REPAIR_RANGE: float = 40.0
    DEFAULT_RADIUS: int = 14
    image_name: ClassVar[str] = "player_fighter.png"

    MOVE_KEYS: ClassVar[dict[int, tuple[int, int]]] = {
        pg.K_w: (0, -1),
        pg.K_s: (0, 1),
        pg.K_a: (-1, 0),
        pg.K_d: (1, 0),
    }
    DASH_KEYS: ClassVar[tuple[int, ...]] = (pg.K_LSHIFT, pg.K_RSHIFT)

    def __init__(
        self,
        pos: tuple[float, float] | None = None,
        max_hp: int = PLAYER_MAX_HP,
        weapons: list[BaseWeapon] | None = None,
        skills: list[BaseSkill] | None = None,
    ) -> None:
        super().__init__(player_id=PLAYER_FIGHTER_ID, pos=pos, max_hp=max_hp)
        self._speed = self.BASE_SPEED
        self._is_dashing: bool = False
        self._facing: tuple[float, float] = (1.0, 0.0)
        self._pending_bullets: list[Bullet] = []
        # 武器・スキル
        self._weapons: list[BaseWeapon] = list(weapons or [])
        self._weapon_index: int = 0
        self._weapon_switch_cooldown_left: float = 0.0
        self._skills: list[BaseSkill] = list(skills or [])
        self._skill_index: int = 0

    # ----- accessors -----

    def is_dashing(self) -> bool:
        """Dashing かどうかを返す。"""
        return self._is_dashing

    def get_facing(self) -> tuple[float, float]:
        """Facing を返す。"""
        return self._facing

    def get_current_weapon(self) -> BaseWeapon | None:
        """Current_weapon を返す。"""
        if not self._weapons:
            return None
        return self._weapons[self._weapon_index % len(self._weapons)]

    def get_current_skill(self) -> BaseSkill | None:
        """Current_skill を返す。"""
        if not self._skills:
            return None
        return self._skills[self._skill_index % len(self._skills)]

    def get_weapons(self) -> list[BaseWeapon]:
        """Weapons を返す。"""
        return list(self._weapons)

    def get_skills(self) -> list[BaseSkill]:
        """Skills を返す。"""
        return list(self._skills)

    def get_attack_cooldown_left(self) -> float:
        """現在の武器の残クールタイム。武器が無いなら 0。"""
        weapon = self.get_current_weapon()
        return weapon.get_cooldown_left() if weapon is not None else 0.0

    def get_skill_cooldown_left(self) -> float:
        """現在のスキルの残クールタイム。"""
        skill = self.get_current_skill()
        return skill.get_cooldown_left() if skill is not None else 0.0

    def is_invincible(self) -> bool:
        """Invincible かどうかを返す。"""
        skill = self.get_current_skill()
        return bool(skill is not None and getattr(skill, "is_invincible", lambda: False)())

    # ----- mutators -----

    def cycle_weapon(self, delta: int = 1) -> None:
        """Weapon を切り替える。"""
        if not self._weapons or self._weapon_switch_cooldown_left > 0:
            return
        self._weapon_index = (self._weapon_index + delta) % len(self._weapons)
        self._weapon_switch_cooldown_left = WEAPON_SWITCH_COOLDOWN

    def cycle_skill(self, delta: int = 1) -> None:
        """Skill を切り替える。"""
        if not self._skills:
            return
        self._skill_index = (self._skill_index + delta) % len(self._skills)

    # ----- event-based input -----

    def handle_event(self, event: pg.event.Event, world: World) -> None:
        """単発イベント（J / K / L / Q / E / 5 / 6 のキー押下）を処理する。"""
        if event.type != pg.KEYDOWN:
            return
        if event.key == pg.K_j:
            self._try_attack(world)
        elif event.key == pg.K_k:
            self._try_skill(world)
        elif event.key == pg.K_l:
            self._try_repair(world)
        elif event.key == pg.K_q:
            self.cycle_weapon(-1)
        elif event.key == pg.K_e:
            self.cycle_weapon(1)
        elif event.key == pg.K_5:
            self.cycle_skill(-1)
        elif event.key == pg.K_6:
            self.cycle_skill(1)

    # ----- continuous input -----

    def update_keys(
        self,
        keys: pg.key.ScancodeWrapper,
        dt: float,
        world: World,
    ) -> None:
        """連続入力（WASD移動、Shiftダッシュ）と内部タイマーを更新する。"""
        self._is_dashing = any(keys[k] for k in self.DASH_KEYS)
        speed_mult = self.DASH_MULTIPLIER if self._is_dashing else 1.0

        dx = 0.0
        dy = 0.0
        for key, (kx, ky) in self.MOVE_KEYS.items():
            if keys[key]:
                dx += kx
                dy += ky
        length = math.hypot(dx, dy)
        if length > 0:
            dx /= length
            dy /= length
            self._facing = (dx, dy)
            self.update({"dt": dt, "dx": dx * speed_mult, "dy": dy * speed_mult})

        # 武器・スキルのクールダウン進行
        for weapon in self._weapons:
            weapon.update(dt)
        for skill in self._skills:
            skill.update(dt, self, world)
        self._weapon_switch_cooldown_left = max(0.0, self._weapon_switch_cooldown_left - dt)

    # ----- pending output -----

    def drain_pending_bullets(self) -> list[Bullet]:
        """前フレームで生成された弾を取り出して内部キューを空にする。"""
        bullets = self._pending_bullets
        self._pending_bullets = []
        return bullets

    # ----- internal -----

    def _try_attack(self, world: World) -> None:
        weapon = self.get_current_weapon()
        if weapon is None:
            return
        target = weapon.find_target(self._pos, world.get_enemies())
        bullets = weapon.fire(self._pos, target, self._facing)
        if not bullets:
            return
        world.get_effects().spawn_muzzle_flash(self._pos, self._facing)
        world.get_sound().play_se(SE_WEAPON_FIRE)
        self._pending_bullets.extend(bullets)

    def _try_skill(self, world: World) -> None:
        skill = self.get_current_skill()
        if skill is None:
            return
        skill.activate(self, world)

    def _try_repair(self, world: World) -> None:
        # 近接タワーを修理。リソース管理は今は Fighter 自身が持たず、後付け可能にする
        # ため、ここでは枠だけ用意する。本体は担当③で BaseTower に HP を追加後に接続。
        nearest = self._nearest_tower_within_range(world)
        if nearest is None:
            return
        _ = nearest

    def _nearest_tower_within_range(self, world: World) -> BaseTower | None:
        x, y = self._pos
        nearest = None
        nearest_dist = self.REPAIR_RANGE
        for tower in world.get_towers():
            tx, ty = tower.get_pos()
            d = math.hypot(tx - x, ty - y)
            if d <= nearest_dist:
                nearest_dist = d
                nearest = tower
        return nearest

    # ----- draw -----

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        x, y = int(self._pos[0]), int(self._pos[1])
        # 向き表示（短い線）
        fx, fy = self._facing
        end = (int(x + fx * self.DEFAULT_RADIUS), int(y + fy * self.DEFAULT_RADIUS))
        pg.draw.line(screen, COLOR_PLAYER, (x, y), end, width=3)
        # 無敵中（ダッシュ攻撃中など）は外周にリング
        if self.is_invincible():
            pg.draw.circle(screen, (255, 255, 255), (x, y), self.DEFAULT_RADIUS + 4, width=2)
