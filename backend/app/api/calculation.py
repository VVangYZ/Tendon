"""钢束计算 HTTP 接口。"""

from fastapi import APIRouter, HTTPException

from app.calculations import (
    FrictionParameters,
    MaterialParameters,
    Profile,
    TendonElongationCalculator,
    TendonGeometry,
    TensioningCase,
)
from app.calculations.geometry import GeometryError
from app.models.schemas import (
    CalculationRequest,
    CalculationResponse,
    DistributionPoint,
    SegmentOutput,
)


router = APIRouter(prefix="/api", tags=["计算"])


def _create_profile(data):
    """将网页表格数据转换为统一的线形对象。"""
    points = [(point.x, point.y, point.value) for point in data.points]
    if data.mode == "xyr":
        return Profile.from_xyr_points(points)
    return Profile.from_xyb_points(points)


@router.post("/calculate", response_model=CalculationResponse)
def calculate_tendon(request: CalculationRequest) -> CalculationResponse:
    """计算单根钢束，并返回结果卡、分段明细和四联图数据。"""
    try:
        geometry = TendonGeometry(
            elevation=_create_profile(request.elevation),
            plan=_create_profile(request.plan),
        )
        calculator = TendonElongationCalculator(
            geometry=geometry,
            friction=FrictionParameters(k=request.k, mu=request.mu),
            material=MaterialParameters(elastic_modulus=request.elastic_modulus),
        )
        # 网页中以 0 表示该端不参与张拉，转换为计算内核使用的 None。
        case = TensioningCase(
            left_stress=request.left_stress if request.left_stress not in (None, 0) else None,
            right_stress=request.right_stress if request.right_stress not in (None, 0) else None,
        )
        result = calculator.calculate(case)
        distribution = calculator.sample_distribution(case, result=result, count=121)
    except (GeometryError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return CalculationResponse(
        total_length=result.total_length,
        total_turn=result.total_turn,
        total_elongation_mm=result.total_elongation * 1000,
        left_elongation_mm=result.left_elongation * 1000,
        right_elongation_mm=result.right_elongation * 1000,
        balance_x=result.balance_x,
        distribution=[DistributionPoint(**point) for point in distribution],
        segments=[
            SegmentOutput(
                x_start=segment.x_start,
                x_end=segment.x_end,
                length=segment.length,
                turn=segment.turn,
                average_stress=segment.average_stress,
                elongation_mm=segment.elongation * 1000,
                source=segment.source,
            )
            for segment in result.segments
        ],
    )
