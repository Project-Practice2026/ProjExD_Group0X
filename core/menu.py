"""起動時のモード選択メニューシーン。

引数なし起動時に表示し、Solo / Host / Client / Versus / Tutorial / Quit から選ばせる。
`run()` は選択結果の文字列（"solo" / "host" / "client" / "versus" / "tutorial" / "quit"）を返す。
実際のゲーム起動は呼び出し側（main.py）が行う。

単体での動作確認はリポジトリルートで `python -m core.menu` を使う。
（`python core/menu.py` は相対 import が解決できず ImportError になるため不可。）

フォントは HUD と同じ `pg.font.SysFont(None, ...)` 方式。日本語フォント未配置だと
文字化けし得る（Issue #111）ため、選択肢ラベルは ASCII にしている。
"""

from __future__ import annotations

import pygame as pg

from .constants import COLOR_BG, COLOR_TEXT, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, SERVER_HOST

# 選択肢: (戻り値, 表示ラベル)
MENU_OPTIONS: list[tuple[str, str]] = [
    ("solo", "ソロプレイ  (1台 / 2人操作)"),
    ("host", "ホスト起動  (プレイヤー1)"),
    ("client", "クライアント接続  (プレイヤー2)"),
    ("versus", "対戦モード  (1台 / 2画面)"),
    ("tutorial", "チュートリアル  (操作説明)"),
    ("quit", "ゲーム終了"),
]


class MenuScene:
    """モード選択メニュー。`run()` で選択結果の文字列を返す。

    描画に依存しない選択ロジック（`move_cursor` / `get_selected_value` /
    `set_index_from_mouse` / `handle_event`）は display なしでも動作するため、
    単体テストしやすい。
    """

    TITLE: str = "共進化砦"
    TITLE_FONT_SIZE: int = 48
    OPTION_FONT_SIZE: int = 32
    HINT_FONT_SIZE: int = 20
    OPTION_GAP: int = 56
    COLOR_SELECTED: tuple[int, int, int] = (255, 220, 120)
    HINT: str = "[↑↓] 選択   [Enter] 決定   [Esc] 終了"

    def __init__(
        self,
        screen: pg.Surface | None = None,
        options: list[tuple[str, str]] | None = None,
    ) -> None:
        if not pg.font.get_init():
            pg.font.init()
        self._screen: pg.Surface | None = screen
        self._clock: pg.time.Clock = pg.time.Clock()
        self._options: list[tuple[str, str]] = (
            list(options) if options is not None else list(MENU_OPTIONS)
        )
        self._index: int = 0
        self._title_font: pg.font.Font = pg.font.SysFont(None, self.TITLE_FONT_SIZE)
        self._option_font: pg.font.Font = pg.font.SysFont(None, self.OPTION_FONT_SIZE)
        self._hint_font: pg.font.Font = pg.font.SysFont(None, self.HINT_FONT_SIZE)

    # ----- selection logic（display 非依存） -----

    def get_index(self) -> int:
        """現在の選択インデックスを返す。"""
        return self._index

    def move_cursor(self, delta: int) -> None:
        """選択カーソルを delta だけ動かす（端で循環する）。"""
        self._index = (self._index + delta) % len(self._options)

    def get_selected_value(self) -> str:
        """現在の選択肢の戻り値文字列を返す。"""
        return self._options[self._index][0]

    def set_index_from_mouse(self, mouse_pos: tuple[int, int]) -> bool:
        """マウス座標が選択肢に重なればその index に移動する。

        Returns:
            いずれかの選択肢に重なった場合 True。
        """
        for i, rect in enumerate(self._option_rects()):
            if rect.collidepoint(mouse_pos):
                self._index = i
                return True
        return False

    def handle_event(self, event: pg.event.Event) -> str | None:
        """1 イベントを処理する。決定されたら選択値を返し、未決定なら None。"""
        if event.type == pg.QUIT:
            return "quit"
        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_UP, pg.K_w):
                self.move_cursor(-1)
            elif event.key in (pg.K_DOWN, pg.K_s):
                self.move_cursor(1)
            elif event.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_SPACE):
                return self.get_selected_value()
            elif event.key == pg.K_ESCAPE:
                return "quit"
        elif event.type == pg.MOUSEMOTION:
            self.set_index_from_mouse(event.pos)
        elif (
            event.type == pg.MOUSEBUTTONDOWN
            and event.button == 1
            and self.set_index_from_mouse(event.pos)
        ):
            return self.get_selected_value()
        return None

    # ----- layout / draw -----

    def _option_rects(self) -> list[pg.Rect]:
        """各選択肢の描画矩形（中央揃え）を返す。"""
        rects: list[pg.Rect] = []
        start_y = SCREEN_HEIGHT // 2 - (len(self._options) - 1) * self.OPTION_GAP // 2
        for i, (_value, label) in enumerate(self._options):
            surf = self._option_font.render(label, True, COLOR_TEXT)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * self.OPTION_GAP))
            rects.append(rect)
        return rects

    def draw(self, screen: pg.Surface) -> None:
        """タイトル・選択肢・操作ヒントを描画する。"""
        screen.fill(COLOR_BG)
        title = self._title_font.render(self.TITLE, True, COLOR_TEXT)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4)))

        rects = self._option_rects()
        for i, (_value, label) in enumerate(self._options):
            color = self.COLOR_SELECTED if i == self._index else COLOR_TEXT
            surf = self._option_font.render(label, True, color)
            screen.blit(surf, rects[i])

        hint = self._hint_font.render(self.HINT, True, COLOR_TEXT)
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 48)))

    # ----- run loop -----

    def run(self) -> str:
        """メニューを表示し、選択された値の文字列を返す。"""
        if self._screen is None:
            self._screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        while True:
            self._clock.tick(FPS)
            for event in pg.event.get():
                result = self.handle_event(event)
                if result is not None:
                    return result
            self.draw(self._screen)
            pg.display.flip()


