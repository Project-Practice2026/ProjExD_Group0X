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

from core.base_player import BasePlayer
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
    """複数 input が同一フレームに届いても、建築役の移動は frame dt で 1 回だけ進む。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        builder = host.get_builder()
        start_x, start_y = builder.get_pos()
        msg = {
            "type": MSG_INPUT,
            "player_id": PLAYER_FIGHTER_ID,
            "input": {"move": [1.0, 0.0]},
        }

        host._dispatch_remote_message(msg)
        host._dispatch_remote_message(msg)
        dt = 1.0 / 60.0
        host.update(dt)

        end_x, end_y = builder.get_pos()
        assert abs(end_x - (start_x + BasePlayer.DEFAULT_SPEED * dt)) < 0.0001
        assert end_y == start_y
    finally:
        pg.quit()


def test_host_ignores_malformed_remote_move_payloads() -> None:
    """不正な move payload は例外にせず、建築役も動かさない。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        start = host.get_builder().get_pos()
        for move in (None, 1.0, [1.0], ["bad", 0.0], {"x": 1.0, "y": 0.0}):
            host._dispatch_remote_message(
                {"type": MSG_INPUT, "player_id": PLAYER_FIGHTER_ID, "input": {"move": move}}
            )

        host.update(1.0 / 60.0)

        assert host.get_builder().get_pos() == start
    finally:
        pg.quit()


def test_client_input_moves_builder_over_network() -> None:
    """クライアントの移動入力で画面左下の建築役が動く（エンドツーエンド）。"""
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
        builder = host.get_builder()
        start_x = builder.get_pos()[0]
        for _ in range(20):
            client.get_client().send_input({"move": [1.0, 0.0], "attack": False})
            _drive_host_one_frame(host)
            time.sleep(0.01)
        assert builder.get_pos()[0] > start_x, "クライアント入力で建築役が右へ動くはず"
    finally:
        client.stop()
        host.stop_network()
        pg.quit()


def test_remote_enter_places_tower_once_per_press() -> None:
    """クライアントの Enter(place) で建築役の位置に 1 個だけタワーが設置される。"""
    pg.init()
    pg.display.set_mode((400, 200))
    host = HostGame(host="127.0.0.1", port=0)
    try:
        world = host.get_world()
        assert world.get_towers() == []
        place_msg = {
            "type": MSG_INPUT,
            "player_id": PLAYER_FIGHTER_ID,
            "input": {"move": [0.0, 0.0], "place": True},
        }
        # 押下の立ち上がりで 1 個設置される。
        host._dispatch_remote_message(place_msg)
        host.update(1.0 / 60.0)
        assert len(world.get_towers()) == 1
        # 押しっぱなし（place=True 継続）では追加設置しない。
        host._dispatch_remote_message(place_msg)
        host.update(1.0 / 60.0)
        assert len(world.get_towers()) == 1
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


def test_client_blit_with_default_falls_back_to_sprite() -> None:
    """image/size が無い（旧ホスト等）でも、既定スプライトで描画できる。"""
    pg.init()
    pg.display.set_mode((400, 200))
    client = ClientGame(host="127.0.0.1", port=9, name="tester")
    try:
        # image 無しでも既定スプライト名が有効なら描画して True。
        assert client._blit_with_default({}, (50.0, 50.0), "player_builder.png", (32, 32))
        # 既定スプライト名も無効なら False（呼び出し側で円フォールバック）。
        assert not client._blit_with_default({}, (0.0, 0.0), "does_not_exist.png", (10, 10))
    finally:
        client.stop()
        pg.quit()


if __name__ == "__main__":
    test_host_starts_and_binds_port()
    test_client_connects_to_host_and_receives_state()
    test_host_processes_client_input()
    test_host_applies_latest_remote_input_once_per_frame()
    test_host_ignores_malformed_remote_move_payloads()
    test_client_input_moves_builder_over_network()
    test_remote_enter_places_tower_once_per_press()
    test_host_broadcasts_state_at_configured_hz()
    test_client_run_stops_net_client_on_connect_failure()
    test_state_players_include_sprite_fields()
    test_client_blit_sprite_uses_image_and_falls_back()
    test_client_blit_with_default_falls_back_to_sprite()
    print("All host-client integration tests passed.")
