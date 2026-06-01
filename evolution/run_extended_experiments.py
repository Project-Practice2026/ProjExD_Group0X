"""Run extended evolution tuning experiments for presentation material.

Usage:
    python -m evolution.run_extended_experiments

This script keeps the game default NeuralNet unchanged and compares extra
conditions in reproducible CSV files under docs/experiments.
"""

from __future__ import annotations

import csv
import math
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from core.constants import (
    EVOLUTION_ELITE_RATE,
    EVOLUTION_MUTATION_RATE,
    EVOLUTION_TOURNAMENT_SIZE,
    EVOLUTION_TUNING_POPULATION_SIZE,
    EVOLUTION_TUNING_SEED,
    FITNESS_DAMAGE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_DAMAGE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_DISTANCE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_SURVIVAL_WEIGHT,
    FITNESS_DISTANCE_WEIGHT,
    FITNESS_SURVIVAL_WEIGHT,
)
from evolution.evolution_manager import EvolutionManager
from evolution.neural_net import (
    DEFAULT_INPUT_SIZE,
    DEFAULT_OUTPUT_SIZE,
    WEIGHT_INIT_SCALE,
    NeuralNet,
)
from evolution.tune_parameters import (
    DAMAGE_SCORE_SCALE,
    DISTANCE_SCORE_SCALE,
    EVAL_INPUTS,
    SURVIVAL_SCORE_SCALE,
    TURN_PENALTY,
    FitnessWeights,
)

OUTPUT_DIR: Path = Path("docs") / "experiments"

SEEDS: tuple[int, ...] = tuple(EVOLUTION_TUNING_SEED + offset for offset in range(5))
STANDARD_GENERATIONS: int = 24
LONG_GENERATIONS: int = 36
MUTATION_FINE_RATES: tuple[float, ...] = (0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30)
POPULATION_SIZES: tuple[int, ...] = (8, 16, 24, 32)
ELITE_RATES: tuple[float, ...] = (0.10, 0.20, 0.30)
TOURNAMENT_SIZES: tuple[int, ...] = (3, 4, 5)
ARCHITECTURES: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("1x16", (16,)),
    ("2x16", (16, 16)),
    ("32x16", (32, 16)),
    ("2x32", (32, 32)),
)


@dataclass(frozen=True)
class ExperimentConfig:
    """One reproducible evolution experiment setting."""

    experiment: str
    condition: str
    seed: int
    generation_count: int
    population_size: int = EVOLUTION_TUNING_POPULATION_SIZE
    mutation_rate: float = EVOLUTION_MUTATION_RATE
    tournament_size: int = EVOLUTION_TOURNAMENT_SIZE
    elite_rate: float = EVOLUTION_ELITE_RATE
    architecture: str = "1x16"
    hidden_sizes: tuple[int, ...] = (16,)
    input_pattern: str = "default"
    eval_inputs: tuple[np.ndarray, ...] | None = None
    weights: FitnessWeights | None = None


@dataclass(frozen=True)
class ExperimentRow:
    """One generation result from an extended experiment run."""

    experiment: str
    condition: str
    seed: int
    generation_count: int
    gen: int
    population_size: int
    mutation_rate: float
    tournament_size: int
    elite_rate: float
    architecture: str
    parameter_count: int
    input_pattern: str
    weight_profile: str
    best_fitness: float
    avg_fitness: float


@dataclass(frozen=True)
class SummaryRow:
    """Mean final result for one experiment condition over all seeds."""

    experiment: str
    condition: str
    runs: int
    final_gen: int
    mean_final_best: float
    std_final_best: float
    mean_final_avg: float
    std_final_avg: float
    mean_best_gain: float
    mean_avg_gain: float


