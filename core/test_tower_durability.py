"""タワーの耐久（敵の体当たりで HP が減り、約10回で破壊される）のテスト。

描画には依存せず、HP ロジックと体当たり判定・World からの除去のみを検証する。
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from core.base_enemy import BaseEnemy
from core.base_tower import BaseTower
from core.constants import TOWER_CONTACT_DISTANCE, TOWER_MAX_HP
from core.fortress import Fortress
from core.world import World
from towers.physical_tower import PhysicalTower

pg.init()


# ===== BaseTower HP =====


def test_tower_starts_at_full_hp() -> None:
    """生成直後は HP が最大（TOWER_MAX_HP）。"""
    tower = BaseTower(pos=(100.0, 100.0))
    assert tower.get_max_hp() == TOWER_MAX_HP
    assert tower.get_hp() == TOWER_MAX_HP
    assert not tower.is_destroyed()


def test_tower_take_damage_and_destroy() -> None:
    """ダメージで HP が減り、負値は無視、0 で破壊扱い。"""
    tower = BaseTower(pos=(0.0, 0.0), max_hp=10)
    tower.take_damage(3)
    assert tower.get_hp() == 7
    tower.take_damage(-5)  # 負のダメージは無視
    assert tower.get_hp() == 7
    tower.take_damage(100)  # HP は 0 未満にならない
    assert tower.get_hp() == 0
    assert tower.is_destroyed()


def test_derived_tower_inherits_hp() -> None:
    """派生タワー（物理）も HP を引き継ぐ。"""
    tower = PhysicalTower(pos=(0.0, 0.0))
    assert tower.get_hp() == tower.get_max_hp() == TOWER_MAX_HP
    tower.take_damage(TOWER_MAX_HP)
    assert tower.is_destroyed()


# ===== 敵の体当たり =====


def test_enemy_bump_respects_cooldown() -> None:
    """接触し続けても TOWER_CONTACT_INTERVAL ごとに 1 回だけダメージが入る。"""
    tower = BaseTower(pos=(100.0, 100.0), max_hp=10)
    enemy = BaseEnemy(pos=(100.0, 100.0), speed=0.0)

    enemy.collide_with_towers([tower], dt=0.1)
    assert tower.get_hp() == 9  # 1 回目はすぐ当たる
    enemy.collide_with_towers([tower], dt=0.1)
    assert tower.get_hp() == 9  # クールダウン中は当たらない
    enemy.collide_with_towers([tower], dt=0.5)
    assert tower.get_hp() == 8  # 間隔経過後に再びダメージ


def test_about_ten_bumps_destroy_tower() -> None:
    """約10回の体当たりでタワーが破壊される。"""
    tower = BaseTower(pos=(100.0, 100.0), max_hp=TOWER_MAX_HP)
    enemy = BaseEnemy(pos=(100.0, 100.0), speed=0.0)
    for _ in range(TOWER_MAX_HP):
        enemy.collide_with_towers([tower], dt=0.5)
    assert tower.is_destroyed()


def test_enemy_out_of_range_does_not_damage_tower() -> None:
    """接触距離より離れた敵はダメージを与えない。"""
    tower = BaseTower(pos=(100.0, 100.0))
    enemy = BaseEnemy(pos=(100.0, 100.0 + TOWER_CONTACT_DISTANCE + 10.0), speed=0.0)
    enemy.collide_with_towers([tower], dt=0.5)
    assert tower.get_hp() == tower.get_max_hp()


def test_dead_enemy_does_not_damage_tower() -> None:
    """撃破済みの敵はタワーにダメージを与えない。"""
    tower = BaseTower(pos=(100.0, 100.0))
    enemy = BaseEnemy(pos=(100.0, 100.0), hp=1, speed=0.0)
    enemy.take_damage(5)
    assert enemy.is_dead()
    enemy.collide_with_towers([tower], dt=0.5)
    assert tower.get_hp() == tower.get_max_hp()


# ===== World からの除去 =====


def test_world_removes_destroyed_tower() -> None:
    """World.update を通じて体当たりされ続けると、破壊タワーが除去される。"""
    world = World(fortress=Fortress(pos=(1000.0, 360.0)))
    tower = BaseTower(pos=(200.0, 360.0), max_hp=TOWER_MAX_HP)
    world.add_tower(tower)
    # タワー上に居座る不動の敵（タワーの攻撃では死なないよう高 HP）。
    enemy = BaseEnemy(pos=(200.0, 360.0), hp=10_000, speed=0.0)
    world.add_enemy(enemy)

    for _ in range(TOWER_MAX_HP + 2):
        world.update(0.5)

    assert tower.is_destroyed()
    assert tower not in world.get_towers()


if __name__ == "__main__":
    test_tower_starts_at_full_hp()
    test_tower_take_damage_and_destroy()
    test_derived_tower_inherits_hp()
    test_enemy_bump_respects_cooldown()
    test_about_ten_bumps_destroy_tower()
    test_enemy_out_of_range_does_not_damage_tower()
    test_dead_enemy_does_not_damage_tower()
    test_world_removes_destroyed_tower()
    print("All tower durability tests passed.")
