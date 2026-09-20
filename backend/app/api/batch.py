"""多根钢束 Excel 导入、批量计算与导出接口。"""

from typing import Literal

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.models.schemas import BatchCalculationRequest, BatchExportRequest, BatchImportResponse
from app.services.batch_excel import BatchExcelError, calculate_project, create_template, export_project, import_project
from app.services.batch_dxf import BatchDxfImportError, import_batch_dxf
from app.api.uploads import read_limited_upload


router = APIRouter(prefix="/api/batch", tags=["批量计算"])


@router.get("/template")
def download_template() -> StreamingResponse:
    """下载固定格式的多根钢束 Excel 模板。"""
    return StreamingResponse(iter([create_template()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=tendon_batch_template.xlsx"})


@router.post("/import", response_model=BatchImportResponse)
async def import_excel(file: UploadFile = File(...)) -> BatchImportResponse:
    """导入固定格式的 .xlsx 工作簿。"""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 文件")
    try:
        project = import_project(await read_limited_upload(file))
    except BatchExcelError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await file.close()
    ready_count = sum(tendon.status == "ready" for tendon in project.tendons)
    return BatchImportResponse(project=project, ready_count=ready_count, invalid_count=len(project.tendons) - ready_count)


@router.post("/import/dxf", response_model=BatchImportResponse)
async def import_dxf(
    file: UploadFile = File(...),
    unit: Literal["m", "mm"] = Query(default="m"),
    label_tolerance: float = Query(default=0.05, gt=0),
) -> BatchImportResponse:
    """按固定图层和左端编号文字导入多根钢束。"""
    if not file.filename or not file.filename.lower().endswith(".dxf"):
        raise HTTPException(status_code=422, detail="仅支持 .dxf 文件")
    try:
        project = import_batch_dxf(await read_limited_upload(file), unit, label_tolerance)
    except BatchDxfImportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        await file.close()
    return BatchImportResponse(project=project, ready_count=len(project.tendons), invalid_count=0)


@router.post("/calculate")
def calculate_batch(request: BatchCalculationRequest):
    """计算导入工程中全部通过校核的钢束。"""
    return calculate_project(request.project)


@router.post("/export")
def export_excel(request: BatchExportRequest) -> StreamingResponse:
    """导出批量计算成果工作簿。"""
    content = export_project(request.project, request.calculation)
    return StreamingResponse(iter([content]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=tendon_batch_results.xlsx"})
