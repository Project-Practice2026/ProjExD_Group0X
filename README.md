# 共進化の砦（仮）

> 2人協力プレイのタワーディフェンス。敵はニューラルネットを持ち、世代を経るごとにプレイヤーのタワー配置を学習して経路を最適化してくる。プレイヤー2人は別々のPCからLAN接続して「建築役」と「前線役」に役割分担し、敵の進化を出し抜く戦略を練る。
<img width="1919" height="1199" alt="image" src="https://github.com/user-attachments/assets/5f9e0874-b457-4a1b-8582-114fa4f55d84" />


## 実行環境の必要条件

* python >= 3.10
* pygame >= 2.5.2
* numpy >= 1.24
* Ruff（`requirements.txt` からインストール）

依存関係は `requirements.txt` に統一しています。初回セットアップ時は以下を実行してください。

```bash
pip install -r requirements.txt
```

## ゲームの概要

* 2人協力プレイ対応のLANネットワークタワーディフェンスゲーム
* 敵は遺伝的ニューラルネットによって世代ごとに進化し、プレイヤーの戦法に適応してくる
* プレイヤー1は「建築役」（マウスでタワー設置）、プレイヤー2は「前線役」（キャラを操作して直接戦闘）
* ウェーブ制で進行し、規定ウェーブを生き残れば勝利、拠点HPが0で敗北
* 追加機能として、互いに敵を送り込み合う対戦モードも搭載

### 起動方法

```bash
# ホスト（プレイヤー1）として起動
python main.py --host

# クライアント（プレイヤー2）として起動
python main.py --client --ip=192.168.1.10

# 1人プレイ（フォールバック・デバッグ用）
python main.py --solo

```

## CI・品質チェック

このリポジトリでは GitHub Actions によるCIを追加しています。`main` へのpush時と、`main` 向けPull Request作成・更新時に以下を実行します。

* `ruff check . --output-format=github`
* `ruff format . --check`
* `python -m compileall .`
* リポジトリ内の `test_*.py` を簡易テストランナーで実行

Pull Requestを出す前に、ローカルでも以下を実行して確認してください。

```bash
ruff check .
ruff format . --check
python -m compileall .
python - <<'PY'
from pathlib import Path
import runpy
import sys

repo_root = Path(".").resolve()
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

test_files = sorted(Path(".").rglob("test_*.py"))

if not test_files:
    print("No test_*.py files found. Skipping simple test runner.")
    raise SystemExit(0)

for path in test_files:
    if any(part in {".venv", "venv", "__pycache__"} for part in path.parts):
        continue
    print(f"Running {path}")
    namespace = runpy.run_path(str(path), run_name="__main__")
    test_functions = [
        value
        for name, value in sorted(namespace.items())
        if name.startswith("test_") and callable(value)
    ]
    for test_function in test_functions:
        test_function()
PY
```

## 操作方法

### プレイヤー1（建築役・ホスト）
* マウス左クリック：タワー設置
* マウス右クリック：タワー選択 → アップグレード／売却
* 数字キー 1〜4：設置するタワー種類の切替（炎／氷／雷／物理）
* スペースキー：次ウェーブを早期開始

### プレイヤー2（前線役・クライアント）
* WASD：キャラ移動
* J：通常攻撃
* K：特殊スキル（クールタイムあり）
* L：タワー修理（近接時、リソース消費）
* Shift：ダッシュ

## ゲームの実装

### 共通基本機能

- [x] 画面・マップ描画と拠点表示（`core/world.py`, `core/fortress.py`）
- [ ] プレイヤー1・2の基本操作（タワー設置、キャラ移動、通常攻撃）※基底のみ `core/base_player.py`、操作実装は別Epicで
- [x] 1種類のタワー設置と弾の発射（`core/base_tower.py`, `core/bullet.py`）
- [x] 敵の出現と直進移動（NN未搭載の固定動作）（`core/base_enemy.py`, `core/wave_manager.py`）
- [x] ウェーブ管理の最低限の枠組み（`core/wave_manager.py` — PREPARE→BATTLE→SUMMARY）
- [ ] 共有リソース（エナジー）の管理（定数 `INITIAL_GOLD` のみ。管理クラスは未実装）
- [x] HUDの基本表示（HP・リソース・ウェーブ番号）（`core/base_hud.py`）
- [ ] soloモード（1台で2プレイヤー操作、テスト・デバッグ用）※別Epic

### core パッケージの主要クラス

`core/` には全担当が継承・利用する基底クラスを配置している。インスタンス変数は `_変数名` 形式、外部アクセスは `get_<name>()` / `set_<name>()` メソッドで統一。

| モジュール | クラス | 役割 |
|------------|--------|------|
| `core/constants.py` | （定数） | 画面/色/バランス/担当別セクション |
| `core/game.py` | `Game` | pygame 初期化・QUIT処理・メインループ |
| `core/fortress.py` | `Fortress` | 拠点HP・HPバー描画・`take_damage` / `is_destroyed` |
| `core/base_player.py` | `BasePlayer` | プレイヤー基底（`Builder` / `Fighter` が継承） |
| `core/base_enemy.py` | `BaseEnemy` | 敵基底（拠点への直進移動）。`EvolvedEnemy` / `BossEnemy` / `SpecialEnemy` が継承 |
| `core/base_tower.py` | `BaseTower` | タワー基底（射程内最近敵を `find_target`、`attack` で `Bullet` 生成）。4属性タワーが継承 |
| `core/bullet.py` | `Bullet` | 対象追尾・命中判定・ダメージ適用 |
| `core/world.py` | `World` | 出現口・タワー配置可否判定・全エンティティの update/draw 統括 |
| `core/wave_manager.py` | `WaveManager` / `WavePhase` | ウェーブ進行（敵factoryで差し替え可能） |
| `core/base_hud.py` | `BaseHud` | HUD基底（HP / Resource / Wave / Generation 表示）。`ExtendedHud` が継承 |

