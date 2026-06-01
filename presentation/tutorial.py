"""Tutorial overlay drawing for first-time players."""

from __future__ import annotations
from core.fonts import get_font
import pygame as pg

from core.constants import (
    COLOR_TEXT,
    HUD_PANEL_BG,
    HUD_PANEL_BORDER,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TUTORIAL_BACKDROP_ALPHA,
    TUTORIAL_BODY_FONT_SIZE,
    TUTORIAL_CHECK_MARK_BOTTOM_OFFSET,
    TUTORIAL_CHECK_MARK_CENTER_OFFSET,
    TUTORIAL_CHECK_MARK_INSET,
    TUTORIAL_CHECK_MARK_WIDTH,
    TUTORIAL_CHECKBOX_BORDER_WIDTH,
    TUTORIAL_CLOSE_BUTTON_SIZE,
    TUTORIAL_LINE_HEIGHT,
    TUTORIAL_PANEL_MARGIN,
    TUTORIAL_PANEL_MAX_HEIGHT,
    TUTORIAL_PANEL_PADDING,
    TUTORIAL_PANEL_WIDTH,
    TUTORIAL_SECTION_BOTTOM_GAP,
    TUTORIAL_SECTION_FONT_SIZE,
    TUTORIAL_SECTION_TITLE_GAP,
    TUTORIAL_SKIP_CHECKBOX_SIZE,
    TUTORIAL_SKIP_LABEL_GAP,
    TUTORIAL_SKIP_ROW_BOTTOM_GAP,
    TUTORIAL_TITLE_FONT_SIZE,
    TUTORIAL_TITLE_TO_BODY_GAP,
)


