"""クライアントゲーム（描画専用）。

`Game` を継承し、`NetClient` 経由でホストから受信した state を `StateBuffer` で
60FPS に補間してそのまま画面に描く。ローカル入力は `NET_INPUT_HZ` でホストに
送信する。ゲームロジックは持たない（権威サーバ＝ホスト側）。

DESIGN.md §2.5（補間）と §2.6（接続の流れ）に準拠。
"""

from __future__ import annotations

import time
from typing import Any

import pygame as pg

from core.fonts import get_font
from network.net_client import NetClient
from network.state_buffer import StateBuffer

from .constants import (
    CLIENT_CONNECTION_FAIL_WAIT_SEC,
    CLIENT_CONNECTION_FAILED_HINT_Y_OFFSET,
    CLIENT_CONNECTION_FAILED_TITLE_Y_OFFSET,
    CLIENT_DEFAULT_BULLET_RADIUS,
    CLIENT_DEFAULT_ENEMY_RADIUS,
    CLIENT_DEFAULT_FORTRESS_RADIUS,
    CLIENT_DEFAULT_PLAYER_RADIUS,
    CLIENT_DEFAULT_TOWER_RADIUS,
    CLIENT_FONT_SIZE,
    CLIENT_HP_BAR_HEIGHT,
    CLIENT_HP_BAR_WIDTH,
    CLIENT_OVERLAY_TEXT_X_GAP,
    CLIENT_OVERLAY_TEXT_Y_OFFSET,
    CLIENT_OVERLAY_X,
    CLIENT_OVERLAY_Y,
    CLIENT_WAIT_FPS,
    CLIENT_WAITING_TEXT_Y_OFFSET,
    COLOR_BG,
    COLOR_BULLET,
    COLOR_ENEMY,
    COLOR_FORTRESS,
    COLOR_HP_BAR_BG,
    COLOR_HP_BAR_FG,
    COLOR_PLAYER,
    COLOR_TEXT,
    COLOR_TOWER,
    FORTRESS_MAX_HP,
    FORTRESS_X_RATIO,
    FORTRESS_Y_RATIO,
    NET_CONNECT_TIMEOUT_SEC,
    NET_INPUT_HZ,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SERVER_HOST,
    SERVER_PORT,
)
from .game import Game


