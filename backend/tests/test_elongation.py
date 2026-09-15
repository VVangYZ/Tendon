"""预应力伸长量计算内核的基础算例。"""

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
