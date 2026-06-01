"""適応度グラフ表示。

世代ごとの最高適応度・平均適応度をリアルタイムで線グラフ描画する。
matplotlib は重いので pygame の draw.line のみで実装。

ゲームループから `add(gen, best, avg)` を世代終了ごとに呼び、`draw(screen, rect)`
で任意位置に描画する。データは直近 `GRAPH_MAX_GENERATIONS` 世代分のみ保持。
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame as pg

try:
    from ..core.constants import (
        COLOR_TEXT,
        GRAPH_BG_COLOR,
        GRAPH_DEFAULT_HEIGHT,
        GRAPH_DEFAULT_WIDTH,
        GRAPH_GRID_COLOR,
        GRAPH_LINE_AVG,
        GRAPH_LINE_BEST,
        GRAPH_MAX_GENERATIONS,
    )
except ImportError:
    from core.constants import (
        COLOR_TEXT,
        GRAPH_BG_COLOR,
        GRAPH_DEFAULT_HEIGHT,
        GRAPH_DEFAULT_WIDTH,
        GRAPH_GRID_COLOR,
        GRAPH_LINE_AVG,
        GRAPH_LINE_BEST,
        GRAPH_MAX_GENERATIONS,
    )


from core.fonts import get_font


@dataclass(frozen=True)
class GenerationRecord:
    """1 世代分の適応度記録。"""

    generation: int
    best: float
    avg: float


class EvolutionGraph:
    """進化グラフを描画する。データ供給は外部から `add()` で行う。"""

    def __init__(
        self,
        max_records: int = GRAPH_MAX_GENERATIONS,
        width: int = GRAPH_DEFAULT_WIDTH,
        height: int = GRAPH_DEFAULT_HEIGHT,
    ) -> None:
        self._records: list[GenerationRecord] = []
        self._max_records: int = max(2, int(max_records))
        self._width: int = max(40, int(width))
        self._height: int = max(20, int(height))
        if not pg.font.get_init():
            pg.font.init()
        self._font: pg.font.Font = get_font(14)

    # ----- accessors -----

    def get_records(self) -> list[GenerationRecord]:
        """Records を返す。"""
        return list(self._records)

    def get_width(self) -> int:
        """Width を返す。"""
        return self._width

    def get_height(self) -> int:
        """Height を返す。"""
        return self._height

    def get_latest(self) -> GenerationRecord | None:
        """Latest を返す。"""
        return self._records[-1] if self._records else None

    # ----- mutators -----

    def add(self, generation: int, best: float, avg: float) -> None:
        """世代記録を追加する。`_max_records` を超えた古い世代から落とす。"""
        record = GenerationRecord(
            generation=int(generation),
            best=float(best),
            avg=float(avg),
        )
        self._records.append(record)
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records :]

    def clear(self) -> None:
        """Clear を行う。"""
        self._records.clear()

    # ----- draw -----

    def draw(
        self,
        screen: pg.Surface,
        origin: tuple[int, int],
        size: tuple[int, int] | None = None,
    ) -> None:
        """`origin` を左上座標としてグラフを描画する。"""
        w, h = size if size is not None else (self._width, self._height)
        x, y = origin
        bg_rect = pg.Rect(x, y, w, h)
        pg.draw.rect(screen, GRAPH_BG_COLOR, bg_rect)
        pg.draw.rect(screen, GRAPH_GRID_COLOR, bg_rect, width=1)

        if len(self._records) < 2:
            self._blit_label(screen, "Evolution Graph (no data)", (x + 4, y + 4))
            return

        max_value = max(*(r.best for r in self._records), 1.0)
        min_value = min(*(r.avg for r in self._records), 0.0)
        value_range = max(1.0, max_value - min_value)

        # グリッド線（横3本）
        for i in range(1, 3):
            yy = y + int(h * i / 3)
            pg.draw.line(screen, GRAPH_GRID_COLOR, (x, yy), (x + w, yy))

        best_points = []
        avg_points = []
        n = len(self._records)
        for i, rec in enumerate(self._records):
            px = x + int(w * i / max(1, n - 1))
            py_best = y + h - int((rec.best - min_value) / value_range * h)
            py_avg = y + h - int((rec.avg - min_value) / value_range * h)
            best_points.append((px, py_best))
            avg_points.append((px, py_avg))

        if len(best_points) >= 2:
            pg.draw.lines(screen, GRAPH_LINE_BEST, False, best_points, width=2)
        if len(avg_points) >= 2:
            pg.draw.lines(screen, GRAPH_LINE_AVG, False, avg_points, width=2)

        latest = self._records[-1]
        self._blit_label(
            screen,
            f"Gen {latest.generation}  best={latest.best:.1f}  avg={latest.avg:.1f}",
            (x + 4, y + 4),
        )

    def _blit_label(
        self,
        screen: pg.Surface,
        text: str,
        pos: tuple[int, int],
    ) -> None:
        surface = self._font.render(text, True, COLOR_TEXT)
        screen.blit(surface, pos)
