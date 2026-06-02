"""全プロジェクトで共有する定数。

担当ごとに自分のセクションへ定数を追記する。マジックナンバーは原則として
ここに集約する。
"""

# ===== 画面・描画（ベース） =====
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60

# ===== 色 =====
COLOR_BG: tuple[int, int, int] = (18, 22, 28)
COLOR_TEXT: tuple[int, int, int] = (238, 238, 238)
COLOR_WHITE: tuple[int, int, int] = (255, 255, 255)
COLOR_BLACK: tuple[int, int, int] = (0, 0, 0)
COLOR_PLAYER: tuple[int, int, int] = (80, 180, 255)
COLOR_ENEMY: tuple[int, int, int] = (240, 90, 90)
COLOR_TOWER: tuple[int, int, int] = (100, 220, 150)
COLOR_FORTRESS: tuple[int, int, int] = (200, 200, 80)
COLOR_BULLET: tuple[int, int, int] = (255, 220, 120)
COLOR_HP_BAR_BG: tuple[int, int, int] = (60, 60, 60)
COLOR_HP_BAR_FG: tuple[int, int, int] = (90, 220, 120)

# ===== ゲームバランス（ベース） =====
PLAYER_BUILDER_ID: int = 1
PLAYER_FIGHTER_ID: int = 2
INITIAL_GOLD: int = 100
FORTRESS_MAX_HP: int = 1000
FORTRESS_X_RATIO: float = 0.85
FORTRESS_Y_RATIO: float = 0.5
PLAYER_MAX_HP: int = 100
ENEMY_BASE_HP: int = 30
ENEMY_BASE_DAMAGE: int = 5
ENEMY_BASE_REWARD: int = 1
TOWER_BASE_RANGE: float = 140.0
TOWER_BASE_DAMAGE: int = 8
TOWER_BASE_COOLDOWN: float = 0.8
BULLET_SPEED: float = 360.0

# タワー耐久（敵の体当たり）。敵が TOWER_CONTACT_DAMAGE のダメージを与え、
# TOWER_MAX_HP / TOWER_CONTACT_DAMAGE ≒ 20 回の体当たりでタワーは破壊される。
TOWER_MAX_HP: int = 20
TOWER_CONTACT_DAMAGE: int = 1  # 敵 1 回の体当たりでタワーに入るダメージ
TOWER_CONTACT_DISTANCE: float = 28.0  # 敵とタワーが接触したとみなす距離
# 同じ敵が同じタワーへ連続でダメージを与えるまでの間隔（秒）。これがないと
# 接触し続ける敵が毎フレーム削ってしまい、数フレームで壊れてしまう。
TOWER_CONTACT_INTERVAL: float = 0.5

# ===== ネットワーク（ベース） =====
SERVER_HOST: str = "127.0.0.1"
SERVER_PORT: int = 50000

# ===== 進化AI（担当①） =====
# 2026-06-01 の拡張実験 (evolution.run_extended_experiments) で最も高い
# 最終適応度を示した aggressive プロファイルを既定値に採用する。
FITNESS_DAMAGE_WEIGHT: float = 14.0
FITNESS_SURVIVAL_WEIGHT: float = 0.5
FITNESS_DISTANCE_WEIGHT: float = 4.0
EVOLUTION_MUTATION_RATE: float = 0.05
EVOLUTION_ELITE_RATE: float = 0.2
EVOLUTION_TOURNAMENT_SIZE: int = 3
EVOLUTION_TUNING_MUTATION_RATES: tuple[float, ...] = (0.01, 0.05, 0.10, 0.20)
EVOLUTION_TUNING_TOURNAMENT_SIZES: tuple[int, ...] = (2, 3, 5)
EVOLUTION_TUNING_POPULATION_SIZE: int = 16
EVOLUTION_TUNING_GENERATION_COUNT: int = 12
EVOLUTION_TUNING_SEED: int = 42
FITNESS_DISTANCE_FOCUS_DAMAGE_WEIGHT: float = 8.0
FITNESS_DISTANCE_FOCUS_SURVIVAL_WEIGHT: float = 1.0
FITNESS_DISTANCE_FOCUS_DISTANCE_WEIGHT: float = 8.0
EARLY_GENERATION_THRESHOLD: int = 5  # この世代以下はNNを使わずタワー誘導で移動する

