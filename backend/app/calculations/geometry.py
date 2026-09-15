"""钢束空间线形及几何计算。"""

from __future__ import annotations

from dataclasses import dataclass
from math import acos, atan2, ceil, cos, exp, hypot, pi, sin, sqrt, tan
from typing import List, Sequence, Tuple, Union


Point2D = Tuple[float, float]


class GeometryError(ValueError):
    """线形输入不满足计算条件时抛出的异常。"""


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _unit(vector: Sequence[float]) -> Tuple[float, ...]:
    length = sqrt(sum(component * component for component in vector))
    if length == 0:
        raise GeometryError("切向量长度不能为零")
    return tuple(component / length for component in vector)


def _simpson(function, left: float, right: float, subdivisions: int = 64) -> float:
    """采用复合辛普森公式进行数值积分。"""
    if right == left:
        return 0.0
    subdivisions = max(2, subdivisions + subdivisions % 2)
    step = (right - left) / subdivisions
    value = function(left) + function(right)
    for index in range(1, subdivisions):
        weight = 4 if index % 2 else 2
        value += weight * function(left + index * step)
    return value * step / 3


@dataclass(frozen=True)
class Line:
    """以共同里程 x 参数化的二维直线段。"""

    start: Point2D
    end: Point2D

    def __post_init__(self) -> None:
        if self.end[0] <= self.start[0]:
            raise GeometryError("线段终点里程必须大于起点里程")

    @property
    def x_start(self) -> float:
        return self.start[0]

    @property
    def x_end(self) -> float:
        return self.end[0]

    def point_at(self, x: float) -> Point2D:
        if not self.x_start <= x <= self.x_end:
            raise GeometryError("查询里程超出直线段范围")
        ratio = (x - self.x_start) / (self.x_end - self.x_start)
        return (x, self.start[1] + ratio * (self.end[1] - self.start[1]))

    def tangent_at(self, x: float) -> Point2D:
        self.point_at(x)
        return _unit((self.end[0] - self.start[0], self.end[1] - self.start[1]))  # type: ignore[return-value]


@dataclass(frozen=True)
class Arc:
    """以 CAD bulge 表示的二维圆弧段，要求 x 沿圆弧单调增加。"""

    start: Point2D
    end: Point2D
    bulge: float

    def __post_init__(self) -> None:
        if self.bulge == 0:
            raise GeometryError("圆弧 bulge 不能为零，请使用 Line")
        if self.end[0] <= self.start[0]:
            raise GeometryError("圆弧终点里程必须大于起点里程")
        previous_x = self._point_by_ratio(0.0)[0]
        for index in range(1, 65):
            current_x = self._point_by_ratio(index / 64)[0]
            if current_x <= previous_x:
                raise GeometryError("圆弧在 x 方向不单调，不能作为共同里程线形")
            previous_x = current_x

    @property
    def x_start(self) -> float:
        return self.start[0]

    @property
    def x_end(self) -> float:
        return self.end[0]

    @property
    def _sweep(self) -> float:
        return 4 * atan2(self.bulge, 1.0)

    @property
    def _center(self) -> Point2D:
        chord_x = self.end[0] - self.start[0]
        chord_y = self.end[1] - self.start[1]
        chord = hypot(chord_x, chord_y)
        factor = chord * (1 - self.bulge * self.bulge) / (4 * self.bulge)
        return (
            (self.start[0] + self.end[0]) / 2 - chord_y * factor / chord,
            (self.start[1] + self.end[1]) / 2 + chord_x * factor / chord,
        )

    @property
    def _radius(self) -> float:
        chord = hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])
        return chord * (1 + self.bulge * self.bulge) / (4 * abs(self.bulge))

    def _point_by_ratio(self, ratio: float) -> Point2D:
        center_x, center_y = self._center
        start_angle = atan2(self.start[1] - center_y, self.start[0] - center_x)
        angle = start_angle + self._sweep * ratio
        return (center_x + self._radius * cos(angle), center_y + self._radius * sin(angle))

    def _ratio_at(self, x: float) -> float:
        if not self.x_start <= x <= self.x_end:
            raise GeometryError("查询里程超出圆弧段范围")
        left, right = 0.0, 1.0
        for _ in range(60):
            middle = (left + right) / 2
            if self._point_by_ratio(middle)[0] < x:
                left = middle
            else:
                right = middle
        return (left + right) / 2

    def point_at(self, x: float) -> Point2D:
        if x == self.x_start:
            return self.start
        if x == self.x_end:
            return self.end
        return self._point_by_ratio(self._ratio_at(x))

    def tangent_at(self, x: float) -> Point2D:
        ratio = self._ratio_at(x)
        center_x, center_y = self._center
        point_x, point_y = self._point_by_ratio(ratio)
        direction = 1.0 if self._sweep > 0 else -1.0
        return _unit((-(point_y - center_y) * direction, (point_x - center_x) * direction))  # type: ignore[return-value]