class ClientGame(Game):
    """描画専用クライアント。"""

    def __init__(
        self,
        host: str = SERVER_HOST,
        port: int = SERVER_PORT,
        name: str = "player2",
        input_hz: int = NET_INPUT_HZ,
    ) -> None:
        """クライアントを初期化する。

        Args:
            host: 接続先ホストの IP。
            port: 接続先ポート番号。
            name: ハンドシェイクで送る名前。
            input_hz: 入力送信周波数（既定 30Hz）。
        """
        super().__init__()
        self._client: NetClient = NetClient(host=host, port=port, name=name)
        self._state_buffer: StateBuffer = StateBuffer()
        self._input_interval: float = 1.0 / max(1, int(input_hz))
        self._time_since_input: float = 0.0
        self._connection_lost: bool = False
        self._latest_seq: int = -1
        if not pg.font.get_init():
            pg.font.init()
        self._font: pg.font.Font = get_font(CLIENT_FONT_SIZE)

    # ----- accessors -----

    def get_client(self) -> NetClient:
        """Client を返す。"""
        return self._client

    def get_state_buffer(self) -> StateBuffer:
        """State_buffer を返す。"""
        return self._state_buffer

    def is_connection_lost(self) -> bool:
        """Connection_lost かどうかを返す。"""
        return self._connection_lost

    # ----- lifecycle -----

    def connect(self, timeout: float = NET_CONNECT_TIMEOUT_SEC) -> bool:
        """ホストへ接続要求を送り、connect_ok を待つ。"""
        return self._client.connect(timeout=timeout)

    def stop(self) -> None:
        """メインループ停止と NetClient の終了。"""
        super().stop()
        self._client.stop()

    def run(self) -> None:
        """メインループ。接続失敗時は即終了。"""
        if not self.connect():
            try:
                self._draw_connection_failed()
                pg.display.flip()
                self._wait_brief()
            finally:
                self.stop()
                pg.quit()
            return
        try:
            super().run()
        finally:
            self._client.stop()

    # ----- per-frame -----

    def update(self, dt: float) -> None:
        """State 受信 → 補間バッファへ push、入力送信、ハートビート更新。"""
        # 受信した state をバッファに蓄積
        latest = self._client.poll_state()
        if latest is not None:
            seq = int(latest.get("seq", 0))
            if seq > self._latest_seq:
                self._state_buffer.push(time.monotonic(), latest)
                self._latest_seq = seq

        # ハートビート / 再送 / タイムアウト判定
        self._client.update()
        if self._client.has_lost_connection():
            self._connection_lost = True
            self._running = False
            return

        # 入力送信（30Hz）
        self._time_since_input += dt
        if self._time_since_input >= self._input_interval:
            self._time_since_input = 0.0
            self._send_local_input()

    def draw(self) -> None:
        """補間 state を取り出してエンティティを描画する。"""
        state = self._state_buffer.get_interpolated(time.monotonic())
        self._screen.fill(COLOR_BG)
        if state is None:
            # Game.run() が draw() 後に flip するため、早期 return でも表示される。
            self._blit_centered("Waiting for host...", y_offset=CLIENT_WAITING_TEXT_Y_OFFSET)
            return
        self._draw_fortress(state)
        self._draw_towers(state)
        self._draw_enemies(state)
        self._draw_players(state)
        self._draw_bullets(state)
        self._draw_overlay(state)

    # ----- input ↓ -----

    def _send_local_input(self) -> None:
        """ローカルキー入力を input メッセージにして送信する。"""
        if not self._client.is_connected():
            return
        keys = pg.key.get_pressed()
        dx = (1 if keys[pg.K_d] else 0) - (1 if keys[pg.K_a] else 0)
        dy = (1 if keys[pg.K_s] else 0) - (1 if keys[pg.K_w] else 0)
        payload: dict[str, Any] = {
            "move": [float(dx), float(dy)],
            "attack": bool(keys[pg.K_j]),
            "skill": bool(keys[pg.K_k]),
        }
        self._client.send_input(payload)

    # ----- draw helpers -----

    def _draw_fortress(self, state: dict[str, Any]) -> None:
        """ホスト側の拠点と同じ右側中央位置へプレースホルダーを描く。"""
        _ = state  # state は将来 fortress 座標を含めた時の予約
        fortress_pos = (SCREEN_WIDTH * FORTRESS_X_RATIO, SCREEN_HEIGHT * FORTRESS_Y_RATIO)
        pg.draw.circle(
            self._screen,
            COLOR_FORTRESS,
            (int(fortress_pos[0]), int(fortress_pos[1])),
            CLIENT_DEFAULT_FORTRESS_RADIUS,
        )

    def _draw_towers(self, state: dict[str, Any]) -> None:
        """State 内のタワー一覧を小さな円で描く。"""
        for tower in state.get("towers", []):
            if not isinstance(tower, dict):
                continue
            pos = tower.get("pos") or [0, 0]
            pg.draw.circle(
                self._screen,
                COLOR_TOWER,
                (int(pos[0]), int(pos[1])),
                CLIENT_DEFAULT_TOWER_RADIUS,
            )

    def _draw_enemies(self, state: dict[str, Any]) -> None:
        """State 内の敵一覧を補間済み座標へ描く。"""
        for enemy in state.get("enemies", []):
            if not isinstance(enemy, dict):
                continue
            pos = enemy.get("pos") or [0, 0]
            pg.draw.circle(
                self._screen,
                COLOR_ENEMY,
                (int(pos[0]), int(pos[1])),
                CLIENT_DEFAULT_ENEMY_RADIUS,
            )

    def _draw_players(self, state: dict[str, Any]) -> None:
        """State 内のプレイヤー一覧を描く。"""
        for player in state.get("players", []):
            if not isinstance(player, dict):
                continue
            pos = player.get("pos") or [0, 0]
            pg.draw.circle(
                self._screen,
                COLOR_PLAYER,
                (int(pos[0]), int(pos[1])),
                CLIENT_DEFAULT_PLAYER_RADIUS,
            )

    def _draw_bullets(self, state: dict[str, Any]) -> None:
        """State 内の弾一覧を描く。"""
        for bullet in state.get("bullets", []):
            if not isinstance(bullet, dict):
                continue
            pos = bullet.get("pos") or [0, 0]
            pg.draw.circle(
                self._screen,
                COLOR_BULLET,
                (int(pos[0]), int(pos[1])),
                CLIENT_DEFAULT_BULLET_RADIUS,
            )

    def _draw_overlay(self, state: dict[str, Any]) -> None:
        """拠点 HP バーと簡易ステータステキストを画面左上に描く。"""
        max_hp = max(1, int(state.get("core_max_hp", FORTRESS_MAX_HP)))
        hp = max(0, int(state.get("fortress_hp", 0)))
        bar_x, bar_y = CLIENT_OVERLAY_X, CLIENT_OVERLAY_Y
        pg.draw.rect(
            self._screen,
            COLOR_HP_BAR_BG,
            (bar_x, bar_y, CLIENT_HP_BAR_WIDTH, CLIENT_HP_BAR_HEIGHT),
        )
        ratio = hp / max_hp
        fg_width = int(CLIENT_HP_BAR_WIDTH * ratio)
        if fg_width > 0:
            pg.draw.rect(
                self._screen,
                COLOR_HP_BAR_FG,
                (bar_x, bar_y, fg_width, CLIENT_HP_BAR_HEIGHT),
            )
        wave = int(state.get("wave", 0))
        pid = self._client.get_player_id()
        self._blit_text(
            f"Core HP {hp}  Wave {wave}  Player {pid}",
            (
                bar_x + CLIENT_HP_BAR_WIDTH + CLIENT_OVERLAY_TEXT_X_GAP,
                bar_y + CLIENT_OVERLAY_TEXT_Y_OFFSET,
            ),
        )

    def _draw_connection_failed(self) -> None:
        """接続失敗時の短い案内を描く。"""
        self._screen.fill(COLOR_BG)
        self._blit_centered(
            "Failed to connect to host.",
            y_offset=CLIENT_CONNECTION_FAILED_TITLE_Y_OFFSET,
        )
        self._blit_centered(
            "Press window close to exit.",
            y_offset=CLIENT_CONNECTION_FAILED_HINT_Y_OFFSET,
        )

    def _blit_text(self, text: str, pos: tuple[int, int]) -> None:
        """指定位置へ通常テキストを描く。"""
        surface = self._font.render(text, True, COLOR_TEXT)
        self._screen.blit(surface, pos)

    def _blit_centered(self, text: str, y_offset: int = 0) -> None:
        """画面中央から y 方向にずらしてテキストを描く。"""
        surface = self._font.render(text, True, COLOR_TEXT)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + y_offset))
        self._screen.blit(surface, rect)

    def _wait_brief(self) -> None:
        """接続失敗メッセージを短時間だけ表示する。"""
        end = time.monotonic() + CLIENT_CONNECTION_FAIL_WAIT_SEC
        while time.monotonic() < end:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    return
            self._clock.tick(CLIENT_WAIT_FPS)
