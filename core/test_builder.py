"""建築役（Builder）のタワー設置ロジックのテスト。

特に「自分の現在位置に Enter で設置する」操作（place_tower_at_self）を検証する。
描画には依存しない（SDL_VIDEODRIVER=dummy）。
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from core.builder import Builder
from core.world import World

pg.init()


def test_builder_places_tower_at_own_position() -> None:
    """place_tower_at_self は建築役の現在位置にタワーを設置する。"""
    world = World()
    builder = Builder(pos=(300.0, 300.0))
    assert builder.place_tower_at_self(world)
    towers = world.get_towers()
    assert len(towers) == 1
    assert towers[0].get_pos() == (300.0, 300.0)


def test_builder_enter_key_places_tower_at_self() -> None:
    """Enter キーで自分の位置にタワーを設置する。"""
    world = World()
    builder = Builder(pos=(250.0, 260.0))
    builder.handle_event(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN), world)
    towers = world.get_towers()
    assert len(towers) == 1
    assert towers[0].get_pos() == (250.0, 260.0)


def test_builder_cannot_place_without_gold() -> None:
    """資源不足では設置できない。"""
    world = World()
    builder = Builder(pos=(300.0, 300.0), gold=0)
    assert not builder.place_tower_at_self(world)
    assert world.get_towers() == []


def test_builder_cannot_place_twice_at_same_spot() -> None:
    """同じ場所には重ねて設置できない（2 回目は設置不可）。"""
    world = World()
    builder = Builder(pos=(400.0, 300.0))
    assert builder.place_tower_at_self(world)
    assert not builder.place_tower_at_self(world)
    assert len(world.get_towers()) == 1


if __name__ == "__main__":
    test_builder_places_tower_at_own_position()
    test_builder_enter_key_places_tower_at_self()
    test_builder_cannot_place_without_gold()
    test_builder_cannot_place_twice_at_same_spot()
    print("All builder tests passed.")
