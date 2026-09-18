"""DXF 线形导入 HTTP 接口。"""

from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.models.schemas import DxfImportResponse, ImportedProfileOutput, ProfilePointInput
from app.services.dxf_import import DxfImportError, import_dxf_profiles


router = APIRouter(prefix="/api", tags=["DXF 导入"])


@router.post("/import/dxf", response_model=DxfImportResponse)
async def import_dxf(
    file: UploadFile = File(...),
    unit: Literal["m", "mm"] = Query(default="m"),
) -> DxfImportResponse:
    """导入固定图层“平面”和“立面”的钢束多段线。"""
    if not file.filename or not file.filename.lower().endswith(".dxf"):
        raise HTTPException(status_code=422, detail="仅支持 .dxf 文件")
    try:
        result = import_dxf_profiles(await file.read(), unit)
    except DxfImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await file.close()

    return DxfImportResponse(
        elevation=ImportedProfileOutput(points=[ProfilePointInput(x=x, y=y, value=bulge) for x, y, bulge in result.elevation.points]),
        plan=ImportedProfileOutput(points=[ProfilePointInput(x=x, y=y, value=bulge) for x, y, bulge in result.plan.points]),
        unit=unit,
    )
