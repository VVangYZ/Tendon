"""预应力钢束摩阻损失和理论伸长量计算。"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import List, Optional, Tuple

from .geometry import GeometryError, TendonGeometry, _simpson


@dataclass(frozen=True)
class FrictionParameters:
    """孔道摩阻参数，其中 k 的单位为 1/长度，μ 无量纲。"""

    k: float
    mu: float

    def __post_init__(self) -> None:
        if self.k < 0 or self.mu < 0:
            raise ValueError("孔道偏差系数 k 和摩阻系数 μ 均不能为负")


@dataclass(frozen=True)
class MaterialParameters:
    """钢束材料参数；应力和弹性模量应采用相同单位，例如 MPa。"""

    elastic_modulus: float

    def __post_init__(self) -> None:
        if self.elastic_modulus <= 0:
            raise ValueError("钢束弹性模量必须大于零")


@dataclass(frozen=True)
class TensioningCase:
    """张拉工况。仅填写一端为单端张拉，同时填写两端为双端同步张拉。"""

    left_stress: Optional[float] = None
    right_stress: Optional[float] = None

    def __post_init__(self) -> None:
        if self.left_stress is None and self.right_stress is None:
            raise ValueError("至少需要提供一个张拉端应力")
        for stress in (self.left_stress, self.right_stress):
            if stress is not None and stress <= 0:
                raise ValueError("张拉端应力必须大于零")

    @property
    def is_double_ended(self) -> bool:
        return self.left_stress is not None and self.right_stress is not None


@dataclass(frozen=True)
class SegmentResult:
    """计算书可直接使用的分段结果。"""

    x_start: float
    x_end: float
    length: float
    turn: float
    average_stress: float
    elongation: float
    source: str


@dataclass(frozen=True)
class CalculationResult:
    """理论伸长量计算成果，伸长量单位与输入长度一致。"""

    total_length: float
    total_turn: float
    total_elongation: float
    left_elongation: float
    right_elongation: float
    balance_x: Optional[float]
    segments: Tuple[SegmentResult, ...]


class TendonElongationCalculator:
    """计算即时理论伸长量，不包含锚具回缩、弹性压缩和时变损失。"""

    def __init__(self, geometry: TendonGeometry, friction: FrictionParameters, material: MaterialParameters) -> None:
        self.geometry = geometry
        self.friction = friction
        self.material = material

    def stress_from_left(self, x: float, stress: float) -> float:
        length = self.geometry.length_between(self.geometry.x_start, x)
        turn = self.geometry.turn_between(self.geometry.x_start, x)
        return stress * exp(-(self.friction.k * length + self.friction.mu * turn))

    def stress_from_right(self, x: float, stress: float) -> float:
        length = self.geometry.length_between(x, self.geometry.x_end)
        turn = self.geometry.turn_between(x, self.geometry.x_end)
        return stress * exp(-(self.friction.k * length + self.friction.mu * turn))

    def _balance_x(self, case: TensioningCase) -> Optional[float]:
        if not case.is_double_ended:
            return None
        assert case.left_stress is not None and case.right_stress is not None
        left, right = self.geometry.x_start, self.geometry.x_end

        def difference(x: float) -> float:
            return self.stress_from_left(x, case.left_stress) - self.stress_from_right(x, case.right_stress)

        start_difference, end_difference = difference(left), difference(right)
        if abs(start_difference) < 1e-10 and abs(end_difference) < 1e-10:
            return (left + right) / 2
        if start_difference * end_difference > 0:
            return None
        for _ in range(80):
            middle = (left + right) / 2
            if difference(left) * difference(middle) <= 0:
                right = middle
            else:
                left = middle
        return (left + right) / 2

    def _elongation_from(self, x1: float, x2: float, source: str, stress: float) -> float:
        def integrand(x: float) -> float:
            unit_tangent = self.geometry.tangent_at(x)
            length_per_x = 1 / unit_tangent[0]
            if source == "left":
                current_stress = self.stress_from_left(x, stress)
            else:
                current_stress = self.stress_from_right(x, stress)
            return current_stress / self.material.elastic_modulus * length_per_x

        points = self.geometry.breakpoints_between(x1, x2)
        return sum(_simpson(integrand, left, right) for left, right in zip(points, points[1:]))

    def calculate(self, case: TensioningCase) -> CalculationResult:
        """计算理论伸长量，并返回可导出至计算书的分段成果。"""
        balance_x = self._balance_x(case)
        x_start, x_end = self.geometry.x_start, self.geometry.x_end
        ranges: List[Tuple[float, float, str, float]] = []

        if case.left_stress is not None and case.right_stress is None:
            ranges.append((x_start, x_end, "left", case.left_stress))
        elif case.right_stress is not None and case.left_stress is None:
            ranges.append((x_start, x_end, "right", case.right_stress))
        elif balance_x is not None:
            assert case.left_stress is not None and case.right_stress is not None
            ranges.extend(((x_start, balance_x, "left", case.left_stress), (balance_x, x_end, "right", case.right_stress)))
        else:
            assert case.left_stress is not None and case.right_stress is not None
            middle = (x_start + x_end) / 2
            if self.stress_from_left(middle, case.left_stress) >= self.stress_from_right(middle, case.right_stress):
                ranges.append((x_start, x_end, "left", case.left_stress))
            else:
                ranges.append((x_start, x_end, "right", case.right_stress))

        segments: List[SegmentResult] = []
        left_elongation = 0.0
        right_elongation = 0.0
        for range_start, range_end, source, stress in ranges:
            points = self.geometry.breakpoints_between(range_start, range_end)
            for segment_start, segment_end in zip(points, points[1:]):
                elongation = self._elongation_from(segment_start, segment_end, source, stress)
                length = self.geometry.length_between(segment_start, segment_end)
                segments.append(SegmentResult(
                    x_start=segment_start,
                    x_end=segment_end,
                    length=length,
                    turn=self.geometry.turn_between(segment_start, segment_end),
                    average_stress=elongation * self.material.elastic_modulus / length,
                    elongation=elongation,
                    source=source,
                ))
                if source == "left":
                    left_elongation += elongation
                else:
                    right_elongation += elongation

        return CalculationResult(
            total_length=self.geometry.length_between(x_start, x_end),
            total_turn=self.geometry.turn_between(x_start, x_end),
            total_elongation=left_elongation + right_elongation,
            left_elongation=left_elongation,
            right_elongation=right_elongation,
            balance_x=balance_x,
            segments=tuple(segments),
        )
