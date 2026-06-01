"""Generate SVG charts from evolution experiment CSV files.

Usage:
    python evolution/visualize_experiments.py

The script intentionally uses only the standard library so experiment figures
can be regenerated without adding plotting dependencies.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal

EXPERIMENT_DIR: Path = Path("docs") / "experiments"
TUNING_PREFIX: str = "evolution_tuning"
WEIGHT_PREFIX: str = "evolution_weight_sweep"

SVG_NS: str = "http://www.w3.org/2000/svg"
FONT_FAMILY: str = "Arial, Helvetica, sans-serif"
BACKGROUND_COLOR: str = "#ffffff"
TEXT_COLOR: str = "#1f2937"
MUTED_TEXT_COLOR: str = "#6b7280"
GRID_COLOR: str = "#e5e7eb"
AXIS_COLOR: str = "#9ca3af"

LINE_COLORS: tuple[str, ...] = ("#2563eb", "#dc2626", "#16a34a", "#7c3aed")
PROFILE_COLORS: dict[str, str] = {
    "baseline": "#2563eb",
    "distance_focus": "#dc2626",
}
HEATMAP_COLORS: tuple[str, ...] = (
    "#eff6ff",
    "#bfdbfe",
    "#60a5fa",
    "#2563eb",
    "#1e3a8a",
)

TUNING_CHART_WIDTH: int = 1080
TUNING_CHART_HEIGHT: int = 620
WEIGHT_CHART_WIDTH: int = 980
WEIGHT_CHART_HEIGHT: int = 520
HEATMAP_WIDTH: int = 760
HEATMAP_HEIGHT: int = 480

CHART_TOP: float = 95.0
CHART_BOTTOM_MARGIN: float = 120.0
CHART_LEFT: float = 78.0
CHART_RIGHT_MARGIN: float = 42.0
PANEL_GAP: float = 38.0
TICK_COUNT: int = 5
LINE_WIDTH: float = 2.4
POINT_RADIUS: float = 3.2

FitnessMetric = Literal["best_fitness", "avg_fitness"]


@dataclass(frozen=True)
class TuningRecord:
    """One row from the mutation-rate and tournament-size CSV."""

    mutation_rate: float
    tournament_size: int
    elite_rate: float
    gen: int
    best_fitness: float
    avg_fitness: float


@dataclass(frozen=True)
class WeightRecord:
    """One row from the fitness-weight sweep CSV."""

    weight_profile: str
    damage_weight: float
    survival_weight: float
    distance_weight: float
    gen: int
    best_fitness: float
    avg_fitness: float


@dataclass(frozen=True)
class PlotArea:
    """Pixel rectangle used by one chart panel."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class LinearScale:
    """Map a numeric domain into an SVG coordinate range."""

    domain_min: float
    domain_max: float
    range_min: float
    range_max: float

    def map_value(self, value: float) -> float:
        """Map a data value to screen coordinates."""
        if self.domain_min == self.domain_max:
            return (self.range_min + self.range_max) / 2.0
        ratio = (value - self.domain_min) / (self.domain_max - self.domain_min)
        return self.range_min + ratio * (self.range_max - self.range_min)


@dataclass(frozen=True)
class AxisData:
    """Scales and ticks for one chart panel."""

    x_scale: LinearScale
    y_scale: LinearScale
    x_ticks: tuple[float, ...]
    y_ticks: tuple[float, ...]
    show_y_labels: bool


@dataclass(frozen=True)
class AxisSpec:
    """Input domain and ticks for building axes."""

    generations: list[int]
    y_domain: tuple[float, float]
    x_ticks: tuple[float, ...]
    y_ticks: tuple[float, ...]
    show_y_labels: bool


@dataclass(frozen=True)
class LineSeries:
    """A line to draw in a chart panel."""

    label: str
    values: tuple[tuple[int, float], ...]
    color: str
    dasharray: str = ""


@dataclass(frozen=True)
class LinePanel:
    """All data needed to draw one line-chart panel."""

    title: str
    area: PlotArea
    axis: AxisData
    series: tuple[LineSeries, ...]


