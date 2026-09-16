"""预应力钢束摩阻损失和理论伸长量计算。"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from math import exp
from typing import List, Optional, Tuple

from .geometry import TendonGeometry


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


@dataclass(frozen=True)
class _PathNode:
    """路径离散点：保存从左端累计的长度和角变位。"""

    x: float
    length: float
    turn: float


class TendonElongationCalculator:
    """计算即时理论伸长量，不包含锚具回缩、弹性压缩和时变损失。"""

    def __init__(self, geometry: TendonGeometry, friction: FrictionParameters, material: MaterialParameters) -> None:
        self.geometry = geometry
        self.friction = friction
        self.material = material
        # 每个原始几何分段划分为 4 个小段；该路径表供后续全部应力和伸长量查询复用。
        self._path_nodes = self._build_path_nodes(subdivisions_per_interval=4)
        self._path_xs = tuple(node.x for node in self._path_nodes)

    def _build_path_nodes(self, subdivisions_per_interval: int) -> Tuple[_PathNode, ...]:
        """预计算里程、累计长度和累计转角，避免伸长量积分中的嵌套几何积分。"""
        breakpoints = self.geometry.breakpoints_between(self.geometry.x_start, self.geometry.x_end)
        nodes = [_PathNode(x=breakpoints[0], length=0.0, turn=0.0)]
        accumulated_length = 0.0
        accumulated_turn = 0.0

        for left, right in zip(breakpoints, breakpoints[1:]):
            previous_x = left
            for index in range(1, subdivisions_per_interval + 1):
                current_x = left + (right - left) * index / subdivisions_per_interval
                accumulated_length += self.geometry.length_between(previous_x, current_x)
                accumulated_turn += self.geometry.turn_between(previous_x, current_x)
                nodes.append(_PathNode(current_x, accumulated_length, accumulated_turn))
                previous_x = current_x
        return tuple(nodes)

    def _path_at(self, x: float) -> Tuple[float, float]:
        """从路径表线性插值得到指定里程的累计长度和累计转角。"""
        first, last = self._path_nodes[0], self._path_nodes[-1]
        if x < first.x - 1e-9 or x > last.x + 1e-9:
            raise ValueError("查询里程超出钢束范围")
        if x <= first.x:
            return first.length, first.turn
        if x >= last.x:
            return last.length, last.turn

        right_index = bisect_right(self._path_xs, x)
        left_node = self._path_nodes[right_index - 1]
        right_node = self._path_nodes[right_index]
        ratio = (x - left_node.x) / (right_node.x - left_node.x)
        length = left_node.length + ratio * (right_node.length - left_node.length)
        turn = left_node.turn + ratio * (right_node.turn - left_node.turn)
        return length, turn

    def _sample_xs_between(self, x1: float, x2: float) -> Tuple[float, ...]:
        """返回区间端点及内部路径表节点，供分段积分复用。"""
        start_index = bisect_right(self._path_xs, x1)
        end_index = bisect_right(self._path_xs, x2)
        return (x1,) + self._path_xs[start_index:end_index] + (x2,)

    def stress_from_left(self, x: float, stress: float) -> float:
        length, turn = self._path_at(x)
        return stress * exp(-(self.friction.k * length + self.friction.mu * turn))

    def stress_from_right(self, x: float, stress: float) -> float:
        length_from_left, turn_from_left = self._path_at(x)
        length = self._path_nodes[-1].length - length_from_left
        turn = self._path_nodes[-1].turn - turn_from_left
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
        """沿缓存路径以辛普森公式积分应力应变，避免在积分点重复求几何量。"""
        elongation = 0.0
        points = self._sample_xs_between(x1, x2)
        for left, right in zip(points, points[1:]):
            left_length, _ = self._path_at(left)
            right_length, _ = self._path_at(right)
            delta_length = right_length - left_length
            middle = (left + right) / 2
            if source == "left":
                left_stress = self.stress_from_left(left, stress)
                middle_stress = self.stress_from_left(middle, stress)
                right_stress = self.stress_from_left(right, stress)
            else:
                left_stress = self.stress_from_right(left, stress)
                middle_stress = self.stress_from_right(middle, stress)
                right_stress = self.stress_from_right(right, stress)
            elongation += delta_length * (left_stress + 4 * middle_stress + right_stress) / (6 * self.material.elastic_modulus)
        return elongation

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
                start_length, start_turn = self._path_at(segment_start)
                end_length, end_turn = self._path_at(segment_end)
                length = end_length - start_length
                segments.append(SegmentResult(
                    x_start=segment_start,
                    x_end=segment_end,
                    length=length,
                    turn=end_turn - start_turn,
                    average_stress=elongation * self.material.elastic_modulus / length,
                    elongation=elongation,
                    source=source,
                ))
                if source == "left":
                    left_elongation += elongation
                else:
                    right_elongation += elongation

        return CalculationResult(
            total_length=self._path_nodes[-1].length,
            total_turn=self._path_nodes[-1].turn,
            total_elongation=left_elongation + right_elongation,
            left_elongation=left_elongation,
            right_elongation=right_elongation,
            balance_x=balance_x,
            segments=tuple(segments),
        )
