"""新内核与参考脚本的回归对比算例。"""

import sys
import unittest
from pathlib import Path

from app.calculations import (
    FrictionParameters,
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


def calculate_reference_case(
    left_stress=1395.0,
    right_stress=1395.0,
    elevation_points=ELEVATION_POINTS,
    plan_points=PLAN_POINTS,
):
    """运行参考脚本中的组合曲线算例。"""
    if Tendon is None or TendonCL2D is None:
        raise RuntimeError("未找到 ref 目录中的参考脚本")
    elevation = TendonCL2D.from_xyr_lst(elevation_points)
    plan = TendonCL2D.from_xyr_lst(plan_points)
    reference = Tendon(
        elevation,
        plan,
        k=0.0015,
        mu=0.25,
        p_start=left_stress,
        p_end=right_stress,
        tendon_e=190000.0,
    )
    stresses = reference.get_ctrl_pts_pp()
    segments = reference.get_segments_dl(stresses)
    return reference.length, reference.zero_pt, reference.get_end_dl(stresses, segments)


def calculate_current_case(
    left_stress=1395.0,
    right_stress=1395.0,
    elevation_points=ELEVATION_POINTS,
    plan_points=PLAN_POINTS,
):
    """运行与参考算例参数一致的新内核计算。"""
    geometry = TendonGeometry(
        elevation=Profile.from_xyr_points(elevation_points),
        plan=Profile.from_xyr_points(plan_points),
    )
    return TendonElongationCalculator(
        geometry=geometry,
        friction=FrictionParameters(k=0.0015, mu=0.25),
        material=MaterialParameters(elastic_modulus=190000.0),
    ).calculate(TensioningCase(left_stress=left_stress, right_stress=right_stress))


class ReferenceComparisonTest(unittest.TestCase):
    def test_combined_vertical_and_plan_curves(self) -> None:
        """参考脚本注释中的组合曲线算例，应与新内核结果接近。"""
        if Tendon is None or TendonCL2D is None:
            self.skipTest("未找到 ref 目录中的参考脚本")
        reference_length, _, (reference_left, reference_right, reference_total) = calculate_reference_case()
        current = calculate_current_case()

        # 两种实现的空间几何离散方式不同，因此以工程计算可接受的相对差比较。
        self.assertAlmostEqual(current.total_length, reference_length, delta=0.02)
        self.assertAlmostEqual(current.total_elongation, reference_total, delta=0.0002)
        self.assertAlmostEqual(current.left_elongation, reference_left, delta=0.0002)
        self.assertAlmostEqual(current.right_elongation, reference_right, delta=0.0002)

    def test_asymmetric_geometry_balance_point(self) -> None:
        """线形不对称、两端等应力时，新内核应得到一致的不动点和伸长量。"""
        if Tendon is None or TendonCL2D is None:
            self.skipTest("未找到 ref 目录中的参考脚本")

        # 平面转弯点位于跨中左侧，使两侧孔道长度和累计转角不同。
        asymmetric_plan_points = [
            (0.0, 0.0, 0.0),
            (25.0, 3.4613, 100.0),
            (75.0, 0.0, 0.0),
        ]
        reference_length, reference_balance_x, (reference_left, reference_right, reference_total) = calculate_reference_case(
            plan_points=asymmetric_plan_points,
        )
        current = calculate_current_case(
            plan_points=asymmetric_plan_points,
        )

        self.assertIsNotNone(reference_balance_x)
        self.assertIsNotNone(current.balance_x)
        self.assertGreater(abs(current.balance_x - 37.5), 1.0)
        self.assertAlmostEqual(current.total_length, reference_length, delta=0.02)
        self.assertAlmostEqual(current.balance_x, reference_balance_x, delta=0.02)
        self.assertAlmostEqual(current.total_elongation, reference_total, delta=0.0002)
        self.assertAlmostEqual(current.left_elongation, reference_left, delta=0.0002)
        self.assertAlmostEqual(current.right_elongation, reference_right, delta=0.0002)
