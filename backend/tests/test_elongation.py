"""预应力伸长量计算内核的基础算例。"""

import math
import unittest

from app.calculations import (
    FrictionParameters,
    Line,
    MaterialParameters,
    Profile,
    TendonElongationCalculator,
    TendonGeometry,
    TensioningCase,
)


def create_straight_geometry(length: float) -> TendonGeometry:
    """创建平面和立面均为直线的水平钢束。"""
    elevation = Profile([Line((0.0, 0.0), (length, 0.0))])
    plan = Profile([Line((0.0, 0.0), (length, 0.0))])
    return TendonGeometry(elevation=elevation, plan=plan)


class TendonElongationCalculatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.material = MaterialParameters(elastic_modulus=200000.0)
        self.no_friction = FrictionParameters(k=0.0, mu=0.0)

    def test_single_end_straight_tendon(self) -> None:
        """无摩阻时，单端直线束伸长量应等于 σL/E。"""
        calculator = TendonElongationCalculator(
            geometry=create_straight_geometry(10.0),
            friction=self.no_friction,
            material=self.material,
        )

        result = calculator.calculate(TensioningCase(left_stress=1000.0))

        self.assertAlmostEqual(result.total_length, 10.0, places=10)
        self.assertAlmostEqual(result.total_turn, 0.0, places=10)
        self.assertAlmostEqual(result.left_elongation, 0.05, places=10)
        self.assertAlmostEqual(result.right_elongation, 0.0, places=10)
        self.assertAlmostEqual(result.total_elongation, 0.05, places=10)

    def test_symmetric_double_end_straight_tendon(self) -> None:
        """无摩阻、两端等应力时，两端各承担半束伸长量。"""
        calculator = TendonElongationCalculator(
            geometry=create_straight_geometry(20.0),
            friction=self.no_friction,
            material=self.material,
        )

        result = calculator.calculate(TensioningCase(left_stress=1200.0, right_stress=1200.0))

        self.assertAlmostEqual(result.balance_x, 10.0, places=10)
        self.assertAlmostEqual(result.left_elongation, 0.06, places=10)
        self.assertAlmostEqual(result.right_elongation, 0.06, places=10)
        self.assertAlmostEqual(result.total_elongation, 0.12, places=10)

    def test_xyr_and_xyb_inputs_create_matching_profiles(self) -> None:
        """角点半径和 CAD bulge 输入应生成相同的圆弧线形。"""
        radius = 5.0
        turn_angle = math.pi / 4
        cut_length = radius * math.tan(turn_angle / 2)
        xyr_profile = Profile.from_xyr_points([
            (0.0, 0.0, 0.0),
            (10.0, 0.0, radius),
            (20.0, 10.0, 0.0),
        ])
        xyb_profile = Profile.from_xyb_points([
            (0.0, 0.0, 0.0),
            (10.0 - cut_length, 0.0, math.tan(turn_angle / 4)),
            (10.0 + cut_length / math.sqrt(2), cut_length / math.sqrt(2), 0.0),
            (20.0, 10.0, 0.0),
        ])

        self.assertAlmostEqual(xyr_profile.x_start, xyb_profile.x_start, places=10)
        self.assertAlmostEqual(xyr_profile.x_end, xyb_profile.x_end, places=10)
        self.assertAlmostEqual(xyr_profile.point_at(10.0)[1], xyb_profile.point_at(10.0)[1], places=10)