class LayeredNeuralNet:
    """Small fully connected tanh network with configurable hidden layers."""

    def __init__(
        self,
        hidden_sizes: tuple[int, ...],
        input_size: int = DEFAULT_INPUT_SIZE,
        output_size: int = DEFAULT_OUTPUT_SIZE,
    ) -> None:
        """Initialize weights for all hidden layers and the output layer."""
        if not hidden_sizes:
            raise ValueError("hidden_sizes must not be empty")
        self._input_size: int = input_size
        self._hidden_sizes: tuple[int, ...] = hidden_sizes
        self._output_size: int = output_size
        layer_sizes = (input_size, *hidden_sizes, output_size)
        self._weights: list[np.ndarray] = [
            np.random.randn(layer_sizes[index], layer_sizes[index + 1]) * WEIGHT_INIT_SCALE
            for index in range(len(layer_sizes) - 1)
        ]
        self._biases: list[np.ndarray] = [
            np.zeros(layer_sizes[index + 1]) for index in range(len(layer_sizes) - 1)
        ]

    @property
    def input_size(self) -> int:
        """Return the input layer size."""
        return self._input_size

    @property
    def hidden_size(self) -> int:
        """Return the first hidden layer size for compatibility."""
        return self._hidden_sizes[0]

    @property
    def output_size(self) -> int:
        """Return the output layer size."""
        return self._output_size

    def forward(self, input_vec: np.ndarray) -> np.ndarray:
        """Run tanh forward propagation through all layers."""
        value = np.asarray(input_vec, dtype=float)
        if value.shape != (self._input_size,):
            expected_shape = (self._input_size,)
            raise ValueError(f"input_vec must have shape {expected_shape}, got {value.shape}")
        for weights, bias in zip(self._weights, self._biases, strict=True):
            value = np.tanh(value @ weights + bias)
        return value

    def get_weights(self) -> list[np.ndarray]:
        """Return defensive copies of all weight and bias arrays."""
        arrays: list[np.ndarray] = []
        for weights, bias in zip(self._weights, self._biases, strict=True):
            arrays.append(weights.copy())
            arrays.append(bias.copy())
        return arrays

    def set_weights(self, weights: list[np.ndarray]) -> None:
        """Set all weight and bias arrays from defensive copies."""
        expected_count = len(self._weights) * 2
        if len(weights) != expected_count:
            raise ValueError(f"weights must have {expected_count} arrays, got {len(weights)}")

        new_weights: list[np.ndarray] = []
        new_biases: list[np.ndarray] = []
        for index, current_weights in enumerate(self._weights):
            supplied_weights = weights[index * 2]
            supplied_bias = weights[index * 2 + 1]
            if supplied_weights.shape != current_weights.shape:
                raise ValueError("weight shape mismatch")
            if supplied_bias.shape != self._biases[index].shape:
                raise ValueError("bias shape mismatch")
            new_weights.append(supplied_weights.copy())
            new_biases.append(supplied_bias.copy())
        self._weights = new_weights
        self._biases = new_biases

    def clone(self) -> LayeredNeuralNet:
        """Create an independent copy with identical parameters."""
        new_net = LayeredNeuralNet(self._hidden_sizes, self._input_size, self._output_size)
        new_net.set_weights(self.get_weights())
        return new_net


class ConfigurableEvolutionManager(EvolutionManager):
    """EvolutionManager variant for experiment-only tournament and elite settings."""

    def __init__(
        self,
        config: ExperimentConfig,
        net_factory: Callable[[], NeuralNet | LayeredNeuralNet],
    ) -> None:
        """Create a population from the supplied network factory."""
        self._experiment_tournament_size: int = config.tournament_size
        self._experiment_elite_rate: float = config.elite_rate
        population = [net_factory() for _ in range(config.population_size)]
        super().__init__(
            population_size=config.population_size,
            mutation_rate=config.mutation_rate,
            population=population,
        )

    def select_elites(
        self,
        population: list[NeuralNet],
        fitness_list: list[float],
        n_elite: int | None = None,
    ) -> list[NeuralNet]:
        """Select elites using the experiment-provided elite rate."""
        elite_count = n_elite
        if elite_count is None:
            elite_count = max(1, int(len(population) * self._experiment_elite_rate))
        return super().select_elites(population, fitness_list, n_elite=elite_count)

    def tournament_select(
        self,
        population: list[NeuralNet],
        fitness_list: list[float],
        _k: int = EVOLUTION_TOURNAMENT_SIZE,
    ) -> NeuralNet:
        """Select parents using the experiment-provided tournament size."""
        return super().tournament_select(
            population,
            fitness_list,
            k=self._experiment_tournament_size,
        )


def run_extended_experiments() -> list[ExperimentRow]:
    """Run all extended experiment families."""
    rows: list[ExperimentRow] = []
    for config in _build_experiment_configs():
        rows.extend(_run_config(config))
    return rows


