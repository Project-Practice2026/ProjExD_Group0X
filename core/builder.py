"""建築役（プレイヤー1）。

マウス左クリックでタワー設置、数字キー1〜4で設置するタワー種類を切替、
スペースキーで次ウェーブを早期開始リクエストする。マウス右クリックは
タワー選択UIの起点となる（中身は担当③が実装する想定）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

import pygame as pg

from .base_player import BasePlayer
from .base_tower import BaseTower
from .constants import COLOR_PLAYER, INITIAL_GOLD, PLAYER_BUILDER_ID, SE_TOWER_PLACE
from .world import World

TowerFactory = Callable[..., BaseTower]


class Builder(BasePlayer):
    """建築役プレイヤー。"""

    DEFAULT_TOWER_COST: int = 30
    DEFAULT_RADIUS: int = 12
    image_name: ClassVar[str] = "player_builder.png"
    TOWER_TYPES: ClassVar[tuple[str, ...]] = ("fire", "ice", "lightning", "physical")
    TOWER_TYPE_KEYS: ClassVar[dict[int, str]] = {
        pg.K_1: "fire",
        pg.K_2: "ice",
        pg.K_3: "lightning",
        pg.K_4: "physical",
    }

    def __init__(
        self,
        pos: tuple[float, float] | None = None,
        gold: int = INITIAL_GOLD,
        tower_cost: int = DEFAULT_TOWER_COST,
        tower_factories: dict[str, TowerFactory] | None = None,
    ) -> None:
        super().__init__(player_id=PLAYER_BUILDER_ID, pos=pos)
        self._gold: int = max(0, gold)
        self._tower_cost: int = max(0, tower_cost)
        self._selected_tower_type: str = self.TOWER_TYPES[0]
        self._wave_skip_requested: bool = False
        self._selected_tower: BaseTower | None = None
        # 属性タワーのファクトリ。未指定の属性は BaseTower にフォールバック。
        self._tower_factories: dict[str, TowerFactory] = dict(tower_factories or {})

    # ----- accessors -----

    def get_gold(self) -> int:
        """Gold を返す。"""
        return self._gold

    def set_gold(self, value: int) -> None:
        """Gold を設定する。"""
        self._gold = max(0, value)

    def get_selected_tower_type(self) -> str:
        """Selected_tower_type を返す。"""
        return self._selected_tower_type

    def get_selected_tower(self) -> BaseTower | None:
        """Selected_tower を返す。"""
        return self._selected_tower

    def get_tower_cost(self) -> int:
        """Tower_cost を返す。"""
        return self._tower_cost

    # ----- input -----

    def handle_event(self, event: pg.event.Event, world: World) -> None:
        """単発イベント（クリック・キー押下）を処理する。"""
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._try_place_tower(world, event.pos)
            elif event.button == 3:
                self._select_tower_at(world, event.pos)
            return

        if event.type == pg.KEYDOWN:
            if event.key in self.TOWER_TYPE_KEYS:
                self._selected_tower_type = self.TOWER_TYPE_KEYS[event.key]
            elif event.key == pg.K_SPACE:
                self._wave_skip_requested = True

    def consume_wave_skip(self) -> bool:
        """ウェーブ早期開始リクエストを取り出して消費する。"""
        if not self._wave_skip_requested:
            return False
        self._wave_skip_requested = False
        return True

    # ----- internal helpers -----

    def _try_place_tower(self, world: World, pos: tuple[int, int]) -> bool:
        fpos = (float(pos[0]), float(pos[1]))
        if self._gold < self._tower_cost:
            return False
        if not world.can_place_tower(fpos):
            return False
        factory = self._tower_factories.get(self._selected_tower_type, BaseTower)
        tower = factory(pos=fpos, purchase_cost=self._tower_cost)
        world.add_tower(tower)
        self._gold -= self._tower_cost
        world.get_sound().play_se(SE_TOWER_PLACE)
        return True

    def _select_tower_at(self, world: World, pos: tuple[int, int]) -> None:
        x, y = float(pos[0]), float(pos[1])
        nearest: BaseTower | None = None
        nearest_dist = float("inf")
        for tower in world.get_towers():
            tx, ty = tower.get_pos()
            d = (tx - x) ** 2 + (ty - y) ** 2
            if d < nearest_dist:
                nearest_dist = d
                nearest = tower
        # 近接判定（半径 24 以内）
        if nearest is not None and nearest_dist <= 24.0 * 24.0:
            self._selected_tower = nearest
        else:
            self._selected_tower = None

    # ----- per-frame -----

    def update(self, input_state: dict) -> None:
        """建築役は基本的に移動しない。インタフェース整合のための no-op。"""
        _ = input_state

    def draw(self, screen: pg.Surface) -> None:
        """Surface に描画する。"""
        super().draw(screen)
        x, y = int(self._pos[0]), int(self._pos[1])
        pg.draw.rect(
            screen,
            COLOR_PLAYER,
            (
                x - self.DEFAULT_RADIUS,
                y - self.DEFAULT_RADIUS,
                self.DEFAULT_RADIUS * 2,
                self.DEFAULT_RADIUS * 2,
            ),
            width=2,
        )