class TutorialOverlay:
    """操作説明をゲーム画面に重ねて描画するオーバーレイ。"""

    PANEL_WIDTH: int = TUTORIAL_PANEL_WIDTH
    PANEL_PADDING: int = TUTORIAL_PANEL_PADDING
    PANEL_MARGIN: int = TUTORIAL_PANEL_MARGIN
    TITLE_FONT_SIZE: int = TUTORIAL_TITLE_FONT_SIZE
    SECTION_FONT_SIZE: int = TUTORIAL_SECTION_FONT_SIZE
    BODY_FONT_SIZE: int = TUTORIAL_BODY_FONT_SIZE
    LINE_HEIGHT: int = TUTORIAL_LINE_HEIGHT
    CLOSE_BUTTON_SIZE: int = TUTORIAL_CLOSE_BUTTON_SIZE
    SKIP_CHECKBOX_SIZE: int = TUTORIAL_SKIP_CHECKBOX_SIZE
    SKIP_LABEL_GAP: int = TUTORIAL_SKIP_LABEL_GAP

    def __init__(self) -> None:
        """フォントと表示状態を初期化する。"""
        if not pg.font.get_init():
            pg.font.init()
        self._title_font: pg.font.Font = get_font(None, self.TITLE_FONT_SIZE)
        self._section_font: pg.font.Font = get_font(None, self.SECTION_FONT_SIZE)
        self._body_font: pg.font.Font = get_font(None, self.BODY_FONT_SIZE)
        self._visible: bool = True
        self._skip_next_time: bool = False
        self._close_rect: pg.Rect = pg.Rect(
            0,
            0,
            self.CLOSE_BUTTON_SIZE,
            self.CLOSE_BUTTON_SIZE,
        )
        self._skip_checkbox_rect: pg.Rect = pg.Rect(
            -self.SKIP_CHECKBOX_SIZE,
            -self.SKIP_CHECKBOX_SIZE,
            self.SKIP_CHECKBOX_SIZE,
            self.SKIP_CHECKBOX_SIZE,
        )

    def is_visible(self) -> bool:
        """表示中なら True を返す。"""
        return self._visible

    def show(self) -> None:
        """オーバーレイを表示する。"""
        self._visible = True

    def hide(self) -> None:
        """オーバーレイを非表示にする。"""
        self._visible = False

    def handle_event(self, event: pg.event.Event) -> bool:
        """閉じる操作やチェック欄の操作を処理する。"""
        if not self._visible:
            return False
        if event.type == pg.KEYDOWN:
            self.hide()
            return True
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self._skip_checkbox_rect.collidepoint(event.pos):
                self.set_skip_next_time(not self.get_skip_next_time())
                return True
            self.hide()
            return True
        return False

    def get_close_rect(self) -> pg.Rect:
        """閉じるボタンの矩形を返す。"""
        return self._close_rect.copy()

    def get_skip_next_time(self) -> bool:
        """次回から自動表示しない設定が選ばれているかを返す。"""
        return self._skip_next_time

    def set_skip_next_time(self, value: bool) -> None:
        """次回から自動表示しない設定を更新する。"""
        self._skip_next_time = bool(value)

    def get_skip_checkbox_rect(self) -> pg.Rect:
        """次回から表示しないチェック欄の矩形を返す。"""
        return self._skip_checkbox_rect.copy()

    def draw(self, screen: pg.Surface) -> None:
        """半透明背景と操作説明を描画する。"""
        if not self._visible:
            return
        self._draw_backdrop(screen)
        panel_rect = self._build_panel_rect()
        self._close_rect = pg.Rect(
            panel_rect.right - self.PANEL_PADDING - self.CLOSE_BUTTON_SIZE,
            panel_rect.y + self.PANEL_PADDING,
            self.CLOSE_BUTTON_SIZE,
            self.CLOSE_BUTTON_SIZE,
        )
        pg.draw.rect(screen, HUD_PANEL_BG, panel_rect, border_radius=8)
        pg.draw.rect(screen, HUD_PANEL_BORDER, panel_rect, width=2, border_radius=8)
        self._draw_contents(screen, panel_rect)
        self._draw_close_button(screen)

    def _draw_backdrop(self, screen: pg.Surface) -> None:
        """ゲーム画面を暗くする半透明背景を描画する。"""
        overlay = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, TUTORIAL_BACKDROP_ALPHA))
        screen.blit(overlay, (0, 0))

    def _build_panel_rect(self) -> pg.Rect:
        """中央に配置する説明パネルの矩形を返す。"""
        height = min(TUTORIAL_PANEL_MAX_HEIGHT, SCREEN_HEIGHT - self.PANEL_MARGIN * 2)
        return pg.Rect(
            (SCREEN_WIDTH - self.PANEL_WIDTH) // 2,
            (SCREEN_HEIGHT - height) // 2,
            self.PANEL_WIDTH,
            height,
        )

    def _draw_contents(self, screen: pg.Surface, panel_rect: pg.Rect) -> None:
        """説明文をパネル内に描画する。"""
        x = panel_rect.x + self.PANEL_PADDING
        y = panel_rect.y + self.PANEL_PADDING
        title = self._title_font.render("操作説明", True, COLOR_TEXT)
        screen.blit(title, (x, y))
        y += TUTORIAL_TITLE_TO_BODY_GAP

        sections = [
            (
                "プレイヤー1 / 建築担当",
                [
                    "1-4: タワーの種類を選択",
                    "左クリック: タワーを配置",
                    "右クリック: タワーを選択",
                    "Space: 次のウェーブを開始",
                ],
            ),
            (
                "プレイヤー 2 / 戦闘担当",
                [
                    "WASD: キャラクター移動",
                    "Shift: ダッシュ",
                    "J: 通常攻撃",
                    "K: スキルを使用",
                    "L: 近くのタワーを修理",
                ],
            ),
            (
                "共通武器 / スキル切り替え",
                [
                    "Q / E: 武器切り替え",
                    "5 / 6: スキル切り替え",
                ],
            ),
        ]

        for heading, lines in sections:
            heading_surface = self._section_font.render(heading, True, COLOR_TEXT)
            screen.blit(heading_surface, (x, y))
            y += TUTORIAL_SECTION_TITLE_GAP
            for line in lines:
                body_surface = self._body_font.render(line, True, COLOR_TEXT)
                screen.blit(body_surface, (x + 18, y))
                y += self.LINE_HEIGHT
            y += TUTORIAL_SECTION_BOTTOM_GAP

        self._draw_skip_option(screen, panel_rect)
        hint = self._body_font.render("任意のキーを押すか、クリックで閉じる", True, COLOR_TEXT)
        hint_rect = hint.get_rect(
            bottomleft=(
                panel_rect.x + self.PANEL_PADDING,
                panel_rect.bottom - self.PANEL_PADDING,
            )
        )
        screen.blit(hint, hint_rect)

    def _draw_skip_option(self, screen: pg.Surface, panel_rect: pg.Rect) -> None:
        """次回から表示しないチェック欄を描画する。"""
        x = panel_rect.x + self.PANEL_PADDING
        y = panel_rect.bottom - self.PANEL_PADDING - TUTORIAL_SKIP_ROW_BOTTOM_GAP
        self._skip_checkbox_rect = pg.Rect(
            x,
            y,
            self.SKIP_CHECKBOX_SIZE,
            self.SKIP_CHECKBOX_SIZE,
        )
        pg.draw.rect(
            screen,
            HUD_PANEL_BORDER,
            self._skip_checkbox_rect,
            width=TUTORIAL_CHECKBOX_BORDER_WIDTH,
        )
        if self._skip_next_time:
            start = (
                self._skip_checkbox_rect.left + TUTORIAL_CHECK_MARK_INSET,
                self._skip_checkbox_rect.centery,
            )
            middle = (
                self._skip_checkbox_rect.centerx - TUTORIAL_CHECK_MARK_CENTER_OFFSET,
                self._skip_checkbox_rect.bottom - TUTORIAL_CHECK_MARK_BOTTOM_OFFSET,
            )
            end = (
                self._skip_checkbox_rect.right - TUTORIAL_CHECK_MARK_INSET,
                self._skip_checkbox_rect.top + TUTORIAL_CHECK_MARK_INSET,
            )
            pg.draw.lines(
                screen,
                COLOR_TEXT,
                False,
                [start, middle, end],
                TUTORIAL_CHECK_MARK_WIDTH,
            )
        label = self._body_font.render("次回から表示しない", True, COLOR_TEXT)
        label_rect = label.get_rect(
            midleft=(
                self._skip_checkbox_rect.right + self.SKIP_LABEL_GAP,
                self._skip_checkbox_rect.centery,
            )
        )
        screen.blit(label, label_rect)

    def _draw_close_button(self, screen: pg.Surface) -> None:
        """閉じるボタンを描画する。"""
        pg.draw.rect(screen, HUD_PANEL_BORDER, self._close_rect, border_radius=4)
        label = self._body_font.render("X", True, COLOR_TEXT)
        screen.blit(label, label.get_rect(center=self._close_rect.center))