# ===== ネットワーク（担当②） =====
NET_STATE_HZ: int = 20  # ホスト→クライアントの状態ブロードキャスト周波数
NET_INPUT_HZ: int = 30  # クライアント→ホストの操作送信周波数
NET_PING_INTERVAL_SEC: float = 0.5  # ping を送る間隔（2Hz）
NET_TIMEOUT_SEC: float = 5.0  # 最終受信からこの秒数経過で切断扱い
NET_ACK_RESEND_INTERVAL_SEC: float = 0.5  # ACK 待ちタイムアウト→再送
NET_ACK_MAX_RETRIES: int = 5  # ACK 再送の最大回数
NET_RECV_BUFFER_BYTES: int = 4096  # recvfrom のバッファサイズ
NET_RECV_TIMEOUT_SEC: float = 0.2  # 受信スレッドの select タイムアウト
NET_CONNECT_TIMEOUT_SEC: float = 3.0  # connect_ok を待つ秒数
# ホストが Player1、最初のクライアントが Player2
NET_FIRST_CLIENT_PLAYER_ID: int = PLAYER_FIGHTER_ID

# クライアント描画
CLIENT_FONT_SIZE: int = 18
CLIENT_DEFAULT_ENEMY_RADIUS: int = 10
CLIENT_DEFAULT_TOWER_RADIUS: int = 16
CLIENT_DEFAULT_PLAYER_RADIUS: int = 14
CLIENT_DEFAULT_FORTRESS_RADIUS: int = 36
CLIENT_DEFAULT_BULLET_RADIUS: int = 4
CLIENT_HP_BAR_WIDTH: int = 220
CLIENT_HP_BAR_HEIGHT: int = 12
CLIENT_OVERLAY_X: int = 10
CLIENT_OVERLAY_Y: int = 10
CLIENT_OVERLAY_TEXT_X_GAP: int = 12
CLIENT_OVERLAY_TEXT_Y_OFFSET: int = -1
CLIENT_WAITING_TEXT_Y_OFFSET: int = -20
CLIENT_CONNECTION_FAILED_TITLE_Y_OFFSET: int = -10
CLIENT_CONNECTION_FAILED_HINT_Y_OFFSET: int = 14
CLIENT_CONNECTION_FAIL_WAIT_SEC: float = 1.5
CLIENT_WAIT_FPS: int = 30

# ===== タワー属性（担当③） =====
# 火炎タワー
FIRE_DAMAGE: int = 10
FIRE_RANGE: float = 130.0
FIRE_COOLDOWN: float = 1.0
FIRE_EXPLOSION_RADIUS: float = 50.0
FIRE_EXPLOSION_FALLOFF: float = 0.6  # 中心から離れるほどダメージが下がる係数

# 氷タワー
ICE_DAMAGE: int = 5
ICE_RANGE: float = 130.0
ICE_COOLDOWN: float = 1.2
ICE_SLOW_FACTOR: float = 0.5  # 速度を半分にする
ICE_SLOW_DURATION: float = 3.0  # 3秒間

# 雷タワー
LIGHTNING_DAMAGE: int = 8
LIGHTNING_RANGE: float = 150.0
LIGHTNING_COOLDOWN: float = 0.6
LIGHTNING_CHAIN_RADIUS: float = 90.0
LIGHTNING_CHAIN_COUNT: int = 3  # 最大連鎖数（初撃含めて 3 体）
LIGHTNING_CHAIN_FALLOFF: float = 0.8  # 連鎖ごとにダメージ係数
LIGHTNING_VISUAL_DURATION: float = 0.2  # 稲妻ラインの表示秒数

# 物理タワー
PHYSICAL_DAMAGE: int = 22
PHYSICAL_RANGE: float = 180.0
PHYSICAL_COOLDOWN: float = 1.6
PHYSICAL_PIERCE_RATIO: float = 0.5  # 残HP割合に応じて最大 +50% のダメージ

