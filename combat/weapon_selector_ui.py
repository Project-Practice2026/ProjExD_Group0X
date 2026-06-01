"""武器切替 UI。

前線役プレイヤー近辺に現在装備中の武器アイコンと残クールタイムを表示する。
Q/E キーによる切替は `Fighter` 側でハンドリング。
"""

from __future__ import annotations

import pygame as pg

from core.fonts import get_font

try:
    from ..core.base_player import BasePlayer
    from ..core.constants import COLOR_TEXT
    from .weapons import BaseWeapon
except ImportError:
    from combat.weapons import BaseWeapon
    from core.base_player import BasePlayer
    from core.constants import COLOR_TEXT


class WeaponSelectorUI:
    """現在装備中の武器アイコンと残クールタイムを描画する。"""

    ICON_SIZE: int = 26
    OFFSET_Y: int = -32

    def __init__(self) -> None:
        if not pg.font.get_init():
            pg.font.init()
        self._font: pg.font.Font = get_font(16)

    def draw(
        self,
        screen: pg.Surface,
        fighter: BasePlayer,
        weapon: BaseWeapon,
    ) -> None:
        """Surface に描画する。"""
        x, y = fighter.get_pos()
        pos = (int(x) - self.ICON_SIZE // 2, int(y) + self.OFFSET_Y)
        weapon.draw_icon(screen, pos, self.ICON_SIZE, highlight=True)
        # 名前ラベル
        label = self._font.render(weapon.get_name().upper(), True, COLOR_TEXT)
        screen.blit(label, (pos[0], pos[1] - 14))
        # クールタイム残り
        if weapon.get_cooldown_left() > 0 and weapon.get_cooldown() > 0:
            ratio = weapon.get_cooldown_left() / weapon.get_cooldown()
            bar_w = self.ICON_SIZE
            bar_h = 3
            bar_x = pos[0]
            bar_y = pos[1] + self.ICON_SIZE + 2
            pg.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))
            pg.draw.rect(
                screen,
                (220, 220, 80),
                (bar_x, bar_y, int(bar_w * (1.0 - ratio)), bar_h),
            )