Segment = Union[Line, Arc]


class Profile:
    """由直线和圆弧组成的立面或平面线形。"""

    def __init__(self, segments: Sequence[Segment]) -> None:
        if not segments:
            raise GeometryError("线形至少需要一个分段")
        self.segments = tuple(segments)
        for previous, current in zip(self.segments, self.segments[1:]):
            if abs(previous.x_end - current.x_start) > 1e-8:
                raise GeometryError("相邻分段里程不连续")
            if hypot(previous.end[0] - current.start[0], previous.end[1] - current.start[1]) > 1e-8:
                raise GeometryError("相邻分段坐标不连续")

    @property
    def x_start(self) -> float:
        return self.segments[0].x_start

    @property
    def x_end(self) -> float:
        return self.segments[-1].x_end

    def _segment_at(self, x: float) -> Segment:
        if not self.x_start <= x <= self.x_end:
            raise GeometryError("查询里程超出线形范围")
        for segment in self.segments:
            if segment.x_start <= x < segment.x_end:
                return segment
        return self.segments[-1]

    def point_at(self, x: float) -> Point2D:
        return self._segment_at(x).point_at(x)

    def tangent_at(self, x: float) -> Point2D:
        return self._segment_at(x).tangent_at(x)

    def breakpoints_between(self, x1: float, x2: float) -> List[float]:
        if not self.x_start <= x1 <= x2 <= self.x_end:
            raise GeometryError("截取里程超出线形范围")
        return [x1] + [segment.x_end for segment in self.segments[:-1] if x1 < segment.x_end < x2] + [x2]


class TendonGeometry:
    """由平面和立面共同定义的空间钢束线形。"""

    def __init__(self, elevation: Profile, plan: Profile) -> None:
        if abs(elevation.x_start - plan.x_start) > 1e-8 or abs(elevation.x_end - plan.x_end) > 1e-8:
            raise GeometryError("立面与平面线形的起终里程必须一致")
        self.elevation = elevation
        self.plan = plan

    @property
    def x_start(self) -> float:
        return self.elevation.x_start

    @property
    def x_end(self) -> float:
        return self.elevation.x_end

    def tangent_at(self, x: float) -> Tuple[float, float, float]:
        """返回空间单位切向量，坐标顺序为 x、平面偏移、立面高程。"""
        plan_tangent = self.plan.tangent_at(x)
        elevation_tangent = self.elevation.tangent_at(x)
        plan_slope = plan_tangent[1] / plan_tangent[0]
        elevation_slope = elevation_tangent[1] / elevation_tangent[0]
        return _unit((1.0, plan_slope, elevation_slope))  # type: ignore[return-value]

    def breakpoints_between(self, x1: float, x2: float) -> List[float]:
        points = set(self.elevation.breakpoints_between(x1, x2) + self.plan.breakpoints_between(x1, x2))
        return sorted(points)

    def length_between(self, x1: float, x2: float) -> float:
        """计算两里程之间的空间钢束长度，单位与输入里程一致。"""
        def metric(x: float) -> float:
            tangent = self.tangent_at(x)
            return 1 / tangent[0]

        points = self.breakpoints_between(x1, x2)
        return sum(_simpson(metric, left, right) for left, right in zip(points, points[1:]))

    def turn_between(self, x1: float, x2: float, samples_per_interval: int = 64) -> float:
        """通过空间切向量离散累计绝对转角，返回弧度。"""
        if x2 < x1:
            raise GeometryError("终止里程不能小于起始里程")
        total_turn = 0.0
        points = self.breakpoints_between(x1, x2)
        for left, right in zip(points, points[1:]):
            previous = self.tangent_at(left)
            for index in range(1, samples_per_interval + 1):
                current_x = left + (right - left) * index / samples_per_interval
                current = self.tangent_at(current_x)
                cosine = _clamp(sum(a * b for a, b in zip(previous, current)), -1.0, 1.0)
                total_turn += acos(cosine)
                previous = current
        return total_turn
