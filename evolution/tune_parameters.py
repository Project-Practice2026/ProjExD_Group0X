"""Run small deterministic sensitivity experiments for the evolution AI.

Usage:
    python -m evolution.tune_parameters

The script writes CSV files under docs/experiments. It is intentionally kept out
of CI because it is a small manual benchmark for presentation material and
fitness-weight tuning.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

from core.constants import (
    EVOLUTION_ELITE_RATE,
    EVOLUTION_MUTATION_RATE,
    EVOLUTION_TOURNAMENT_SIZE,
    EVOLUTION_TUNING_GENERATION_COUNT,
    EVOLUTION_TUNING_MUTATION_RATES,
    EVOLUTION_TUNING_POPULATION_SIZE,
    EVOLUTION_TUNING_SEED,
    EVOLUTION_TUNING_TOURNAMENT_SIZES,
    FITNESS_DAMAGE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_DAMAGE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_DISTANCE_WEIGHT,
    FITNESS_DISTANCE_FOCUS_SURVIVAL_WEIGHT,
    FITNESS_DISTANCE_WEIGHT,
    FITNESS_SURVIVAL_WEIGHT,
)
from evolution.evolution_manager import EvolutionManager
from evolution.neural_net import DEFAULT_INPUT_SIZE, NeuralNet

OUTPUT_DIR: Path = Path("docs") / "experiments"

EVAL_INPUTS: tuple[np.ndarray, ...] = (
    np.linspace(-1.0, 1.0, DEFAULT_INPUT_SIZE),
    np.linspace(1.0, -1.0, DEFAULT_INPUT_SIZE),
    np.sin(np.linspace(0.0, np.pi, DEFAULT_INPUT_SIZE)),
)
DAMAGE_SCORE_SCALE: float = 8.0
SURVIVAL_SCORE_SCALE: float = 6.0
DISTANCE_SCORE_SCALE: float = 10.0
TURN_PENALTY: float = 0.25


@dataclass(frozen=True)
class FitnessWeights:
    """Weight profile used to combine deterministic proxy metrics."""

    name: str
    damage: float
    survival: float
    distance: float


@dataclass(frozen=True)
class TuningRow:
    """One generation of the mutation-rate and tournament-size grid."""

    mutation_rate: float
    tournament_size: int
    elite_rate: float
    gen: int
    best_fitness: float
    avg_fitness: float


@dataclass(frozen=True)
class WeightSweepRow:
    """One generation from the fitness-weight sensitivity run."""

    weight_profile: str
    damage_weight: float
    survival_weight: float
    distance_weight: float
    gen: int
    best_fitness: float
    avg_fitness: float


class TunableEvolutionManager(EvolutionManager):
    """EvolutionManager variant with configurable tournament size for experiments."""

    def __init__(
        self,
        population_size: int,
        mutation_rate: float,
        tournament_size: int,
    ) -> None:
        self._tournament_size: int = tournament_size
        super().__init__(population_size=population_size, mutation_rate=mutation_rate)

    def tournament_select(
        self,
        population: list[NeuralNet],
        fitness_list: list[float],
        _k: int = EVOLUTION_TOURNAMENT_SIZE,
    ) -> NeuralNet:
        """Select using the script-provided tournament size."""
        return super().tournament_select(
            population,
            fitness_list,
            k=self._tournament_size,
        )


def _proxy_record(net: NeuralNet) -> dict[str, float]:
    """Convert a neural net into deterministic combat-like proxy metrics."""
    outputs = np.asarray([net.forward(input_vec) for input_vec in EVAL_INPUTS])
    forward_drive = float(np.mean(outputs[:, 0]))
    turn_amount = float(np.mean(np.abs(outputs[:, 1])))
    stability = max(0.0, 1.0 - turn_amount)

    return {
        "damage_dealt": max(0.0, forward_drive + 1.0) * DAMAGE_SCORE_SCALE,
        "survival_time": stability * SURVIVAL_SCORE_SCALE,
        "distance_improvement": max(0.0, forward_drive + 1.0 - turn_amount * TURN_PENALTY)
        * DISTANCE_SCORE_SCALE,
    }


def _weighted_fitness(net: NeuralNet, weights: FitnessWeights) -> float:
    """Calculate deterministic fitness using a supplied weight profile."""
    record = _proxy_record(net)
    return (
        record["damage_dealt"] * weights.damage
        + record["survival_time"] * weights.survival
        + record["distance_improvement"] * weights.distance
    )


def evaluate_population(
    manager: EvolutionManager,
    weights: FitnessWeights,
) -> list[float]:
    """Evaluate all networks in the current population."""
    return [_weighted_fitness(net, weights) for net in manager.population]


def run_parameter_grid(weights: FitnessWeights) -> list[TuningRow]:
    """Run the mutation-rate and tournament-size grid experiment."""
    rows: list[TuningRow] = []
    for mutation_rate in EVOLUTION_TUNING_MUTATION_RATES:
        for tournament_size in EVOLUTION_TUNING_TOURNAMENT_SIZES:
            # 各組み合わせを同じ初期個体群から開始し、差をハイパーパラメータ由来に寄せる。
            np.random.seed(EVOLUTION_TUNING_SEED)
            manager = TunableEvolutionManager(
                population_size=EVOLUTION_TUNING_POPULATION_SIZE,
                mutation_rate=mutation_rate,
                tournament_size=tournament_size,
            )
            for generation in range(EVOLUTION_TUNING_GENERATION_COUNT + 1):
                fitness = evaluate_population(manager, weights)
                rows.append(
                    TuningRow(
                        mutation_rate=mutation_rate,
                        tournament_size=tournament_size,
                        elite_rate=EVOLUTION_ELITE_RATE,
                        gen=generation,
                        best_fitness=max(fitness),
                        avg_fitness=float(np.mean(fitness)),
                    )
                )
                if generation < EVOLUTION_TUNING_GENERATION_COUNT:
                    manager.next_generation(fitness)
    return rows


def run_weight_sweep() -> list[WeightSweepRow]:
    """Run one baseline-vs-distance-focused fitness-weight comparison."""
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
    )
    rows: list[WeightSweepRow] = []
    for profile in profiles:
        np.random.seed(EVOLUTION_TUNING_SEED)
        manager = TunableEvolutionManager(
            population_size=EVOLUTION_TUNING_POPULATION_SIZE,
            mutation_rate=EVOLUTION_MUTATION_RATE,
            tournament_size=EVOLUTION_TOURNAMENT_SIZE,
        )
        for generation in range(EVOLUTION_TUNING_GENERATION_COUNT + 1):
            fitness = evaluate_population(manager, profile)
            rows.append(
                WeightSweepRow(
                    weight_profile=profile.name,
                    damage_weight=profile.damage,
                    survival_weight=profile.survival,
                    distance_weight=profile.distance,
                    gen=generation,
                    best_fitness=max(fitness),
                    avg_fitness=float(np.mean(fitness)),
                )
            )
            if generation < EVOLUTION_TUNING_GENERATION_COUNT:
                manager.next_generation(fitness)
    return rows


def _write_csv(path: Path, rows: list[TuningRow] | list[WeightSweepRow]) -> None:
    """Write dataclass rows to a CSV file."""
    if not rows:
        raise ValueError("rows must not be empty")

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _print_top_parameter_sets(rows: list[TuningRow]) -> None:
    """Print the final best-fitness ranking for quick terminal inspection."""
    final_rows = [row for row in rows if row.gen == EVOLUTION_TUNING_GENERATION_COUNT]
    ranked_rows = sorted(final_rows, key=lambda row: row.best_fitness, reverse=True)

    print("Top parameter sets by final best_fitness:")
    for row in ranked_rows[:5]:
        print(
            "  "
            f"mutation_rate={row.mutation_rate:.2f}, "
            f"tournament_size={row.tournament_size}, "
            f"best={row.best_fitness:.3f}, "
            f"avg={row.avg_fitness:.3f}"
        )


def main() -> None:
    """Run the manual benchmark and write timestamped CSV files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    baseline_weights = FitnessWeights(
        name="baseline",
        damage=FITNESS_DAMAGE_WEIGHT,
        survival=FITNESS_SURVIVAL_WEIGHT,
        distance=FITNESS_DISTANCE_WEIGHT,
    )

    tuning_rows = run_parameter_grid(baseline_weights)
    tuning_path = OUTPUT_DIR / f"evolution_tuning_{timestamp}.csv"
    _write_csv(tuning_path, tuning_rows)

    weight_rows = run_weight_sweep()
    weight_path = OUTPUT_DIR / f"evolution_weight_sweep_{timestamp}.csv"
    _write_csv(weight_path, weight_rows)

    print(f"Wrote {tuning_path}")
    print(f"Wrote {weight_path}")
    _print_top_parameter_sets(tuning_rows)


if __name__ == "__main__":
    main()
