"""网页 API 的输入与输出数据模型。"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProfilePointInput(BaseModel):
    """线形表格的一行数据，value 对应半径 r 或 bulge b。"""

    x: float
    y: float
    value: float = 0.0


class ProfileInput(BaseModel):
    """立面或平面线形的输入。"""

    mode: Literal["xyr", "xyb"] = "xyr"
    points: list[ProfilePointInput] = Field(min_length=2)


class ImportedProfileOutput(BaseModel):
    """DXF 导入的一条 x/y/b 线形。"""

    mode: Literal["xyb"] = "xyb"
    points: list[ProfilePointInput]


class DxfImportResponse(BaseModel):
    """DXF 文件导入后返回的平面与立面线形。"""

    elevation: ImportedProfileOutput
    plan: ImportedProfileOutput
    unit: Literal["m", "mm"]


class CalculationRequest(BaseModel):
    """单根钢束计算请求。"""

    elevation: ProfileInput
    plan: ProfileInput
    k: float = Field(default=0.0015, ge=0)
    mu: float = Field(default=0.25, ge=0)
    elastic_modulus: float = Field(default=195000.0, gt=0)
    left_stress: Optional[float] = Field(default=1395.0, ge=0)
    right_stress: Optional[float] = Field(default=1395.0, ge=0)


class DistributionPoint(BaseModel):
    """四联图在一个里程处需要展示的数据。"""

    x: float
    plan_y: float
    elevation_y: float
    stress: float
    elongation_mm: float


class SegmentOutput(BaseModel):
    """计算明细中的一段钢束。"""

    x_start: float
    x_end: float
    length: float
    turn: float
    average_stress: float
    elongation_mm: float
    source: str


class CalculationResponse(BaseModel):
    """网页计算结果。"""

    total_length: float
    total_turn: float
    total_elongation_mm: float
    left_elongation_mm: float
    right_elongation_mm: float
    balance_x: Optional[float]
    distribution: list[DistributionPoint]
    segments: list[SegmentOutput]


class NamedProfile(BaseModel):
    """供多根钢束复用的一条 x/y/b 线形。"""

    id: str
    points: list[ProfilePointInput] = Field(min_length=2)


class BatchDefaults(BaseModel):
    """批量导入工作簿提供的统一默认参数。"""

    unit: Literal["m", "mm"] = "m"
    k: float = Field(default=0.0015, ge=0)
    mu: float = Field(default=0.25, ge=0)
    elastic_modulus: float = Field(default=195000.0, gt=0)
    left_stress: float = Field(default=1395.0, ge=0)
    right_stress: float = Field(default=1395.0, ge=0)


class BatchTendon(BaseModel):
    """一根批量钢束的引用、解析参数与校核结果。"""

    id: str
    elevation_id: str
    plan_id: str
    left_stress: float = Field(ge=0)
    right_stress: float = Field(ge=0)
    k: float = Field(ge=0)
    mu: float = Field(ge=0)
    elastic_modulus: float = Field(gt=0)
    elevation: Optional[ProfileInput] = None
    plan: Optional[ProfileInput] = None
    status: Literal["ready", "invalid"] = "ready"
    error: Optional[str] = None


class BatchProject(BaseModel):
    """Excel 导入后保留在前端会话中的批量工程数据。"""

    defaults: BatchDefaults
    elevation_profiles: list[NamedProfile] = []
    plan_profiles: list[NamedProfile] = []
    tendons: list[BatchTendon]


class BatchImportResponse(BaseModel):
    """批量 Excel 导入及逐束校核结果。"""

    project: BatchProject
    ready_count: int
    invalid_count: int


class BatchCalculationItem(BaseModel):
    """一根钢束的批量计算状态与结果。"""

    id: str
    status: Literal["success", "failed", "skipped"]
    error: Optional[str] = None
    result: Optional[CalculationResponse] = None


class BatchCalculationRequest(BaseModel):
    """请求对已导入项目执行批量计算。"""

    project: BatchProject


class BatchCalculationResponse(BaseModel):
    """批量计算的逐束结果。"""

    items: list[BatchCalculationItem]
    success_count: int
    failed_count: int


class BatchExportRequest(BaseModel):
    """将导入数据与计算结果导出为新的工作簿。"""

    project: BatchProject
    calculation: BatchCalculationResponse
