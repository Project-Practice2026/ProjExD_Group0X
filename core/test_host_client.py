"""HostGame ↔ ClientGame のループバック統合テスト。

同一プロセス内で HostGame と ClientGame を並列起動し、ハンドシェイク・state
同期・入力送信が動作することを verify する。GUI は不要（SDL_VIDEODRIVER=dummy）。
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame as pg

from core.client_game import ClientGame
from core.constants import NET_CONNECT_TIMEOUT_SEC, PLAYER_FIGHTER_ID
from core.host_game import HostGame
from network.net_protocol import MSG_INPUT


class _FailingClient:
    """ClientGame.run の接続失敗分岐用スタブ。"""

    def __init__(self) -> None:
        self.stopped: bool = False

    def connect(self, timeout: float = NET_CONNECT_TIMEOUT_SEC) -> bool:
        _ = timeout
        return False

    def stop(self) -> None:
        self.stopped = True


def _wait_until(
    predicate: Callable[[], bool],
    timeout: float = 3.0,
    step: float = 0.05,
) -> bool:
    """述語が True になるまで最大 timeout 秒待機する。"""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(step)
    return False


def _drive_host_one_frame(host: HostGame, dt: float = 1.0 / 60.0) -> None:
    """HostGame の 1 フレーム分を手動で進める（run() を使わずに verify するため）。"""
    pg.event.pump()
    host.handle_events()
    host.update(dt)


def test_host_starts_and_binds_port() -> None:
    """HostGame.start_network() でソケットがバインドされる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        host.start_network()
        bound = host.get_bound_address()
        assert bound is not None
        assert bound[1] > 0  # 動的ポート
    finally:
        host.stop_network()
        pg.quit()


def test_client_connects_to_host_and_receives_state() -> None:
    """ClientGame.connect() でハンドシェイクが成立し、state を受信できる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    host.start_network()
    bound = host.get_bound_address()
    assert bound is not None
    host_ip, host_port = bound

    client = ClientGame(host=host_ip, port=host_port, name="tester")
    try:
        # 接続
        connected = client.connect(timeout=2.0)
        assert connected, "client should connect to host"
        assert client.get_client().get_player_id() == PLAYER_FIGHTER_ID

        # ホスト側ループを数フレーム回して state broadcast を発生させる
        for _ in range(20):
            _drive_host_one_frame(host)

        # クライアントが state を受信するまで待つ
        assert _wait_until(lambda: client.get_client().poll_state() is not None)

        # state バッファに push できることを verify
        latest = client.get_client().poll_state()
        assert latest is not None
        assert latest.get("type") == "state"
        assert "enemies" in latest
        assert "fortress_hp" in latest
        assert "wave" in latest
    finally:
        client.stop()
        host.stop_network()
        pg.quit()


def test_host_processes_client_input() -> None:
    """クライアントが送った input がホストの inbox に届く（dispatch も例外なく動く）。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    host.start_network()
    bound = host.get_bound_address()
    assert bound is not None
    host_ip, host_port = bound

    client = ClientGame(host=host_ip, port=host_port, name="tester2")
    try:
        assert client.connect(timeout=2.0)
        # クライアント側から input を送る
        client.get_client().send_input({"move": [1.0, 0.0], "attack": False})

        # ホスト側のループで input が dispatch される（例外が出ないことを確認）
        for _ in range(10):
            _drive_host_one_frame(host)

        # _broadcast_state が動いたことを seq で確認
        assert host.get_state_seq() >= 1
    finally:
        client.stop()
        host.stop_network()
        pg.quit()