def summarize_rows(rows: list[ExperimentRow]) -> list[SummaryRow]:
    """Summarize final-generation performance by condition."""
    summaries: list[SummaryRow] = []
    group_keys = sorted({(row.experiment, row.condition) for row in rows})
    for experiment, condition in group_keys:
        group = [row for row in rows if row.experiment == experiment and row.condition == condition]
        final_gen = max(row.gen for row in group)
        final_rows = [row for row in group if row.gen == final_gen]
        initial_rows = [row for row in group if row.gen == 0]
        initial_by_seed = {row.seed: row for row in initial_rows}
        best_gains = [
            row.best_fitness - initial_by_seed[row.seed].best_fitness for row in final_rows
        ]
        avg_gains = [row.avg_fitness - initial_by_seed[row.seed].avg_fitness for row in final_rows]
        summaries.append(
            SummaryRow(
                experiment=experiment,
                condition=condition,
                runs=len(final_rows),
                final_gen=final_gen,
                mean_final_best=_mean(row.best_fitness for row in final_rows),
                std_final_best=_std(row.best_fitness for row in final_rows),
                mean_final_avg=_mean(row.avg_fitness for row in final_rows),
                std_final_avg=_std(row.avg_fitness for row in final_rows),
                mean_best_gain=_mean(best_gains),
                mean_avg_gain=_mean(avg_gains),
            )
        )
    return summaries


def main() -> None:
    """Run experiments and write raw and summary CSV files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rows = run_extended_experiments()
    summaries = summarize_rows(rows)

    raw_path = OUTPUT_DIR / f"evolution_extended_experiments_{timestamp}.csv"
    summary_path = OUTPUT_DIR / f"evolution_extended_summary_{timestamp}.csv"
    _write_csv(raw_path, rows)
    _write_csv(summary_path, summaries)

    print(f"Wrote {raw_path}")
    print(f"Wrote {summary_path}")
    _print_highlights(summaries)


def _build_experiment_configs() -> list[ExperimentConfig]:
    """Build the full set of extended experiment configurations."""
    baseline_weights = FitnessWeights(
        name="baseline",
        damage=FITNESS_DAMAGE_WEIGHT,
        survival=FITNESS_SURVIVAL_WEIGHT,
        distance=FITNESS_DISTANCE_WEIGHT,
    )
    configs: list[ExperimentConfig] = []
    configs.extend(_seed_repeat_configs(baseline_weights))
    configs.extend(_mutation_fine_configs(baseline_weights))
    configs.extend(_long_run_configs(baseline_weights))
    configs.extend(_population_configs(baseline_weights))
    configs.extend(_elite_tournament_configs(baseline_weights))
    configs.extend(_weight_profile_configs())
    configs.extend(_architecture_configs(baseline_weights))
    configs.extend(_input_pattern_configs(baseline_weights))
    return configs


def _seed_repeat_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build multi-seed checks for representative parameter sets."""
    parameter_sets = (
        ("default_0.05_t3", 0.05, 3),
        ("fast_best_0.20_t3", 0.20, 3),
        ("fast_avg_0.20_t5", 0.20, 5),
        ("middle_0.10_t5", 0.10, 5),
    )
    return [
        ExperimentConfig(
            experiment="seed_repeat",
            condition=name,
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=mutation_rate,
            tournament_size=tournament_size,
            weights=weights,
        )
        for name, mutation_rate, tournament_size in parameter_sets
        for seed in SEEDS
    ]


def _mutation_fine_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build fine mutation-rate sweep configs."""
    return [
        ExperimentConfig(
            experiment="mutation_fine",
            condition=f"mutation_{mutation_rate:.3f}",
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=mutation_rate,
            tournament_size=5,
            weights=weights,
        )
        for mutation_rate in MUTATION_FINE_RATES
        for seed in SEEDS
    ]


def _long_run_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build longer-generation runs for growth-curve comparison."""
    return [
        ExperimentConfig(
            experiment="long_run",
            condition=name,
            seed=seed,
            generation_count=LONG_GENERATIONS,
            mutation_rate=mutation_rate,
            tournament_size=tournament_size,
            weights=weights,
        )
        for name, mutation_rate, tournament_size in (
            ("default_0.05_t3", 0.05, 3),
            ("fast_0.20_t5", 0.20, 5),
        )
        for seed in SEEDS
    ]


def _population_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build population-size sweep configs."""
    return [
        ExperimentConfig(
            experiment="population_size",
            condition=f"population_{population_size}",
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            population_size=population_size,
            mutation_rate=0.20,
            tournament_size=5,
            weights=weights,
        )
        for population_size in POPULATION_SIZES
        for seed in SEEDS
    ]


def _elite_tournament_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build elite-rate and tournament-size grid configs."""
    return [
        ExperimentConfig(
            experiment="elite_tournament",
            condition=f"elite_{elite_rate:.2f}_t{tournament_size}",
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=0.20,
            tournament_size=tournament_size,
            elite_rate=elite_rate,
            weights=weights,
        )
        for elite_rate in ELITE_RATES
        for tournament_size in TOURNAMENT_SIZES
        for seed in SEEDS
    ]