def is_valid_ipv4(text: str) -> bool:
    """4 オクテット・各 0〜255 の IPv4 文字列なら True を返す。

    先頭ゼロ付き（"010" 等）は socket 解決で 8 進数と解釈され得て曖昧なため拒否する
    （"0" 単独は許容）。これにより `010.0.0.1` が誤って 8.0.0.1 に解決されるのを防ぐ。
    """
    parts = text.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        if len(part) > 1 and part[0] == "0":  # 先頭ゼロ禁止（"0" は可）
            return False
        if not (0 <= int(part) <= 255):
            return False
    return True


class IpInputScene:
    """接続先ホスト IP を入力するシーン。

    `run()` は確定した IP 文字列、または取消（Esc / QUIT）時に None を返す。
    入力ロジック（`insert_char` / `backspace` / `try_confirm`）は display 非依存で
    単体テストしやすい。
    """

    PROMPT: str = "接続先ホストの IP アドレスを入力してください"
    HINT: str = "[0-9 .] 入力 [Backspace] 削除 [Enter] 接続 [Esc] 戻る"
    INPUT_FONT_SIZE: int = 40
    LABEL_FONT_SIZE: int = 24
    MAX_LENGTH: int = 15  # "255.255.255.255"
    COLOR_ERROR: tuple[int, int, int] = (240, 110, 90)
    COLOR_CARET: tuple[int, int, int] = (255, 220, 120)

    def __init__(self, screen: pg.Surface | None = None, initial_ip: str = SERVER_HOST) -> None:
        if not pg.font.get_init():
            pg.font.init()
        self._screen: pg.Surface | None = screen
        self._clock: pg.time.Clock = pg.time.Clock()
        self._text: str = initial_ip
        self._error: str = ""
        self._input_font: pg.font.Font = pg.font.SysFont(None, self.INPUT_FONT_SIZE)
        self._label_font: pg.font.Font = pg.font.SysFont(None, self.LABEL_FONT_SIZE)

    # ----- input logic（display 非依存） -----

    def get_text(self) -> str:
        """現在の入力文字列を返す。"""
        return self._text

    def get_error(self) -> str:
        """直近の検証エラーメッセージ（なければ空文字）を返す。"""
        return self._error

    def insert_char(self, ch: str) -> None:
        """数字または '.' を 1 文字末尾に追加する（文字種・長さを制限）。"""
        if len(self._text) >= self.MAX_LENGTH:
            return
        if ch.isdigit() or ch == ".":
            self._text += ch
            self._error = ""

    def backspace(self) -> None:
        """末尾を 1 文字削除する。"""
        self._text = self._text[:-1]
        self._error = ""

    def try_confirm(self) -> str | None:
        """確定を試みる。妥当なら IP 文字列を返し、無効ならエラーを設定して None。"""
        if is_valid_ipv4(self._text):
            return self._text
        self._error = "無効なIPアドレス形式です(例: 192.168.1.10)"
        return None

    def handle_event(self, event: pg.event.Event) -> tuple[bool, str | None]:
        """1 イベントを処理する。

        Returns:
            (done, ip): done=True で終了。ip が文字列なら確定、None なら取消。
        """
        if event.type == pg.QUIT:
            return True, None
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                return True, None
            if event.key in (pg.K_RETURN, pg.K_KP_ENTER):
                ip = self.try_confirm()
                return (ip is not None), ip
            if event.key == pg.K_BACKSPACE:
                self.backspace()
            elif event.unicode:
                self.insert_char(event.unicode)
        return False, None

    # ----- draw -----

    def draw(self, screen: pg.Surface) -> None:
        """プロンプト・入力欄・エラー・操作ヒントを描画する。"""
        screen.fill(COLOR_BG)
        center_x = SCREEN_WIDTH // 2

        prompt = self._label_font.render(self.PROMPT, True, COLOR_TEXT)
        screen.blit(prompt, prompt.get_rect(center=(center_x, SCREEN_HEIGHT // 2 - 60)))

        caret = "_" if (pg.time.get_ticks() // 500) % 2 == 0 else " "
        field = self._input_font.render(self._text + caret, True, self.COLOR_CARET)
        screen.blit(field, field.get_rect(center=(center_x, SCREEN_HEIGHT // 2)))

        if self._error:
            err = self._label_font.render(self._error, True, self.COLOR_ERROR)
            screen.blit(err, err.get_rect(center=(center_x, SCREEN_HEIGHT // 2 + 50)))

        hint = self._label_font.render(self.HINT, True, COLOR_TEXT)
        screen.blit(hint, hint.get_rect(center=(center_x, SCREEN_HEIGHT - 48)))

    # ----- run loop -----

    def run(self) -> str | None:
        """IP 入力画面を表示し、確定した IP 文字列（取消時は None）を返す。"""
        if self._screen is None:
            self._screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        while True:
            self._clock.tick(FPS)
            for event in pg.event.get():
                done, ip = self.handle_event(event)
                if done:
                    return ip
            self.draw(self._screen)
            pg.display.flip()


if __name__ == "__main__":
    # 単体起動はリポジトリルートで `python -m core.menu`（直接 `python core/menu.py`
    # は相対 import が解決できないため不可）。
    pg.init()
    selected = MenuScene().run()
    if selected == "client":
        ip_result = IpInputScene().run()
        print(f"selected: {selected}  ip: {ip_result}")
    else:
        print(f"selected: {selected}")
    pg.quit()