# 色（属性別表示色）
COLOR_FIRE: tuple[int, int, int] = (240, 110, 60)
COLOR_ICE: tuple[int, int, int] = (110, 200, 240)
COLOR_LIGHTNING: tuple[int, int, int] = (250, 230, 80)
COLOR_PHYSICAL: tuple[int, int, int] = (200, 200, 200)

# アップグレード（共通）
TOWER_MAX_LEVEL: int = 3
TOWER_UPGRADE_COST_PER_LEVEL: tuple[int, ...] = (0, 30, 50)  # Lv1→2 が 30、Lv2→3 が 50
TOWER_UPGRADE_DAMAGE_BONUS: float = 0.4  # Lv ごとに +40%
TOWER_UPGRADE_RANGE_BONUS: float = 0.15  # Lv ごとに +15%
TOWER_UPGRADE_COOLDOWN_MULT: float = 0.85  # Lv ごとに ×0.85
TOWER_SELL_REFUND_RATIO: float = 0.5  # 総投資額の 50% を返金

# ===== 前線戦闘・演出（担当④） =====
# 武器
WEAPON_MELEE_DAMAGE: int = 14
WEAPON_MELEE_RANGE: float = 60.0
WEAPON_MELEE_COOLDOWN: float = 0.35
WEAPON_RANGED_DAMAGE: int = 7
WEAPON_RANGED_RANGE: float = 260.0
WEAPON_RANGED_COOLDOWN: float = 0.25
WEAPON_AREA_DAMAGE: int = 9
WEAPON_AREA_RANGE: float = 180.0
WEAPON_AREA_COOLDOWN: float = 0.9
WEAPON_AREA_EXPLOSION_RADIUS: float = 45.0
WEAPON_SWITCH_COOLDOWN: float = 0.2

# スキル
SKILL_DASH_COOLDOWN: float = 8.0
SKILL_DASH_DISTANCE: float = 220.0
SKILL_DASH_DURATION: float = 0.25
SKILL_DASH_DAMAGE: int = 18
SKILL_DASH_HIT_RADIUS: float = 30.0
SKILL_AREA_COOLDOWN: float = 12.0
SKILL_AREA_RADIUS: float = 110.0
SKILL_AREA_DAMAGE: int = 14

# ボス
BOSS_HP_MULTIPLIER: int = 15  # 通常敵 HP の倍率
BOSS_SPEED: float = 35.0
BOSS_DAMAGE: int = 30
BOSS_REWARD: int = 25
BOSS_RADIUS: int = 26
BOSS_SPECIAL_INTERVAL: float = 5.0  # 特殊行動（AOE）の発動間隔（秒）
BOSS_SPECIAL_DAMAGE: int = 12
BOSS_SPECIAL_RADIUS: float = 80.0
BOSS_WAVE_MODULO: int = 5  # 5の倍数ウェーブでボス出現
SOLO_MAX_WAVE: int = 15  # solo / host の最大ウェーブ数（BOSS_WAVE_MODULO の倍数を推奨）

# 特殊敵
FAST_ENEMY_HP: int = 12
FAST_ENEMY_SPEED: float = 160.0
FAST_ENEMY_DAMAGE: int = 4
FAST_ENEMY_REWARD: int = 2
SHIELDED_ENEMY_HP: int = 22
SHIELDED_ENEMY_SHIELD: int = 30  # 盾HP（盾が割れるまでダメージ無効）
SHIELDED_ENEMY_SPEED: float = 60.0
SHIELDED_ENEMY_DAMAGE: int = 6
SHIELDED_ENEMY_REWARD: int = 3
SPECIAL_FAST_PROBABILITY: float = 0.2
SPECIAL_SHIELDED_PROBABILITY: float = 0.1

# ===== 難易度スケーリング（ゲーム拡張 / Epic #125） =====
# 進化世代ごとに敵 HP を増やす。ウェーブではなく世代を基準にすることで、
# 1 世代の個体群を複数ウェーブで評価しても同一世代内の HP が一定になり、
# 進化AI の fitness 比較の公平性（選択バイアス防止）を保つ。
ENEMY_HP_GROWTH_PER_GENERATION: float = 0.15  # 世代ごとに敵 HP を +15%（世代1 は等倍）

