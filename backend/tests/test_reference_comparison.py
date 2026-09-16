"""新内核与参考脚本的回归对比算例。"""

import math
import sys
import unittest
from pathlib import Path

from app.calculations import (
    Arc,
    FrictionParameters,
    Line,
    MaterialParameters,
    Profile,
    TendonElongationCalculator,
    TendonGeometry,
    TensioningCase,
)


# 允许测试直接加载保留在项目根目录 ref 下的参考实现。
REFERENCE_DIRECTORY = Path(__file__).resolve().parents[2] / "ref"
if REFERENCE_DIRECTORY.is_dir():
    sys.path.insert(0, str(REFERENCE_DIRECTORY))
    from tendon_new6_CanCutArc import Tendon, TendonCL2D  # noqa: E402
else:
    Tendon = TendonCL2D = None


def profile_from_xyr(points):
    """按参考脚本相同的圆弧切点规则，将控制点和半径转为新内核线形。"""
    segments = []
    previous_end = (points[0][0], points[0][1])
    for index in range(1, len(points) - 1):
        previous = points[index - 1]
        current = points[index]
        following = points[index + 1]
        radius = current[2]
        if radius <= 0:
            raise ValueError("中间控制点半径必须大于零")

        vector_before = (current[0] - previous[0], current[1] - previous[1])
        vector_after = (following[0] - current[0], following[1] - current[1])
        length_before = math.hypot(*vector_before)
        length_after = math.hypot(*vector_after)
        unit_before = (vector_before[0] / length_before, vector_before[1] / length_before)
        unit_after = (vector_after[0] / length_after, vector_after[1] / length_after)
        angle = math.acos(unit_before[0] * unit_after[0] + unit_before[1] * unit_after[1])
        cut = radius * math.tan(angle / 2)
        arc_start = (current[0] - unit_before[0] * cut, current[1] - unit_before[1] * cut)
        arc_end = (current[0] + unit_after[0] * cut, current[1] + unit_after[1] * cut)
        direction = 1 if unit_after[1] > unit_before[1] else -1

        segments.append(Line(previous_end, arc_start))
        segments.append(Arc(arc_start, arc_end, math.tan(angle * direction / 4)))
        previous_end = arc_end

    segments.append(Line(previous_end, (points[-1][0], points[-1][1])))
    return Profile(segments)


ELEVATION_POINTS = [
    (0.0, 0.0, 0.0),
    (5.191, -1.294, 10.0),
    (27.647, -1.294, 10.0),
    (32.273, -0.141, 10.0),
    (42.729, -0.141, 10.0),
    (47.355, -1.294, 10.0),
    (69.811, -1.294, 10.0),
    (75.0, 0.0, 0.0),
]
PLAN_POINTS = [
    (0.0, 0.0, 0.0),
    (37.5, 3.4613, 407.99),
    (75.0, 0.0, 0.0),
]


def calculate_reference_case():
    """运行参考脚本中的组合曲线算例。"""
    if Tendon is None or TendonCL2D is None:
        raise RuntimeError("未找到 ref 目录中的参考脚本")
    elevation = TendonCL2D.from_xyr_lst(ELEVATION_POINTS)
    plan = TendonCL2D.from_xyr_lst(PLAN_POINTS)
    reference = Tendon(elevation, plan, k=0.0015, mu=0.25, tendon_e=190000.0)
    stresses = reference.get_ctrl_pts_pp()
    segments = reference.get_segments_dl(stresses)
    return reference.length, reference.get_end_dl(stresses, segments)


def calculate_current_case():
    """运行与参考算例参数一致的新内核计算。"""
    geometry = TendonGeometry(
        elevation=profile_from_xyr(ELEVATION_POINTS),
        plan=profile_from_xyr(PLAN_POINTS),
    )
    return TendonElongationCalculator(
        geometry=geometry,
        friction=FrictionParameters(k=0.0015, mu=0.25),
        material=MaterialParameters(elastic_modulus=190000.0),
    ).calculate(TensioningCase(left_stress=1395.0, right_stress=1395.0))


class ReferenceComparisonTest(unittest.TestCase):
    def test_combined_vertical_and_plan_curves(self) -> None:
        """参考脚本注释中的组合曲线算例，应与新内核结果接近。"""
        if Tendon is None or TendonCL2D is None:
            self.skipTest("未找到 ref 目录中的参考脚本")
        reference_length, (reference_left, reference_right, reference_total) = calculate_reference_case()
        current = calculate_current_case()

        # 两种实现的空间几何离散方式不同，因此以工程计算可接受的相对差比较。
        self.assertAlmostEqual(current.total_length, reference_length, delta=0.02)
        self.assertAlmostEqual(current.total_elongation, reference_total, delta=0.0002)
        self.assertAlmostEqual(current.left_elongation, reference_left, delta=0.0002)
        self.assertAlmostEqual(current.right_elongation, reference_right, delta=0.0002)