@dataclass(frozen=True)
class HeatmapLayout:
    """Pixel layout for heatmap cells."""

    x0: float
    y0: float
    cell_width: float
    cell_height: float


@dataclass(frozen=True)
class Rect:
    """Pixel rectangle."""

    x: float
    y: float
    width: float
    height: float


def read_tuning_rows(path: Path) -> list[TuningRecord]:
    """Read parameter-tuning CSV rows."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return [
            TuningRecord(
                mutation_rate=float(row["mutation_rate"]),
                tournament_size=int(row["tournament_size"]),
                elite_rate=float(row["elite_rate"]),
                gen=int(row["gen"]),
                best_fitness=float(row["best_fitness"]),
                avg_fitness=float(row["avg_fitness"]),
            )
            for row in csv.DictReader(file)
        ]


def read_weight_rows(path: Path) -> list[WeightRecord]:
    """Read fitness-weight sweep CSV rows."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return [
            WeightRecord(
                weight_profile=row["weight_profile"],
                damage_weight=float(row["damage_weight"]),
                survival_weight=float(row["survival_weight"]),
                distance_weight=float(row["distance_weight"]),
                gen=int(row["gen"]),
                best_fitness=float(row["best_fitness"]),
                avg_fitness=float(row["avg_fitness"]),
            )
            for row in csv.DictReader(file)
        ]