def test_host_applies_latest_remote_input_once_per_frame() -> None:
    """複数 input が同一フレームに届いても、移動は frame dt で 1 回だけ進む。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        fighter = host.get_fighter()
        start_x, start_y = fighter.get_pos()
        msg = {
            "type": MSG_INPUT,
            "player_id": PLAYER_FIGHTER_ID,
            "input": {"move": [1.0, 0.0]},
        }

        host._dispatch_remote_message(msg)
        host._dispatch_remote_message(msg)
        dt = 1.0 / 60.0
        host.update(dt)

        end_x, end_y = fighter.get_pos()
        assert abs(end_x - (start_x + fighter.BASE_SPEED * dt)) < 0.0001
        assert end_y == start_y
    finally:
        pg.quit()


def test_host_ignores_malformed_remote_move_payloads() -> None:
    """不正な move payload は例外にせず、最新入力として採用しない。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        start = host.get_fighter().get_pos()
        for move in (None, 1.0, [1.0], ["bad", 0.0], {"x": 1.0, "y": 0.0}):
            host._dispatch_remote_message(
                {"type": MSG_INPUT, "player_id": PLAYER_FIGHTER_ID, "input": {"move": move}}
            )

        host.update(1.0 / 60.0)

        assert host.get_fighter().get_pos() == start
    finally:
        pg.quit()


def test_host_broadcasts_state_at_configured_hz() -> None:
    """HostGame.update を 1 秒分回すと state_seq が state_hz 回程度増える。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0, state_hz=20)
    host.start_network()
    try:
        # 1 秒分回す（60FPS で 60 フレーム）
        for _ in range(60):
            _drive_host_one_frame(host, dt=1.0 / 60.0)
        # 1 秒で 20Hz → 約 20 回（最低 15 回は超える想定）
        assert host.get_state_seq() >= 15
    finally:
        host.stop_network()
        pg.quit()


def test_client_run_stops_net_client_on_connect_failure() -> None:
    """接続失敗で早期 return しても NetClient.stop() を呼ぶ。"""
    pg.init()
    pg.display.set_mode((400, 200))
    client = ClientGame(host="127.0.0.1", port=9, name="tester3")
    failing_client = _FailingClient()
    client._client = failing_client

    def no_wait() -> None:
        pass

    client._wait_brief = no_wait
    client.run()

    assert failing_client.stopped
    assert not client.is_running()


def test_state_players_include_sprite_fields() -> None:
    """送信 state のプレイヤーに画像名・サイズが含まれ、クライアントが描画できる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    host.start_network()
    bound = host.get_bound_address()
    assert bound is not None
    host_ip, host_port = bound

    client = ClientGame(host=host_ip, port=host_port, name="tester")
    try:
        assert client.connect(timeout=2.0)
        for _ in range(20):
            _drive_host_one_frame(host)
        assert _wait_until(lambda: client.get_client().poll_state() is not None)
        latest = client.get_client().poll_state()
        assert latest is not None
        players = latest.get("players", [])
        assert players, "state にプレイヤーが含まれるはず"
        for player in players:
            assert isinstance(player.get("image"), str) and player["image"]
            size = player.get("size")
            assert isinstance(size, list) and len(size) == 2
    finally:
        client.stop()
        host.stop_network()
        pg.quit()


def test_client_blit_sprite_uses_image_and_falls_back() -> None:
    """`_blit_sprite` は image/size があれば描画し、無ければ False を返す。"""
    pg.init()
    pg.display.set_mode((400, 200))
    client = ClientGame(host="127.0.0.1", port=9, name="tester")
    try:
        # 正常な image/size はスプライトを描いて True。
        assert client._blit_sprite({"image": "player_fighter.png", "size": [32, 32]}, (50.0, 50.0))
        # image/size が無い場合は False（呼び出し側で円フォールバック）。
        assert not client._blit_sprite({}, (0.0, 0.0))
        assert not client._blit_sprite({"image": "player_fighter.png"}, (0.0, 0.0))
    finally:
        client.stop()
        pg.quit()


if __name__ == "__main__":
    test_host_starts_and_binds_port()
    test_client_connects_to_host_and_receives_state()
    test_host_processes_client_input()
    test_host_applies_latest_remote_input_once_per_frame()
    test_host_ignores_malformed_remote_move_payloads()
    test_host_broadcasts_state_at_configured_hz()
    test_client_run_stops_net_client_on_connect_failure()
    test_state_players_include_sprite_fields()
    test_client_blit_sprite_uses_image_and_falls_back()
    print("All host-client integration tests passed.")
