"""Tests for evolution helpers."""

from __future__ import annotations

from itertools import pairwise

import numpy as np

from core.base_tower import BaseTower
from core.constants import (
    EARLY_GENERATION_THRESHOLD,
    ENEMY_BASE_HP,
    ENEMY_HP_GROWTH_PER_GENERATION,
    EVOLUTION_ELITE_RATE,
    EVOLUTION_MUTATION_RATE,
    EVOLUTION_TOURNAMENT_SIZE,
    FITNESS_DAMAGE_WEIGHT,
    FITNESS_DISTANCE_WEIGHT,
    FITNESS_SURVIVAL_WEIGHT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from core.fortress import Fortress
from core.world import World
from evolution import tune_parameters
from evolution.evolution_driver import EvolutionDriver
from evolution.evolution_manager import EvolutionManager
from evolution.evolved_enemy import EvolvedEnemy
from evolution.neural_net import DEFAULT_INPUT_SIZE, DEFAULT_OUTPUT_SIZE, NeuralNet


class _CapturingEvolutionManager(EvolutionManager):
    """next_generation に渡された fitness を検証用に保持する manager。"""

    def __post_init__(self) -> None:
        super().__post_init__()
        self.captured_fitness: list[float] | None = None

    def next_generation(self, fitness: list[float]) -> list[NeuralNet]:
        self.captured_fitness = list(fitness)
        return super().next_generation(fitness)


class _FixedBrain:
    def __init__(self, output: tuple[float, float]) -> None:
        self._output: np.ndarray = np.asarray(output, dtype=float)
        self.last_input: np.ndarray | None = None

    def forward(self, input_vec: np.ndarray) -> np.ndarray:
        self.last_input = np.asarray(input_vec, dtype=float)
        return self._output


DETERMINISTIC_EVAL_INPUT: np.ndarray = np.linspace(-1.0, 1.0, DEFAULT_INPUT_SIZE)


def _weights_match(left: list[np.ndarray], right: list[np.ndarray]) -> bool:
    """Return whether two NeuralNet weight lists are exactly identical."""
    return all(np.array_equal(a, b) for a, b in zip(left, right, strict=True))


def _deterministic_network_fitness(net: NeuralNet) -> float:
    """Score a network deterministically from a fixed observation vector."""
    output = net.forward(DETERMINISTIC_EVAL_INPUT)
    return float(output[0])


def test_neural_net_forward_shape() -> None:
    net = NeuralNet()
    output = net.forward(np.zeros(DEFAULT_INPUT_SIZE))
    assert output.shape == (DEFAULT_OUTPUT_SIZE,)


def test_neural_net_forward_output_range() -> None:
    net = NeuralNet()
    output = net.forward(np.ones(DEFAULT_INPUT_SIZE))
    assert np.all((output >= -1.0) & (output <= 1.0))


def test_neural_net_rejects_wrong_input_shape() -> None:
    net = NeuralNet()
    try:
        net.forward(np.zeros(DEFAULT_INPUT_SIZE - 1))
    except ValueError as error:
        assert "input_vec must have shape" in str(error)
    else:
        raise AssertionError("NeuralNet.forward should reject wrong input shape")


def test_neural_net_set_weights_matches_forward_result() -> None:
    net = NeuralNet()
    # b1/b2 に非ゼロ値を設定してバイアスのコピー漏れも検出できるようにする
    w1, b1, w2, b2 = net.get_weights()
    b1[:] = np.linspace(-0.5, 0.5, b1.shape[0])
    b2[:] = np.linspace(-0.3, 0.3, b2.shape[0])
    net.set_weights([w1, b1, w2, b2])

    input_vec = np.linspace(0.0, 1.0, DEFAULT_INPUT_SIZE)
    expected = net.forward(input_vec)

    copied_net = NeuralNet()
    weights = net.get_weights()
    copied_net.set_weights(weights)
    assert np.allclose(copied_net.forward(input_vec), expected)

    # set_weights が defensive copy: 渡した配列を変更してもコピー先は影響を受けない
    # w1[0, :] は input_vec[0]==0.0 に対応するため b1 を変更して確実に検出する
    weights[1][0] += 999.0
    assert np.allclose(copied_net.forward(input_vec), expected)

    # get_weights が defensive copy: 返された配列を変更しても元のNNは影響を受けない
    leaked = net.get_weights()
    leaked[1][0] += 999.0
    assert np.allclose(net.forward(input_vec), expected)


def test_neural_net_clone_keeps_independent_weights() -> None:
    net = NeuralNet()
    cloned_net = net.clone()
    original_weights = cloned_net.get_weights()

    # set_weightsによる配列差し替えでなくin-place変更で浅いコピーバグも検出する
    net.w1[0, 0] += 1.0
    net.b1[0] += 1.0
    net.w2[0, 0] += 1.0
    net.b2[0] += 1.0

    assert np.array_equal(cloned_net.w1, original_weights[0])
    assert np.array_equal(cloned_net.b1, original_weights[1])
    assert np.array_equal(cloned_net.w2, original_weights[2])
    assert np.array_equal(cloned_net.b2, original_weights[3])


def test_evolved_enemy_builds_twelve_dimensional_input() -> None:
    enemy = EvolvedEnemy(pos=(100.0, 100.0), hp=20)
    enemy.take_damage(5)
    fortress = Fortress(pos=(580.0, 370.0))
    tower = BaseTower(pos=(196.0, 154.0))

    input_vec = enemy._build_input_vector(fortress, [tower])

    assert input_vec.shape == (DEFAULT_INPUT_SIZE,)
    assert input_vec[0] == 0.75
    assert input_vec[1] == (fortress.get_pos()[0] - enemy.get_pos()[0]) / SCREEN_WIDTH
    assert input_vec[2] == (fortress.get_pos()[1] - enemy.get_pos()[1]) / SCREEN_HEIGHT
    assert input_vec[3] == (tower.get_pos()[0] - enemy.get_pos()[0]) / SCREEN_WIDTH
    assert input_vec[4] == (tower.get_pos()[1] - enemy.get_pos()[1]) / SCREEN_HEIGHT


def test_evolved_enemy_moves_with_brain_output() -> None:
    brain = _FixedBrain((1.0, 0.0))
    enemy = EvolvedEnemy(pos=(100.0, 100.0), brain=brain, speed=60.0)
    fortress = Fortress(pos=(900.0, 100.0))

    enemy.update_with_towers(fortress, [], dt=0.5)

    assert enemy.get_pos() == (130.0, 100.0)
    assert brain.last_input is not None


def test_world_passes_towers_to_evolved_enemy() -> None:
    brain = _FixedBrain((0.0, 1.0))
    # EARLY_GENERATION_THRESHOLD を超えた世代を指定してNNパスを通す
    enemy = EvolvedEnemy(
        pos=(100.0, 100.0),
        brain=brain,
        speed=0.0,
        generation=EARLY_GENERATION_THRESHOLD + 1,
    )
    tower = BaseTower(pos=(220.0, 160.0))
    world = World(spawn_points=[], fortress=Fortress(pos=(900.0, 100.0)))
    world.add_enemy(enemy)
    world.add_tower(tower)

    world.update(0.1)

    assert brain.last_input is not None
    assert brain.last_input[3] == (tower.get_pos()[0] - enemy.get_pos()[0]) / SCREEN_WIDTH
    assert brain.last_input[4] == (tower.get_pos()[1] - enemy.get_pos()[1]) / SCREEN_HEIGHT


def test_early_generation_moves_toward_nearest_tower() -> None:
    """初期世代（閾値以下）はNNを使わず最近傍タワーへ向かうことを確認する。"""
    brain = _FixedBrain((0.0, 0.0))  # NN出力は原点（呼ばれないはず）
    enemy = EvolvedEnemy(
        pos=(100.0, 300.0),
        brain=brain,
        speed=60.0,
        generation=EARLY_GENERATION_THRESHOLD,
    )
    tower = BaseTower(pos=(200.0, 300.0))  # 真横にタワー
    fortress = Fortress(pos=(900.0, 300.0))

    enemy.update_with_towers(fortress, [tower], dt=1.0)

    ex, ey = enemy.get_pos()
    assert ex > 100.0, "タワー方向（+x）に移動しているはず"
    assert abs(ey - 300.0) < 1e-9, "y座標は変わらないはず"
    assert brain.last_input is None, "早期世代ではNNは呼ばれないはず"


def test_early_generation_falls_back_to_nn_when_no_towers() -> None:
    """初期世代でもタワーがなければNNで移動することを確認する。"""
    brain = _FixedBrain((1.0, 0.0))
    enemy = EvolvedEnemy(
        pos=(100.0, 100.0),
        brain=brain,
        speed=60.0,
        generation=0,
    )
    fortress = Fortress(pos=(900.0, 100.0))

    enemy.update_with_towers(fortress, [], dt=0.5)

    assert enemy.get_pos() == (130.0, 100.0)
    assert brain.last_input is not None, "タワーなし時はNNにフォールバックするはず"


def test_early_generation_targets_fortress_when_near_all_towers() -> None:
    """早期世代でも全タワーに到達済みなら拠点方向へ進むことを確認する（Issue #155）。

    タワー位置と完全に重なる位置にいる敵は、これまで方向ベクトルが (0,0) になって
    停滞していた。修正後はタワーを誘導対象から除外し、拠点方向へフォールバックする。
    """
    brain = _FixedBrain((0.0, 0.0))  # NN出力が呼ばれた場合の検知用
    enemy = EvolvedEnemy(
        pos=(200.0, 100.0),  # タワーと同座標
        brain=brain,
        speed=60.0,
        generation=0,
    )
    tower = BaseTower(pos=(200.0, 100.0))
    fortress = Fortress(pos=(900.0, 100.0))

    enemy.update_with_towers(fortress, [tower], dt=0.5)

    ex, ey = enemy.get_pos()
    assert ex > 200.0, "拠点方向（+x）へ移動しているはず"
    assert abs(ey - 100.0) < 1e-9, "拠点と同じ y にあるので y は変わらないはず"
    assert brain.last_input is None, "早期世代ではNNを呼ばずに拠点へ向かうべき"


def test_later_generation_uses_nn_even_with_towers() -> None:
    """閾値を超えた世代はタワーがあってもNNを使うことを確認する。"""
    brain = _FixedBrain((0.0, 1.0))  # 真下に移動するNN出力
    enemy = EvolvedEnemy(
        pos=(100.0, 100.0),
        brain=brain,
        speed=60.0,
        generation=EARLY_GENERATION_THRESHOLD + 1,
    )
    tower = BaseTower(pos=(200.0, 100.0))  # 真横にタワー
    fortress = Fortress(pos=(900.0, 100.0))

    enemy.update_with_towers(fortress, [tower], dt=0.5)

    _ex, ey = enemy.get_pos()
    assert ey > 100.0, "NNの出力（+y方向）に移動しているはず"
    assert brain.last_input is not None, "閾値超えではNNが呼ばれるはず"


def test_evolution_manager_uses_default_neural_net_shape() -> None:
    manager = EvolutionManager(population_size=2)
    assert manager.population[0].input_size == DEFAULT_INPUT_SIZE
    assert manager.population[0].output_size == DEFAULT_OUTPUT_SIZE


def test_evolution_manager_uses_default_mutation_rate() -> None:
    manager = EvolutionManager(population_size=1)
    assert EVOLUTION_MUTATION_RATE == 0.05
    assert manager.mutation_rate == EVOLUTION_MUTATION_RATE


def test_next_generation_keeps_population_size() -> None:
    manager = EvolutionManager(population_size=6)
    generation = manager.next_generation([1, 2, 3, 4, 5, 6])
    assert len(generation) == 6


def test_next_generation_preserves_top_elite_identity() -> None:
    """エリート選択により、適応度最高の個体は次世代でも同一オブジェクトとして残る。"""
    min_population_for_elite = 10
    if EVOLUTION_ELITE_RATE > 0:
        min_population_for_elite = max(
            min_population_for_elite,
            int(np.ceil(1.0 / EVOLUTION_ELITE_RATE)),
        )
    manager = EvolutionManager(population_size=min_population_for_elite)
    top_index = len(manager.population) // 3
    top_individual = manager.population[top_index]
    fitness = [float(index + 1) for index in range(len(manager.population))]
    # 最高適応度個体を一意にするため、他の全個体より大きい値を置く。
    fitness[top_index] = max(fitness) + 1.0

    elites = manager.select_elites(manager.population, fitness)
    assert any(individual is top_individual for individual in elites)

    new_population = manager.next_generation(fitness)
    # エリート（少なくとも 1 個体）は次世代に「同じ参照」で含まれる
    assert any(individual is top_individual for individual in new_population)


def test_next_generation_invokes_crossover_for_non_elite_slots() -> None:
    """エリート以外の枠は crossover を経由して生成される。"""
    manager = EvolutionManager(population_size=5)
    fitness = [1.0, 2.0, 3.0, 4.0, 5.0]
    original_population = list(manager.population)
    elite_count = len(manager.select_elites(original_population, fitness))
    expected_child_count = manager.population_size - elite_count

    crossover_calls: list[tuple[NeuralNet, NeuralNet]] = []
    original_crossover = manager.crossover

    def spy(parent_a: NeuralNet, parent_b: NeuralNet) -> NeuralNet:
        crossover_calls.append((parent_a, parent_b))
        return original_crossover(parent_a, parent_b)

    manager.crossover = spy  # type: ignore[method-assign]
    try:
        manager.next_generation(fitness)
    finally:
        del manager.crossover  # type: ignore[attr-defined]

    # エリート以外の各子個体を作るたびに crossover が 1 回呼ばれる。
    assert len(crossover_calls) == expected_child_count
    # 親 2 体は population から選ばれている
    for parent_a, parent_b in crossover_calls:
        assert any(parent_a is individual for individual in original_population)
        assert any(parent_b is individual for individual in original_population)


def test_next_generation_increments_generation_counter() -> None:
    """next_generation 完了で世代番号が +1 される。"""
    manager = EvolutionManager(population_size=3)
    initial = manager.get_generation()
    manager.next_generation([1.0, 2.0, 3.0])
    assert manager.get_generation() == initial + 1


def test_crossover_mixes_parent_weights() -> None:
    manager = EvolutionManager(population_size=1)
    parent_a = NeuralNet(input_size=2, hidden_size=2, output_size=2)
    parent_b = NeuralNet(input_size=2, hidden_size=2, output_size=2)
    parent_a.set_weights([np.zeros_like(weights) for weights in parent_a.get_weights()])
    parent_b.set_weights([np.ones_like(weights) for weights in parent_b.get_weights()])
    random_state = np.random.get_state()

    try:
        np.random.seed(0)
        child = manager.crossover(parent_a, parent_b)
    finally:
        np.random.set_state(random_state)

    child_weights = child.get_weights()
    assert all(np.all((weights == 0.0) | (weights == 1.0)) for weights in child_weights)
    assert any(np.any(weights == 0.0) for weights in child_weights)
    assert any(np.any(weights == 1.0) for weights in child_weights)


def test_crossover_keeps_parents_independent() -> None:
    manager = EvolutionManager(population_size=1)
    parent_a = NeuralNet(input_size=2, hidden_size=2, output_size=2)
    parent_b = NeuralNet(input_size=2, hidden_size=2, output_size=2)
    parent_a_weights = parent_a.get_weights()
    parent_b_weights = parent_b.get_weights()

    child = manager.crossover(parent_a, parent_b)
    child.w1[0, 0] += 100.0

    assert all(
        np.array_equal(before, after)
        for before, after in zip(parent_a_weights, parent_a.get_weights(), strict=True)
    )
    assert all(
        np.array_equal(before, after)
        for before, after in zip(parent_b_weights, parent_b.get_weights(), strict=True)
    )


def test_mutate_rate_zero_keeps_weights_unchanged() -> None:
    manager = EvolutionManager(population_size=1)
    net = NeuralNet()
    original_weights = net.get_weights()

    manager.mutate(net, rate=0.0)

    mutated_weights = net.get_weights()
    assert all(
        np.array_equal(before, after)
        for before, after in zip(original_weights, mutated_weights, strict=True)
    )


def test_mutation_rate_zero_keeps_population_identical() -> None:
    """mutation_rate=0.0 keeps an identical-weight population unchanged after breeding."""
    random_state = np.random.get_state()
    try:
        np.random.seed(7)
        manager = EvolutionManager(population_size=4, mutation_rate=0.0)
        template_weights = [
            np.full_like(weights, fill_value=float(index + 1))
            for index, weights in enumerate(manager.population[0].get_weights())
        ]
        for net in manager.population:
            net.set_weights(template_weights)

        before = [net.get_weights() for net in manager.population]
        manager.next_generation([1.0, 0.5, 0.3, 0.1])
        after = [net.get_weights() for net in manager.population]
    finally:
        np.random.set_state(random_state)

    assert len(after) == len(before)
    assert all(_weights_match(weights, template_weights) for weights in after)


def test_mutate_rate_one_changes_weights() -> None:
    manager = EvolutionManager(population_size=1)
    net = NeuralNet()
    original_weights = net.get_weights()
    random_state = np.random.get_state()

    try:
        np.random.seed(0)
        manager.mutate(net, rate=1.0, scale=0.1)
    finally:
        np.random.set_state(random_state)

    mutated_weights = net.get_weights()
    assert any(
        not np.array_equal(before, after)
        for before, after in zip(original_weights, mutated_weights, strict=True)
    )


def test_calc_fitness_uses_enemy_record_values() -> None:
    manager = EvolutionManager(population_size=1)
    enemy_record = {
        "damage_dealt": 3,
        "survival_time": 20,
        "distance_improvement": 4,
    }
    expected = (
        enemy_record["damage_dealt"] * FITNESS_DAMAGE_WEIGHT
        + enemy_record["survival_time"] * FITNESS_SURVIVAL_WEIGHT
        + enemy_record["distance_improvement"] * FITNESS_DISTANCE_WEIGHT
    )
    assert manager.calc_fitness(enemy_record) == expected


def test_fitness_monotonicity() -> None:
    """Fitness increases when damage, survival, or distance progress increases."""
    manager = EvolutionManager(population_size=1)
    baseline = {
        "damage_dealt": 1.0,
        "survival_time": 1.0,
        "distance_improvement": 1.0,
    }
    base_fitness = manager.calc_fitness(baseline)

    assert manager.calc_fitness({**baseline, "damage_dealt": 2.0}) > base_fitness
    assert manager.calc_fitness({**baseline, "survival_time": 2.0}) > base_fitness
    assert manager.calc_fitness({**baseline, "distance_improvement": 2.0}) > base_fitness


def test_select_elites_returns_highest_fitness_individuals() -> None:
    manager = EvolutionManager(population_size=1)
    population = [NeuralNet() for _ in range(4)]
    fitness_list = [3.0, 10.0, 1.0, 7.0]

    elites = manager.select_elites(population, fitness_list, n_elite=2)

    assert elites == [population[1], population[3]]


def test_select_elites_uses_default_elite_rate() -> None:
    manager = EvolutionManager(population_size=1)
    population = [NeuralNet() for _ in range(10)]
    fitness_list = [float(index) for index in range(10)]
    expected_count = int(len(population) * EVOLUTION_ELITE_RATE)

    elites = manager.select_elites(population, fitness_list)

    assert len(elites) == expected_count
    assert elites[0] is population[-1]


def test_elite_always_preserved() -> None:
    """The first selected elite is always the unique maximum-fitness individual."""
    manager = EvolutionManager(population_size=1)
    population = [NeuralNet() for _ in range(5)]
    top_index = 2
    fitness_list = [0.0, 1.0, 9.0, 3.0, 2.0]

    elites = manager.select_elites(population, fitness_list, n_elite=1)

    assert elites[0] is population[top_index]


def test_tournament_select_returns_best_candidate() -> None:
    manager = EvolutionManager(population_size=1)
    population = [NeuralNet() for _ in range(EVOLUTION_TOURNAMENT_SIZE)]
    fitness_list = [1.0, 8.0, 3.0]

    selected = manager.tournament_select(
        population,
        fitness_list,
        k=EVOLUTION_TOURNAMENT_SIZE,
    )

    assert selected is population[1]


def test_evolution_improves_average_fitness_with_fixed_seed() -> None:
    """A fixed-seed deterministic fitness run improves average fitness over generations."""
    random_state = np.random.get_state()
    try:
        np.random.seed(42)
        manager = EvolutionManager(population_size=12, mutation_rate=EVOLUTION_MUTATION_RATE)
        averages: list[float] = []
        bests: list[float] = []

        for _generation in range(8):
            fitness = [_deterministic_network_fitness(net) for net in manager.population]
            averages.append(float(np.mean(fitness)))
            bests.append(max(fitness))
            manager.next_generation(fitness)

        final_fitness = [_deterministic_network_fitness(net) for net in manager.population]
        averages.append(float(np.mean(final_fitness)))
        bests.append(max(final_fitness))
    finally:
        np.random.set_state(random_state)

    assert averages[-1] > averages[0]
    assert all(next_best >= best - 1e-12 for best, next_best in pairwise(bests))


def test_parameter_grid_reuses_initial_seed_for_each_combination() -> None:
    """Parameter grid starts every combination from the same initial population."""
    random_state = np.random.get_state()
    original_mutation_rates = tune_parameters.EVOLUTION_TUNING_MUTATION_RATES
    original_tournament_sizes = tune_parameters.EVOLUTION_TUNING_TOURNAMENT_SIZES
    original_population_size = tune_parameters.EVOLUTION_TUNING_POPULATION_SIZE
    original_generation_count = tune_parameters.EVOLUTION_TUNING_GENERATION_COUNT
    mutation_rates = (0.01, 0.20)
    tournament_sizes = (2, 5)

    try:
        tune_parameters.EVOLUTION_TUNING_MUTATION_RATES = mutation_rates
        tune_parameters.EVOLUTION_TUNING_TOURNAMENT_SIZES = tournament_sizes
        tune_parameters.EVOLUTION_TUNING_POPULATION_SIZE = 6
        tune_parameters.EVOLUTION_TUNING_GENERATION_COUNT = 0
        weights = tune_parameters.FitnessWeights(
            name="test",
            damage=1.0,
            survival=1.0,
            distance=1.0,
        )

        rows = tune_parameters.run_parameter_grid(weights)
    finally:
        tune_parameters.EVOLUTION_TUNING_MUTATION_RATES = original_mutation_rates
        tune_parameters.EVOLUTION_TUNING_TOURNAMENT_SIZES = original_tournament_sizes
        tune_parameters.EVOLUTION_TUNING_POPULATION_SIZE = original_population_size
        tune_parameters.EVOLUTION_TUNING_GENERATION_COUNT = original_generation_count
        np.random.set_state(random_state)

    generation_zero_rows = [row for row in rows if row.gen == 0]
    assert len(generation_zero_rows) == len(mutation_rates) * len(tournament_sizes)
    first_row = generation_zero_rows[0]
    assert all(row.best_fitness == first_row.best_fitness for row in generation_zero_rows)
    assert all(row.avg_fitness == first_row.avg_fitness for row in generation_zero_rows)


def test_evolution_driver_waits_until_population_is_evaluated() -> None:
    manager = EvolutionManager(population_size=3)
    now = 0.0
    driver = EvolutionDriver(manager=manager, time_source=lambda: now)

    driver.spawn_enemy((100.0, 100.0))
    driver.spawn_enemy((100.0, 100.0))

    assert not driver.finalize_wave()
    assert manager.get_generation() == 1
    assert driver.get_evaluated_population_count() == 2
    assert driver.get_spawned_count() == 0

    driver.spawn_enemy((100.0, 100.0))

    assert driver.finalize_wave()
    assert manager.get_generation() == 2
    assert driver.get_evaluated_population_count() == 0
    assert driver.get_spawned_count() == 0


def test_evolution_driver_uses_locked_survival_time_for_dead_enemy() -> None:
    now = 0.0

    def current_time() -> float:
        return now

    manager = _CapturingEvolutionManager(population_size=2)
    driver = EvolutionDriver(manager=manager, time_source=current_time)
    early = driver.spawn_enemy((100.0, 100.0))
    driver.spawn_enemy((100.0, 100.0))

    now = 0.5
    early.take_damage(early.get_hp())
    driver.observe_frame()

    now = 5.0
    assert driver.finalize_wave()

    assert manager.captured_fitness is not None
    assert manager.captured_fitness[0] < manager.captured_fitness[1]


def test_spawned_enemies_share_hp_within_generation() -> None:
    """同一世代では全個体の最大HPが一致する（fitness 比較の公平性）。

    HP スケーリングをウェーブ依存にすると round-robin 評価で個体ごとに HP が
    変わり選択バイアスになるため、世代依存にして同一世代内は一定にしている。
    """
    manager = EvolutionManager(population_size=3)
    driver = EvolutionDriver(manager=manager)
    hps = [driver.spawn_enemy((100.0, 100.0)).get_max_hp() for _ in range(6)]
    assert len(set(hps)) == 1, "同一世代の敵は同じ最大HPを持つはず"
    assert hps[0] == ENEMY_BASE_HP, "世代1 は等倍（ENEMY_BASE_HP）であるべき"


def test_enemy_hp_increases_with_generation() -> None:
    """世代が進むと敵の最大HPが上がる（難易度スケーリング）。"""
    manager = EvolutionManager(population_size=2)
    driver = EvolutionDriver(manager=manager)
    gen1_hp = driver.spawn_enemy((100.0, 100.0)).get_max_hp()
    manager.next_generation([1.0, 2.0])  # 世代を 1 つ進める
    gen2_hp = driver.spawn_enemy((100.0, 100.0)).get_max_hp()
    assert gen2_hp > gen1_hp
    assert gen2_hp == round(ENEMY_BASE_HP * (1.0 + ENEMY_HP_GROWTH_PER_GENERATION))