def generate_visualizations(
    tuning_csv: Path | None = None,
    weight_csv: Path | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Generate all experiment SVG charts and return their paths."""
    target_dir = EXPERIMENT_DIR if output_dir is None else output_dir
    tuning_path = _latest_csv(TUNING_PREFIX) if tuning_csv is None else tuning_csv
    weight_path = _latest_csv(WEIGHT_PREFIX) if weight_csv is None else weight_csv

    tuning_rows = read_tuning_rows(tuning_path)
    weight_rows = read_weight_rows(weight_path)

    target_dir.mkdir(parents=True, exist_ok=True)
    output_paths = [
        target_dir / "evolution_tuning_best_fitness.svg",
        target_dir / "evolution_tuning_final_heatmap.svg",
        target_dir / "evolution_weight_sweep.svg",
    ]
    _write_text(output_paths[0], build_tuning_best_svg(tuning_rows, tuning_path.name))
    _write_text(output_paths[1], build_tuning_heatmap_svg(tuning_rows, tuning_path.name))
    _write_text(output_paths[2], build_weight_sweep_svg(weight_rows, weight_path.name))
    return output_paths


def build_tuning_best_svg(rows: list[TuningRecord], source_name: str) -> str:
    """Build a small-multiple line chart for best_fitness."""
    mutation_rates = sorted({row.mutation_rate for row in rows})
    tournament_sizes = sorted({row.tournament_size for row in rows})
    generations = sorted({row.gen for row in rows})
    y_domain = _padded_domain([row.best_fitness for row in rows])

    plot_width = _panel_width(TUNING_CHART_WIDTH, len(tournament_sizes))
    plot_height = TUNING_CHART_HEIGHT - CHART_TOP - CHART_BOTTOM_MARGIN
    x_ticks = tuple(float(value) for value in _integer_ticks(generations))
    y_ticks = _tick_values(y_domain)
    color_map = _color_map(mutation_rates, LINE_COLORS)

    body: list[str] = [
        _chart_title("Parameter Grid: best_fitness by generation", source_name),
        _rotated_axis_label("best_fitness", 26.0, 330.0),
        _bottom_axis_label("generation", TUNING_CHART_WIDTH / 2.0, 528.0),
    ]
    for index, tournament_size in enumerate(tournament_sizes):
        area = PlotArea(
            x=CHART_LEFT + index * (plot_width + PANEL_GAP),
            y=CHART_TOP,
            width=plot_width,
            height=plot_height,
        )
        axis = _axis_for_area(
            area,
            AxisSpec(generations, y_domain, x_ticks, y_ticks, index == 0),
        )
        series = tuple(
            LineSeries(
                label=f"mutation={_format_number(rate, 2)}",
                values=_tuning_series(rows, tournament_size, rate, "best_fitness"),
                color=color_map[rate],
            )
            for rate in mutation_rates
        )
        body.extend(
            _draw_line_panel(
                LinePanel(f"tournament_size={tournament_size}", area, axis, series),
            ),
        )

    body.extend(_draw_legend(_legend_items(mutation_rates, color_map), 250.0, 570.0))
    return _svg_document(TUNING_CHART_WIDTH, TUNING_CHART_HEIGHT, body)


def build_tuning_heatmap_svg(rows: list[TuningRecord], source_name: str) -> str:
    """Build a final-generation heatmap for best_fitness."""
    final_gen = max(row.gen for row in rows)
    final_rows = [row for row in rows if row.gen == final_gen]
    mutation_rates = sorted({row.mutation_rate for row in final_rows})
    tournament_sizes = sorted({row.tournament_size for row in final_rows})
    lookup = {(row.mutation_rate, row.tournament_size): row for row in final_rows}
    values = [row.best_fitness for row in final_rows]
    best_row = max(final_rows, key=lambda row: row.best_fitness)

    layout = HeatmapLayout(x0=178.0, y0=118.0, cell_width=118.0, cell_height=66.0)

    body: list[str] = [
        _chart_title(f"Final best_fitness heatmap (gen {final_gen})", source_name),
        f'<text x="{HEATMAP_WIDTH / 2:.1f}" y="94" class="axis-title">mutation_rate</text>',
        '<text x="54" y="216" class="axis-title" transform="rotate(-90 54 216)">'
        "tournament_size</text>",
        (
            f'<text x="{HEATMAP_WIDTH / 2:.1f}" y="420" class="note">'
            f"best: mutation={_format_number(best_row.mutation_rate, 2)}, "
            f"tournament={best_row.tournament_size}, "
            f"best_fitness={_format_number(best_row.best_fitness, 3)}</text>"
        ),
    ]
    body.extend(_draw_heatmap_headers(mutation_rates, tournament_sizes, layout))
    for row_index, tournament_size in enumerate(tournament_sizes):
        for col_index, mutation_rate in enumerate(mutation_rates):
            record = lookup[(mutation_rate, tournament_size)]
            rect = Rect(
                x=layout.x0 + col_index * layout.cell_width,
                y=layout.y0 + row_index * layout.cell_height,
                width=layout.cell_width,
                height=layout.cell_height,
            )
            body.append(_heatmap_cell(record.best_fitness, values, rect))

    return _svg_document(HEATMAP_WIDTH, HEATMAP_HEIGHT, body)


def build_weight_sweep_svg(rows: list[WeightRecord], source_name: str) -> str:
    """Build best and average fitness charts for the weight sweep."""
    profiles = sorted({row.weight_profile for row in rows})
    generations = sorted({row.gen for row in rows})
    y_domain = _padded_domain(
        [value for row in rows for value in (row.best_fitness, row.avg_fitness)]
    )
    plot_width = _panel_width(WEIGHT_CHART_WIDTH, 2)
    plot_height = WEIGHT_CHART_HEIGHT - CHART_TOP - CHART_BOTTOM_MARGIN
    x_ticks = tuple(float(value) for value in _integer_ticks(generations))
    y_ticks = _tick_values(y_domain)

    body: list[str] = [
        _chart_title("Fitness Weight Sweep", source_name),
        _rotated_axis_label("fitness", 26.0, 285.0),
        _bottom_axis_label("generation", WEIGHT_CHART_WIDTH / 2.0, 430.0),
    ]
    for index, metric in enumerate(("best_fitness", "avg_fitness")):
        area = PlotArea(
            x=CHART_LEFT + index * (plot_width + PANEL_GAP),
            y=CHART_TOP,
            width=plot_width,
            height=plot_height,
        )
        axis = _axis_for_area(
            area,
            AxisSpec(generations, y_domain, x_ticks, y_ticks, index == 0),
        )
        series = tuple(_weight_series(rows, profile, metric) for profile in profiles)
        body.extend(_draw_line_panel(LinePanel(metric, area, axis, series)))

    legend = tuple((profile, PROFILE_COLORS.get(profile, "#4b5563")) for profile in profiles)
    body.extend(_draw_legend(legend, 345.0, 470.0))
    return _svg_document(WEIGHT_CHART_WIDTH, WEIGHT_CHART_HEIGHT, body)


def main() -> None:
    """Run the CLI entry point."""
    args = _parse_args()
    outputs = generate_visualizations(args.tuning_csv, args.weight_csv, args.output_dir)
    for path in outputs:
        print(f"Wrote {path}")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tuning-csv", type=Path, default=None)
    parser.add_argument("--weight-csv", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=EXPERIMENT_DIR)
    return parser.parse_args()


def _latest_csv(prefix: str) -> Path:
    """Return the newest timestamped CSV for a prefix."""
    paths = sorted(EXPERIMENT_DIR.glob(f"{prefix}_*.csv"))
    if not paths:
        raise FileNotFoundError(f"No CSV files found for {prefix!r} in {EXPERIMENT_DIR}")
    return paths[-1]


def _write_text(path: Path, text: str) -> None:
    """Write UTF-8 text to a file."""
    path.write_text(text, encoding="utf-8")


def _svg_document(width: int, height: int, body: list[str]) -> str:
    """Wrap SVG body elements in a document."""
    style = f"""
    <style>
      svg {{ background: {BACKGROUND_COLOR}; font-family: {FONT_FAMILY}; }}
      .title {{ fill: {TEXT_COLOR}; font-size: 24px; font-weight: 700; text-anchor: middle; }}
      .subtitle {{ fill: {MUTED_TEXT_COLOR}; font-size: 12px; text-anchor: middle; }}
      .panel-title {{ fill: {TEXT_COLOR}; font-size: 14px; font-weight: 700; text-anchor: middle; }}
      .axis-label {{ fill: {MUTED_TEXT_COLOR}; font-size: 11px; text-anchor: middle; }}
      .axis-title {{ fill: {TEXT_COLOR}; font-size: 13px; font-weight: 700; text-anchor: middle; }}
      .note {{ fill: {TEXT_COLOR}; font-size: 13px; text-anchor: middle; }}
      .legend {{ fill: {TEXT_COLOR}; font-size: 12px; dominant-baseline: middle; }}
    </style>
    """
    content = "\n".join(body)
    return (
        f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n{style}\n{content}\n</svg>\n'
    )


def _chart_title(title: str, source_name: str) -> str:
    """Return a two-line chart title."""
    return (
        f'<text x="50%" y="38" class="title">{escape(title)}</text>'
        f'<text x="50%" y="62" class="subtitle">source: {escape(source_name)}</text>'
    )


def _rotated_axis_label(label: str, x: float, y: float) -> str:
    """Return a rotated y-axis label."""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="axis-title" '
        f'transform="rotate(-90 {x:.1f} {y:.1f})">{escape(label)}</text>'
    )


def _bottom_axis_label(label: str, x: float, y: float) -> str:
    """Return a centered x-axis label."""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="axis-title">{escape(label)}</text>'


def _panel_width(total_width: int, panel_count: int) -> float:
    """Calculate panel width for a row of panels."""
    usable = total_width - CHART_LEFT - CHART_RIGHT_MARGIN - PANEL_GAP * (panel_count - 1)
    return usable / panel_count


def _axis_for_area(
    area: PlotArea,
    spec: AxisSpec,
) -> AxisData:
    """Build axis data for a plot area."""
    return AxisData(
        x_scale=LinearScale(
            float(min(spec.generations)),
            float(max(spec.generations)),
            area.x,
            area.x + area.width,
        ),
        y_scale=LinearScale(
            spec.y_domain[0],
            spec.y_domain[1],
            area.y + area.height,
            area.y,
        ),
        x_ticks=spec.x_ticks,
        y_ticks=spec.y_ticks,
        show_y_labels=spec.show_y_labels,
    )


def _draw_line_panel(panel: LinePanel) -> list[str]:
    """Draw axes, title, and series for one line panel."""
    parts = [
        f'<text x="{panel.area.x + panel.area.width / 2:.1f}" y="{panel.area.y - 18:.1f}" '
        f'class="panel-title">{escape(panel.title)}</text>',
    ]
    parts.extend(_draw_axes(panel.area, panel.axis))
    for series in panel.series:
        parts.append(_polyline(series, panel.axis))
        parts.append(_last_point(series, panel.axis))
    return parts


def _draw_axes(area: PlotArea, axis: AxisData) -> list[str]:
    """Draw grid lines, axes, and numeric tick labels."""
    parts: list[str] = [
        _line(
            (area.x, area.y + area.height),
            (area.x + area.width, area.y + area.height),
            AXIS_COLOR,
            1.2,
        ),
        _line((area.x, area.y), (area.x, area.y + area.height), AXIS_COLOR, 1.2),
    ]
    for tick in axis.x_ticks:
        x = axis.x_scale.map_value(tick)
        parts.append(_line((x, area.y), (x, area.y + area.height), GRID_COLOR, 0.8))
        parts.append(
            f'<text x="{x:.1f}" y="{area.y + area.height + 20:.1f}" '
            f'class="axis-label">{_format_number(tick, 0)}</text>',
        )
    for tick in axis.y_ticks:
        y = axis.y_scale.map_value(tick)
        parts.append(_line((area.x, y), (area.x + area.width, y), GRID_COLOR, 0.8))
        if axis.show_y_labels:
            parts.append(
                f'<text x="{area.x - 10:.1f}" y="{y + 4:.1f}" '
                f'class="axis-label" text-anchor="end">{_format_number(tick, 1)}</text>',
            )
    return parts


def _polyline(series: LineSeries, axis: AxisData) -> str:
    """Draw one line series as an SVG polyline."""
    points = " ".join(
        f"{axis.x_scale.map_value(float(gen)):.1f},{axis.y_scale.map_value(value):.1f}"
        for gen, value in series.values
    )
    dash = f' stroke-dasharray="{series.dasharray}"' if series.dasharray else ""
    return (
        f'<polyline fill="none" stroke="{series.color}" stroke-width="{LINE_WIDTH}"'
        f' stroke-linejoin="round" stroke-linecap="round"{dash} points="{points}" />'
    )


def _last_point(series: LineSeries, axis: AxisData) -> str:
    """Draw the final point for a line series."""
    gen, value = series.values[-1]
    x = axis.x_scale.map_value(float(gen))
    y = axis.y_scale.map_value(value)
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{POINT_RADIUS:.1f}" fill="{series.color}" />'


def _line(start: tuple[float, float], end: tuple[float, float], color: str, width: float) -> str:
    """Draw one SVG line."""
    return (
        f'<line x1="{start[0]:.1f}" y1="{start[1]:.1f}" '
        f'x2="{end[0]:.1f}" y2="{end[1]:.1f}" '
        f'stroke="{color}" stroke-width="{width:.1f}" />'
    )


def _draw_legend(items: tuple[tuple[str, str], ...], x: float, y: float) -> list[str]:
    """Draw a horizontal legend."""
    parts: list[str] = []
    cursor = x
    for label, color in items:
        parts.append(_line((cursor, y), (cursor + 24.0, y), color, LINE_WIDTH))
        parts.append(
            f'<text x="{cursor + 32.0:.1f}" y="{y:.1f}" class="legend">{escape(label)}</text>',
        )
        cursor += max(116.0, len(label) * 8.0 + 54.0)
    return parts


def _legend_items(values: list[float], color_map: dict[float, str]) -> tuple[tuple[str, str], ...]:
    """Build legend labels for mutation-rate values."""
    return tuple((f"mutation={_format_number(value, 2)}", color_map[value]) for value in values)


def _draw_heatmap_headers(
    mutation_rates: list[float],
    tournament_sizes: list[int],
    layout: HeatmapLayout,
) -> list[str]:
    """Draw row and column labels for the heatmap."""
    parts: list[str] = []
    for col_index, mutation_rate in enumerate(mutation_rates):
        x = layout.x0 + col_index * layout.cell_width + layout.cell_width / 2.0
        parts.append(
            f'<text x="{x:.1f}" y="{layout.y0 - 18.0:.1f}" '
            f'class="axis-label">{_format_number(mutation_rate, 2)}</text>',
        )
    for row_index, tournament_size in enumerate(tournament_sizes):
        y = layout.y0 + row_index * layout.cell_height + layout.cell_height / 2.0 + 4.0
        parts.append(
            f'<text x="{layout.x0 - 24.0:.1f}" y="{y:.1f}" '
            f'class="axis-label" text-anchor="end">{tournament_size}</text>',
        )
    return parts


def _heatmap_cell(value: float, values: list[float], rect: Rect) -> str:
    """Draw one heatmap cell with a numeric label."""
    color = _heatmap_color(value, values)
    label_color = "#ffffff" if _normalized(value, values) > 0.55 else TEXT_COLOR
    return (
        f'<rect x="{rect.x:.1f}" y="{rect.y:.1f}" '
        f'width="{rect.width:.1f}" height="{rect.height:.1f}" '
        f'fill="{color}" stroke="{BACKGROUND_COLOR}" stroke-width="2" />'
        f'<text x="{rect.x + rect.width / 2.0:.1f}" '
        f'y="{rect.y + rect.height / 2.0 + 5.0:.1f}" '
        f'fill="{label_color}" font-size="15" font-weight="700" text-anchor="middle">'
        f"{_format_number(value, 1)}</text>"
    )


def _heatmap_color(value: float, values: list[float]) -> str:
    """Map a value to a heatmap color."""
    ratio = _normalized(value, values)
    index = min(int(ratio * (len(HEATMAP_COLORS) - 1)), len(HEATMAP_COLORS) - 1)
    return HEATMAP_COLORS[index]


def _normalized(value: float, values: list[float]) -> float:
    """Normalize a value inside a collection to 0.0 through 1.0."""
    low = min(values)
    high = max(values)
    if low == high:
        return 1.0
    return (value - low) / (high - low)


def _color_map(values: list[float], colors: tuple[str, ...]) -> dict[float, str]:
    """Assign colors to numeric values."""
    return {value: colors[index % len(colors)] for index, value in enumerate(values)}


def _tuning_series(
    rows: list[TuningRecord],
    tournament_size: int,
    mutation_rate: float,
    metric: FitnessMetric,
) -> tuple[tuple[int, float], ...]:
    """Extract one parameter-grid line series."""
    values = [
        (row.gen, _metric_value(row, metric))
        for row in rows
        if row.tournament_size == tournament_size and row.mutation_rate == mutation_rate
    ]
    return tuple(sorted(values))


def _weight_series(rows: list[WeightRecord], profile: str, metric: FitnessMetric) -> LineSeries:
    """Extract one weight-sweep line series."""
    values = [
        (row.gen, _metric_value(row, metric)) for row in rows if row.weight_profile == profile
    ]
    return LineSeries(
        label=profile,
        values=tuple(sorted(values)),
        color=PROFILE_COLORS.get(profile, "#4b5563"),
    )


def _metric_value(row: TuningRecord | WeightRecord, metric: FitnessMetric) -> float:
    """Return the requested fitness metric from a row."""
    if metric == "best_fitness":
        return row.best_fitness
    return row.avg_fitness


def _padded_domain(values: list[float]) -> tuple[float, float]:
    """Return a y-domain with visual padding."""
    low = min(values)
    high = max(values)
    padding = max((high - low) * 0.08, 1.0)
    return low - padding, high + padding


def _integer_ticks(values: list[int]) -> tuple[int, ...]:
    """Return a compact set of integer x-axis ticks."""
    low = min(values)
    high = max(values)
    if high == low:
        return (low,)
    step = max(1, round((high - low) / (TICK_COUNT - 1)))
    ticks = tuple(range(low, high + 1, step))
    return ticks if ticks[-1] == high else (*ticks, high)


def _tick_values(domain: tuple[float, float]) -> tuple[float, ...]:
    """Return evenly spaced y-axis tick values."""
    low, high = domain
    return tuple(low + (high - low) * index / (TICK_COUNT - 1) for index in range(TICK_COUNT))


def _format_number(value: float, digits: int) -> str:
    """Format a number without unnecessary trailing zeroes."""
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


if __name__ == "__main__":
    main()
