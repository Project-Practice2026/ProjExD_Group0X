"""詳細 HUD（BaseHud 拡張）。

`BaseHud` を継承し、`game_state` に追加キー（`selected_tower` / `skills` /
`best_fitness` / `opponent_core_hp` 等）が含まれていればパネル化して描画する。
"""

from __future__ import annotations

import pygame as pg

try:
    from ..core.base_hud import BaseHud
    from ..core.constants import (
        COLOR_HP_BAR_BG,
        COLOR_TEXT,
        HUD_OPPONENT_BAR_FG,
        HUD_PANEL_BG,
        HUD_PANEL_BORDER,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
    )
except ImportError:
    from core.base_hud import BaseHud
    from core.constants import (
        COLOR_HP_BAR_BG,
        COLOR_TEXT,
        HUD_OPPONENT_BAR_FG,
        HUD_PANEL_BG,
        HUD_PANEL_BORDER,
        SCREEN_HEIGHT,
        SCREEN_WIDTH,
    )

from core.fonts import get_font


class ExtendedHud(BaseHud):
    """詳細表示版 HUD。"""

    PANEL_WIDTH: int = 200
    PANEL_PADDING: int = 6
    PANEL_LINE_HEIGHT: int = 16
    SKILL_ICON_SIZE: int = 22
    SKILL_ICON_GAP: int = 6
    OPPONENT_BAR_WIDTH: int = 220
    OPPONENT_BAR_HEIGHT: int = 12

    def __init__(self) -> None:
        super().__init__()
        if not pg.font.get_init():
            pg.font.init()
        self._panel_font: pg.font.Font = get_font(16)

    # 既存 API（後方互換）
    def set_status(self, wave: int, money: int) -> None:
        # 旧呼出はメッセージリストに残す（未使用キーは無視）
        """Status を設定する。"""
        self.messages = [f"wave={wave}", f"money={money}"]

    def draw(self, screen: pg.Surface, game_state: dict) -> None:
        """基本 HUD に加え、選択中タワー・スキル・対戦相手 HP・進化最強値を描画。"""
        super().draw(screen, game_state)

        # 右下にタワー詳細パネル（選択中のみ）
        self._draw_selected_tower_panel(screen, game_state.get("selected_tower"))
        # 左下にスキルアイコン
        self._draw_skill_icons(screen, game_state.get("skills") or [])
        # 上部中央に「ベスト適応度」表示
        self._draw_best_fitness(screen, game_state.get("best_fitness"))
        # 右上下段に相手の拠点HP（対戦時）
        self._draw_opponent_hp(
            screen,
            game_state.get("opponent_core_hp"),
            game_state.get("opponent_core_max_hp"),
        )

    # ----- internal -----

    def _draw_selected_tower_panel(
        self,
        screen: pg.Surface,
        tower_info: dict | None,
    ) -> None:
        if not tower_info:
            return
        lines = [
            f"Tower: {tower_info.get('element', 'base').upper()}",
            f" Lv  : {int(tower_info.get('level', 1))}",
            f" DMG : {int(tower_info.get('damage', 0))}",
            f" RNG : {int(tower_info.get('range', 0))}",
            f" CD  : {float(tower_info.get('cooldown', 0.0)):.2f}s",
            f" Cost: {int(tower_info.get('cost', 0))}",
        ]
        height = self.PANEL_PADDING * 2 + self.PANEL_LINE_HEIGHT * len(lines)
        x = SCREEN_WIDTH - self.PANEL_WIDTH - self.MARGIN
        y = SCREEN_HEIGHT - height - self.MARGIN - self.SKILL_ICON_SIZE - 20
        rect = pg.Rect(x, y, self.PANEL_WIDTH, height)
        pg.draw.rect(screen, HUD_PANEL_BG, rect)
        pg.draw.rect(screen, HUD_PANEL_BORDER, rect, width=1)
        for i, line in enumerate(lines):
            surface = self._panel_font.render(line, True, COLOR_TEXT)
            screen.blit(
                surface,
                (
                    x + self.PANEL_PADDING,
                    y + self.PANEL_PADDING + i * self.PANEL_LINE_HEIGHT,
                ),
            )

    def _draw_skill_icons(
        self,
        screen: pg.Surface,
        skills: list[dict],
    ) -> None:
        if not skills:
            return
        x = self.MARGIN
        y = SCREEN_HEIGHT - self.SKILL_ICON_SIZE - self.MARGIN
        for skill in skills:
            cd = float(skill.get("cooldown", 0.0)) or 1.0
            cd_left = float(skill.get("cooldown_left", 0.0))
            active = bool(skill.get("active", False))
            color = (140, 200, 255) if active else (200, 200, 200)
            rect = pg.Rect(x, y, self.SKILL_ICON_SIZE, self.SKILL_ICON_SIZE)
            pg.draw.rect(screen, color, rect)
            pg.draw.rect(screen, HUD_PANEL_BORDER, rect, width=1)
            # クールタイム表示
            if cd_left > 0:
                ratio = max(0.0, min(1.0, cd_left / cd))
                overlay_h = int(self.SKILL_ICON_SIZE * ratio)
                pg.draw.rect(
                    screen,
                    (0, 0, 0),
                    (x, y, self.SKILL_ICON_SIZE, overlay_h),
                )
            # ラベル
            label = self._panel_font.render(
                str(skill.get("name", "?"))[:4],
                True,
                COLOR_TEXT,
            )
            screen.blit(label, (x, y + self.SKILL_ICON_SIZE + 2))
            x += self.SKILL_ICON_SIZE + self.SKILL_ICON_GAP

    def _draw_best_fitness(
        self,
        screen: pg.Surface,
        best_fitness: float | None,
    ) -> None:
        if best_fitness is None:
            return
        text = f"Best Fitness: {float(best_fitness):.1f}"
        surface = self._panel_font.render(text, True, COLOR_TEXT)
        rect = surface.get_rect(midtop=(SCREEN_WIDTH // 2, self.MARGIN))
        screen.blit(surface, rect)

    def _draw_opponent_hp(
        self,
        screen: pg.Surface,
        opponent_hp: int | None,
        opponent_max_hp: int | None,
    ) -> None:
        if opponent_hp is None:
            return
        max_hp = int(opponent_max_hp) if opponent_max_hp else 1000
        bar_x = SCREEN_WIDTH - self.OPPONENT_BAR_WIDTH - self.MARGIN
        bar_y = self.MARGIN + 30
        pg.draw.rect(
            screen,
            COLOR_HP_BAR_BG,
            (bar_x, bar_y, self.OPPONENT_BAR_WIDTH, self.OPPONENT_BAR_HEIGHT),
        )
        ratio = max(0.0, min(1.0, opponent_hp / max_hp if max_hp > 0 else 0.0))
        fg_width = int(self.OPPONENT_BAR_WIDTH * ratio)
        if fg_width > 0:
            pg.draw.rect(
                screen,
                HUD_OPPONENT_BAR_FG,
                (bar_x, bar_y, fg_width, self.OPPONENT_BAR_HEIGHT),
            )
        label = self._panel_font.render(
            f"Opp HP {opponent_hp}/{max_hp}",
            True,
            COLOR_TEXT,
        )
        screen.blit(label, (bar_x, bar_y + self.OPPONENT_BAR_HEIGHT + 2))