# 特殊敵（FastEnemy / ShieldedEnemy）のウェーブスケーリング。
# 特殊敵は進化AIの fitness 対象外なのでウェーブ基準でよい（バイアスを生まない）。
SPECIAL_ENEMY_BASE_PROBABILITY: float = 0.1  # wave1 の特殊敵出現率
SPECIAL_ENEMY_PROBABILITY_GROWTH_PER_WAVE: float = 0.04  # ウェーブごとに出現率 +0.04
SPECIAL_ENEMY_PROBABILITY_MAX: float = 0.5  # 出現率の上限
SPECIAL_ENEMY_HP_GROWTH_PER_WAVE: float = 0.1  # 特殊敵 HP をウェーブごと +10%

# ボスのウェーブスケーリング（出現回ごと。ボスは fitness 対象外）。
BOSS_HP_GROWTH_PER_APPEARANCE: float = 0.3  # ボス出現回ごとに HP +30%
BOSS_DAMAGE_GROWTH_PER_APPEARANCE: float = 0.15  # ボス出現回ごとに接触ダメージ +15%

# ウェーブクリアボーナス（クリア時に資源と拠点HPを付与）。
WAVE_CLEAR_GOLD_BONUS: int = 20  # 通常ウェーブクリアで得る資源
WAVE_CLEAR_FORTRESS_HEAL: int = 30  # 通常ウェーブクリアで回復する拠点HP
BOSS_WAVE_CLEAR_GOLD_BONUS: int = 40  # ボスウェーブクリア時の追加資源
BOSS_WAVE_CLEAR_FORTRESS_HEAL: int = 60  # ボスウェーブクリア時の追加拠点HP

# エフェクト
EFFECT_EXPLOSION_PARTICLES: int = 22
EFFECT_HIT_PARTICLES: int = 8
EFFECT_MUZZLE_PARTICLES: int = 6
EFFECT_SHOCKWAVE_DURATION: float = 0.35
COLOR_EFFECT_EXPLOSION: tuple[int, int, int] = (255, 180, 60)
COLOR_EFFECT_HIT: tuple[int, int, int] = (255, 240, 200)
COLOR_EFFECT_SHOCKWAVE: tuple[int, int, int] = (160, 200, 255)
COLOR_EFFECT_BOSS_DEATH: tuple[int, int, int] = (255, 80, 80)
COLOR_BOSS: tuple[int, int, int] = (200, 60, 200)
COLOR_FAST: tuple[int, int, int] = (255, 230, 90)
COLOR_SHIELDED: tuple[int, int, int] = (150, 180, 220)
COLOR_SHIELD: tuple[int, int, int] = (90, 200, 240)

# ===== 対戦・可視化・サウンド（担当⑤） =====
# 進化グラフ
EVOLUTION_GRAPH_DEFAULT_ORIGIN: tuple[int, int] = (10, 80)
GRAPH_DEFAULT_WIDTH: int = 200
GRAPH_DEFAULT_HEIGHT: int = 100
GRAPH_MAX_GENERATIONS: int = 60  # 表示する直近世代数
GRAPH_LINE_BEST: tuple[int, int, int] = (255, 200, 80)
GRAPH_LINE_AVG: tuple[int, int, int] = (140, 200, 255)
GRAPH_GRID_COLOR: tuple[int, int, int] = (60, 60, 70)
GRAPH_BG_COLOR: tuple[int, int, int] = (12, 14, 20)

# 詳細HUD
HUD_PANEL_BG: tuple[int, int, int] = (24, 28, 36)
HUD_PANEL_BORDER: tuple[int, int, int] = (90, 90, 100)
HUD_OPPONENT_BAR_FG: tuple[int, int, int] = (240, 80, 80)