### 前線戦闘と演出（秋山担当）

前線役プレイヤーの武器・スキル、ボス敵・特殊敵、視覚演出（パーティクル/波紋）を `combat/` パッケージに実装。`core` 側との結合を疎にするため、エフェクトは `core.world.EffectSink` Protocol を介して注入し、武器・スキルは `Fighter.__init__` で外部から受け取る（`TYPE_CHECKING` ガード）。

| モジュール | クラス | 役割 |
|------------|--------|------|
| `combat/weapons.py` | `BaseWeapon` / `MeleeWeapon` / `RangedWeapon` / `AreaWeapon` / `AreaBullet` | 3 種類の武器。`fire(owner_pos, target, facing) -> list[Bullet]` で統一 IF |
| `combat/fighter_skills.py` | `BaseSkill` / `DashAttackSkill` / `AreaAttackSkill` | スキル基底＋ダッシュ攻撃（無敵＋通過ダメージ）＋範囲攻撃（波紋エフェクト） |
| `combat/boss_enemy.py` | `BossEnemy` | 通常敵×`BOSS_HP_MULTIPLIER` の HP、`BOSS_SPECIAL_INTERVAL` 毎の周囲AOE、撃破時 `trigger_death_effect` で大爆発 |
| `combat/special_enemy.py` | `FastEnemy` / `ShieldedEnemy` | 高速低HP／盾HPを `_shield` で吸収し破壊後に本HPが減る |
| `combat/effects.py` | `EffectManager` / `Particle` / `Shockwave` | `spawn_explosion` / `spawn_hit` / `spawn_muzzle_flash` / `spawn_shockwave`。寿命減衰・波紋拡大演出 |
| `combat/weapon_selector_ui.py` | `WeaponSelectorUI` | Fighter 近辺に現武器アイコン＋名前＋クールタイムバーを描画 |
| `core/world.py` | `EffectSink` Protocol | エフェクト発火点の最小プロトコル。実体は `EffectManager`、未注入時は `_NullEffects` フォールバック |

操作（Fighter / プレイヤー2）:

* **WASD** ＝ 移動 ／ **Shift** ＝ 通常ダッシュ（速度 ×1.8）
* **J** ＝ 通常攻撃（現在の武器を発射）
* **K** ＝ スキル発動（DashAttack または AreaAttack）
* **Q / E** ＝ 武器サイクル（MELEE → RANGED → AREA）
* **5 / 6** ＝ スキルサイクル

ボス出現:

* `WaveManager.boss_factory` を渡しておくと、`wave % BOSS_WAVE_MODULO == 0`（既定 5）のウェーブで先頭に 1 体だけボスが投入される
* `SoloGame._update_bosses` がボスを duck-typed に駆動（`update_with_world` / `trigger_death_effect` を `getattr` で呼ぶ）

### 分担追加機能

* **進化NNによる敵移動システム（担当：木村）** ：敵が個別に小さなニューラルネットを持ち、遺伝的アルゴリズムによりウェーブごとに進化する機能。NumPyのみで実装し、敵の経路選択を世代を経るごとに最適化する
* **LANネットワーク通信（担当：秋山）** ：UDPによる権威サーバ型のクライアント-サーバ通信機能。ホストがゲームロジックを保持し、20Hzで状態同期、30Hzで操作受信、重要イベントはACK＋再送で確実に伝達する
* **タワー属性・アップグレードシステム（担当：木村）** ：炎／氷／雷／物理の4属性タワーと、レベルアップ機能。属性ごとに敵への効果が異なり、戦略性を生む
* **前線プレイヤー武器・スキル＋特殊敵・ボス・エフェクト（秋山担当）** ：3 種武器（MELEE/RANGED/AREA）の切替、スキル（DashAttack/AreaAttack）、ボス敵（HP×15・周囲AOE）と特殊敵（FastEnemy/ShieldedEnemy）、パーティクルエフェクト（爆発/命中/マズル/波紋）。`combat/` パッケージで実装済み
* **対戦モード＋進化可視化＋HUD拡張＋サウンド（担当：小山）** ：互いに敵を送り合う対戦モード、世代ごとの適応度グラフ、詳細HUD、BGM・効果音

* **UI多言語日本語化対応・画面レイアウト最適化（担当：齋藤）** ：日本語化に伴うメインメニュー・IP入力画面の文字化けを `get_font` の共通化により解消。およびチュートリアルオーバーレイ画面におけるチェックボックス行とヒント文の位置計算ロジック定数化（`HINT_TOP_GAP`）による文字重なりバグの防止

### ToDo

- [ ] 進化AIの適応度関数のパラメータ調整
- [ ] ネットワーク同期のラグ補正
- [ ] 対戦モードのバランス調整

### メモ

* クラス内のインスタンス変数は、すべて `_変数名` のように先頭にアンダースコアを付け、外部アクセスは `get_変数名()` / `set_変数名()` メソッドを介して行う設計とする
* すべてのクラスに関係する関数は、各パッケージの `__init__.py` ではなく、関連するモジュール内のクラス外で定義する
* `main.py` の冒頭には必ず `os.chdir(os.path.dirname(os.path.abspath(__file__)))` を記述する
* 詳細な設計方針・クラス設計・ネットワークプロトコルは `docs/DESIGN.md` を参照
* コード規約・ディレクトリルール・AI支援開発のガイドラインは `AGENTS.md` を参照
