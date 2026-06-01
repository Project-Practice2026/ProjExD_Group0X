"""タワー選択 UI。

画面下部に 4 属性のアイコン（hotbar）を並べ、選択中の属性をハイライトする。
マウス位置にゴーストプレビューを描画し、`World.can_place_tower` の結果で
色（白系 / 赤）を切り替える。
"""

from __future__ import annotations

from typing import ClassVar

import pygame as pg

from core.builder import Builder
from core.constants import (
    COLOR_FIRE,
    COLOR_ICE,
    COLOR_LIGHTNING,
    COLOR_PHYSICAL,
    COLOR_TEXT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.fonts import get_font
from core.world import World


class TowerSelectorUI:
    """選択中のタワー種別と設置可否を可視化する HUD。"""

    ICON_SIZE: int = 36
    ICON_GAP: int = 12
    GHOST_RADIUS: int = 14
    GHOST_ALPHA: int = 110
    BAR_BOTTOM_MARGIN: int = 12

    ELEMENT_ORDER: ClassVar[tuple[str, ...]] = ("fire", "ice", "lightning", "physical")
    ELEMENT_COLORS: ClassVar[dict[str, tuple[int, int, int]]] = {
        "fire": COLOR_FIRE,
        "ice": COLOR_ICE,
        "lightning": COLOR_LIGHTNING,
        "physical": COLOR_PHYSICAL,
    }
    ELEMENT_LABELS: ClassVar[dict[str, str]] = {
        "fire": "1",
        "ice": "2",
        "lightning": "3",
        "physical": "4",
    }

    def __init__(self) -> None:
        if not pg.font.get_init():
            pg.font.init()
        self._font: pg.font.Font = get_font(18)

    def draw(
        self,
        screen: pg.Surface,
        builder: Builder,
        world: World,
        mouse_pos: tuple[int, int] | None = None,
    ) -> None:
        """Surface に描画する。"""
        self._draw_hotbar(screen, builder.get_selected_tower_type())
        if mouse_pos is not None:
            self._draw_ghost(
                screen,
                builder=builder,
                world=world,
                mouse_pos=mouse_pos,
            )

    def _draw_hotbar(self, screen: pg.Surface, selected: str) -> None:
        total_width = (
            len(self.ELEMENT_ORDER) * self.ICON_SIZE + (len(self.ELEMENT_ORDER) - 1) * self.ICON_GAP
        )
        start_x = (SCREEN_WIDTH - total_width) // 2
        y = SCREEN_HEIGHT - self.ICON_SIZE - self.BAR_BOTTOM_MARGIN

        for index, element in enumerate(self.ELEMENT_ORDER):
            x = start_x + index * (self.ICON_SIZE + self.ICON_GAP)
            color = self.ELEMENT_COLORS[element]
            rect = pg.Rect(x, y, self.ICON_SIZE, self.ICON_SIZE)
            pg.draw.rect(screen, color, rect)
            border_color = COLOR_TEXT if element == selected else (60, 60, 60)
            border_width = 3 if element == selected else 1
            pg.draw.rect(screen, border_color, rect, width=border_width)
            label_surface = self._font.render(self.ELEMENT_LABELS[element], True, COLOR_TEXT)
            screen.blit(
                label_surface,
                (x + 4, y + self.ICON_SIZE - label_surface.get_height() - 2),
            )

    def _draw_ghost(
        self,
        screen: pg.Surface,
        builder: Builder,
        world: World,
        mouse_pos: tuple[int, int],
    ) -> None:
        element = builder.get_selected_tower_type()
        color = self.ELEMENT_COLORS.get(element, COLOR_TEXT)
        can_place = world.can_place_tower((float(mouse_pos[0]), float(mouse_pos[1])))
        ghost_color = color if can_place else (220, 70, 70)
        try:
            ghost = pg.Surface(
                (self.GHOST_RADIUS * 2, self.GHOST_RADIUS * 2),
                flags=pg.SRCALPHA,
            )
            pg.draw.circle(
                ghost,
                (*ghost_color, self.GHOST_ALPHA),
                (self.GHOST_RADIUS, self.GHOST_RADIUS),
                self.GHOST_RADIUS,
            )
            screen.blit(
                ghost,
                (mouse_pos[0] - self.GHOST_RADIUS, mouse_pos[1] - self.GHOST_RADIUS),
            )
        except (pg.error, ValueError):
            pg.draw.circle(screen, ghost_color, mouse_pos, self.GHOST_RADIUS, width=2)