def _weight_profile_configs() -> list[ExperimentConfig]:
    """Build fitness-weight profile comparison configs."""
    profiles = (
        FitnessWeights(
            name="baseline",
            damage=FITNESS_DAMAGE_WEIGHT,
            survival=FITNESS_SURVIVAL_WEIGHT,
            distance=FITNESS_DISTANCE_WEIGHT,
        ),
        FitnessWeights(
            name="distance_focus",
            damage=FITNESS_DISTANCE_FOCUS_DAMAGE_WEIGHT,
            survival=FITNESS_DISTANCE_FOCUS_SURVIVAL_WEIGHT,
            distance=FITNESS_DISTANCE_FOCUS_DISTANCE_WEIGHT,
        ),
        FitnessWeights(name="survival_focus", damage=8.0, survival=4.0, distance=5.0),
        FitnessWeights(name="aggressive", damage=14.0, survival=0.5, distance=4.0),
    )
    return [
        ExperimentConfig(
            experiment="weight_profile",
            condition=profile.name,
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=0.20,
            tournament_size=5,
            weights=profile,
        )
        for profile in profiles
        for seed in SEEDS
    ]


def _architecture_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build NN architecture comparison configs."""
    return [
        ExperimentConfig(
            experiment="architecture",
            condition=f"{name}_mutation_{mutation_rate:.2f}",
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=mutation_rate,
            tournament_size=5,
            architecture=name,
            hidden_sizes=hidden_sizes,
            weights=weights,
        )
        for name, hidden_sizes in ARCHITECTURES
        for mutation_rate in (0.05, 0.20)
        for seed in SEEDS
    ]


def _input_pattern_configs(weights: FitnessWeights) -> list[ExperimentConfig]:
    """Build proxy-input pattern robustness configs."""
    return [
        ExperimentConfig(
            experiment="input_pattern",
            condition=name,
            seed=seed,
            generation_count=STANDARD_GENERATIONS,
            mutation_rate=0.20,
            tournament_size=5,
            input_pattern=name,
            eval_inputs=inputs,
            weights=weights,
        )
        for name, inputs in _input_patterns()
        for seed in SEEDS
    ]


def _run_config(config: ExperimentConfig) -> list[ExperimentRow]:
    """Run one config and collect each generation result."""
    np.random.seed(config.seed)
    weights = _weights_or_default(config)
    eval_inputs = EVAL_INPUTS if config.eval_inputs is None else config.eval_inputs
    manager = ConfigurableEvolutionManager(config, _net_factory(config.hidden_sizes))
    parameter_count = _parameter_count(config.hidden_sizes)
    rows: list[ExperimentRow] = []

    for generation in range(config.generation_count + 1):
        fitness = _evaluate_population(manager, weights, eval_inputs)
        rows.append(
            ExperimentRow(
                experiment=config.experiment,
                condition=config.condition,
                seed=config.seed,
                generation_count=config.generation_count,
                gen=generation,
                population_size=config.population_size,
                mutation_rate=config.mutation_rate,
                tournament_size=config.tournament_size,
                elite_rate=config.elite_rate,
                architecture=config.architecture,
                parameter_count=parameter_count,
                input_pattern=config.input_pattern,
                weight_profile=weights.name,
                best_fitness=max(fitness),
                avg_fitness=float(np.mean(fitness)),
            )
        )
        if generation < config.generation_count:
            manager.next_generation(fitness)
    return rows


def _evaluate_population(
    manager: EvolutionManager,
    weights: FitnessWeights,
    eval_inputs: tuple[np.ndarray, ...],
) -> list[float]:
    """Evaluate a population with a configurable proxy input set."""
    return [_weighted_fitness(net, weights, eval_inputs) for net in manager.population]


def _weighted_fitness(
    net: NeuralNet | LayeredNeuralNet,
    weights: FitnessWeights,
    eval_inputs: tuple[np.ndarray, ...],
) -> float:
    """Calculate weighted proxy fitness for one network."""
    record = _proxy_record(net, eval_inputs)
    return (
        record["damage_dealt"] * weights.damage
        + record["survival_time"] * weights.survival
        + record["distance_improvement"] * weights.distance
    )


def _proxy_record(
    net: NeuralNet | LayeredNeuralNet,
    eval_inputs: tuple[np.ndarray, ...],
) -> dict[str, float]:
    """Convert network outputs into deterministic proxy metrics."""
    outputs = np.asarray([net.forward(input_vec) for input_vec in eval_inputs])
    forward_drive = float(np.mean(outputs[:, 0]))
    turn_amount = float(np.mean(np.abs(outputs[:, 1])))
    stability = max(0.0, 1.0 - turn_amount)
    return {
        "damage_dealt": max(0.0, forward_drive + 1.0) * DAMAGE_SCORE_SCALE,
        "survival_time": stability * SURVIVAL_SCORE_SCALE,
        "distance_improvement": max(0.0, forward_drive + 1.0 - turn_amount * TURN_PENALTY)
        * DISTANCE_SCORE_SCALE,
    }


def _input_patterns() -> tuple[tuple[str, tuple[np.ndarray, ...]], ...]:
    """Return proxy input sets used to check overfitting to fixed observations."""
    return (
        ("default", EVAL_INPUTS),
        (
            "tower_pressure",
            (
                _input_vec(
                    (0.9, 0.65, 0.0, 0.10, 0.00, 0.25, -0.12, 0.10, 0.50, 0.22, -0.08, 1.00),
                ),
                _input_vec(
                    (0.6, 0.40, -0.15, 0.08, -0.10, 0.75, 0.14, 0.16, 0.50, -0.18, 0.05, 0.25),
                ),
                _input_vec(
                    (0.3, 0.24, 0.18, -0.10, 0.06, 1.00, 0.18, -0.08, 0.75, 0.30, 0.00, 0.50),
                ),
            ),
        ),
        (
            "mixed_positions",
            (
                _input_vec(
                    (1.0, 0.85, 0.20, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                ),
                _input_vec(
                    (0.7, 0.35, -0.35, 0.20, 0.18, 0.25, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                ),
                _input_vec(
                    (0.4, 0.12, 0.40, -0.08, -0.22, 0.50, 0.16, 0.08, 1.00, 0.00, 0.00, 0.00),
                ),
            ),
        ),
    )


def _input_vec(values: tuple[float, ...]) -> np.ndarray:
    """Build a fixed-size proxy observation vector."""
    if len(values) != DEFAULT_INPUT_SIZE:
        raise ValueError("input pattern length must match DEFAULT_INPUT_SIZE")
    return np.asarray(values, dtype=float)


def _weights_or_default(config: ExperimentConfig) -> FitnessWeights:
    """Return the configured weights or the baseline profile."""
    if config.weights is not None:
        return config.weights
    return FitnessWeights(
        name="baseline",
        damage=FITNESS_DAMAGE_WEIGHT,
        survival=FITNESS_SURVIVAL_WEIGHT,
        distance=FITNESS_DISTANCE_WEIGHT,
    )


def _net_factory(hidden_sizes: tuple[int, ...]) -> Callable[[], NeuralNet | LayeredNeuralNet]:
    """Return a network factory for an architecture."""
    if hidden_sizes == (16,):
        return NeuralNet
    return lambda: LayeredNeuralNet(hidden_sizes)


def _parameter_count(hidden_sizes: tuple[int, ...]) -> int:
    """Return the number of trainable parameters for an architecture."""
    layer_sizes = (DEFAULT_INPUT_SIZE, *hidden_sizes, DEFAULT_OUTPUT_SIZE)
    return sum(
        layer_sizes[index] * layer_sizes[index + 1] + layer_sizes[index + 1]
        for index in range(len(layer_sizes) - 1)
    )


def _write_csv(path: Path, rows: list[ExperimentRow] | list[SummaryRow]) -> None:
    """Write dataclass rows to CSV."""
    if not rows:
        raise ValueError("rows must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _print_highlights(summaries: list[SummaryRow]) -> None:
    """Print compact highlights for terminal inspection."""
    print("Top summary rows by mean_final_avg:")
    for row in sorted(summaries, key=lambda item: item.mean_final_avg, reverse=True)[:8]:
        print(
            f"  {row.experiment}/{row.condition}: "
            f"best={row.mean_final_best:.3f}, "
            f"avg={row.mean_final_avg:.3f}, "
            f"avg_gain={row.mean_avg_gain:.3f}"
        )


def _mean(values: Iterable[float]) -> float:
    """Return the arithmetic mean of values."""
    value_list = list(values)
    return float(sum(value_list) / len(value_list))


def _std(values: Iterable[float]) -> float:
    """Return the population standard deviation of values."""
    value_list = list(values)
    average = _mean(value_list)
    variance = sum((value - average) ** 2 for value in value_list) / len(value_list)
    return float(math.sqrt(variance))


if __name__ == "__main__":
    main()