# チュートリアル
TUTORIAL_PANEL_WIDTH: int = 760
TUTORIAL_PANEL_PADDING: int = 24
TUTORIAL_PANEL_MARGIN: int = 36
TUTORIAL_PANEL_MAX_HEIGHT: int = 620
TUTORIAL_TITLE_FONT_SIZE: int = 34
TUTORIAL_SECTION_FONT_SIZE: int = 24
TUTORIAL_BODY_FONT_SIZE: int = 18
TUTORIAL_LINE_HEIGHT: int = 23
TUTORIAL_CLOSE_BUTTON_SIZE: int = 34
TUTORIAL_BACKDROP_ALPHA: int = 150
TUTORIAL_TITLE_TO_BODY_GAP: int = 46
TUTORIAL_SECTION_TITLE_GAP: int = 27
TUTORIAL_SECTION_BOTTOM_GAP: int = 8
TUTORIAL_SKIP_CHECKBOX_SIZE: int = 18
TUTORIAL_SKIP_LABEL_GAP: int = 8
TUTORIAL_SKIP_ROW_BOTTOM_GAP: int = 34
TUTORIAL_CHECK_MARK_WIDTH: int = 3
TUTORIAL_CHECKBOX_BORDER_WIDTH: int = 2
TUTORIAL_CHECK_MARK_INSET: int = 4
TUTORIAL_CHECK_MARK_CENTER_OFFSET: int = 1
TUTORIAL_CHECK_MARK_BOTTOM_OFFSET: int = 5
# チュートリアル設定
SETTINGS_FILE_NAME: str = "settings.json"
SETTINGS_KEY_TUTORIAL_SEEN: str = "tutorial_seen"
SETTINGS_JSON_INDENT: int = 2
# 対戦
VERSUS_FIELD_GAP: int = 16  # 2フィールド間の余白
VERSUS_SEND_COST: int = 25  # 敵送信のリソース消費
VERSUS_SEND_KEY_PROMPT: str = "B"  # 敵送信メニューを開くキー（表示用）
VERSUS_MAX_WAVE: int = 99  # 対戦中は時間制限なし扱い
# 対戦モード HUD（左右の各盤面の上部に拠点HP/資源/ウェーブを表示する）
VERSUS_HUD_MARGIN: int = 10  # 画面端からの内側マージン
VERSUS_HUD_LINE_HEIGHT: int = 22  # HUD テキストの行送り
VERSUS_HUD_FONT_SIZE: int = 18  # HUD 本文フォントサイズ
VERSUS_HUD_HP_BAR_WIDTH: int = 200  # 拠点 HP バーの幅
VERSUS_HUD_HP_BAR_HEIGHT: int = 12  # 拠点 HP バーの高さ
VERSUS_HINT_FONT_SIZE: int = 16  # 画面下部の操作ヒント用フォントサイズ
VERSUS_HINT_BOTTOM_MARGIN: int = 12  # 操作ヒントを画面下からどれだけ上に置くか
VERSUS_HINT_TEXT: str = "SPACE: 左→右に送信   ENTER: 右→左に送信   ESC: 終了"

# サウンド
SOUND_ASSET_DIR: str = "assets/sound"  # SE/BGM の検索先
SOUND_DEFAULT_BGM_VOLUME: float = 0.5
SOUND_DEFAULT_SE_VOLUME: float = 0.8
SOUND_MIXER_FREQUENCY: int = 44100
SOUND_MIXER_CHANNELS: int = 2

# SE 名（音源ファイルは `assets/sound/<name>.wav` または .ogg）
SE_TOWER_PLACE: str = "tower_place"
SE_TOWER_FIRE: str = "tower_fire"
SE_HIT: str = "hit"
SE_ENEMY_DIE: str = "enemy_die"
SE_WEAPON_FIRE: str = "weapon_fire"
SE_SKILL_DASH: str = "skill_dash"
SE_SKILL_AREA: str = "skill_area"
SE_BOSS_SPECIAL: str = "boss_special"
SE_BOSS_DIE: str = "boss_die"
SE_WAVE_START: str = "wave_start"
SE_WAVE_END: str = "wave_end"
SE_VERSUS_SEND: str = "versus_send_enemy"
SE_VICTORY: str = "victory"
SE_DEFEAT: str = "defeat"
BGM_MAIN: str = "bgm_main"  # `assets/sound/bgm_main.ogg` などを想定
