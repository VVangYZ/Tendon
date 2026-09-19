"""按编号文字关联多根钢束平立面线形的 DXF 导入服务。"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from app.models.schemas import BatchDefaults, BatchProject, BatchTendon, NamedProfile, ProfileInput, ProfilePointInput
from app.services.batch_excel import TOLERANCE_M, _resolve_profiles
from app.services.dxf_import import (
    DxfImportError,
    LAYER_ELEVATION,
    LAYER_PLAN,
    _extract_points,
    _normalize_direction,
    _read_document,
    _unit_scale,
)


LAYER_TENDON_ID = "钢束编号"
MAX_FILE_SIZE = 20 * 1024 * 1024


class BatchDxfImportError(ValueError):
    """批量 DXF 不符合图层和编号文字约定时抛出。"""


@dataclass(frozen=True)
class _LabeledProfile:
    """完成编号文字匹配的单条线形。"""

    tendon_id: str
    profile: ProfileInput


def import_batch_dxf(content: bytes, unit: str, label_tolerance_m: float = 0.05) -> BatchProject:
    """导入平面、立面多段线，并通过左端点编号文字配对。"""
    if not content:
        raise BatchDxfImportError("DXF 文件为空")
    if len(content) > MAX_FILE_SIZE:
        raise BatchDxfImportError("DXF 文件不得大于 20 MB")
    if label_tolerance_m <= 0:
        raise BatchDxfImportError("编号文字匹配容差必须大于 0")

    try:
        scale = _unit_scale(unit)
        document = _read_document(content)
    except DxfImportError as error:
        raise BatchDxfImportError(str(error)) from error

    modelspace = document.modelspace()
    labels = _read_labels(modelspace, scale)
    elevation = _read_labeled_profiles(modelspace, LAYER_ELEVATION, labels, scale, label_tolerance_m)
    plan = _read_labeled_profiles(modelspace, LAYER_PLAN, labels, scale, label_tolerance_m)
    elevations = _unique_profiles(elevation, LAYER_ELEVATION)
    plans = _unique_profiles(plan, LAYER_PLAN)
    _validate_label_coverage(labels, elevations, plans)

    tendons: list[BatchTendon] = []
    for tendon_id in sorted(elevations):
        try:
            elevation_profile, plan_profile = _resolve_profiles(tendon_id, tendon_id, elevations, plans)
        except ValueError as error:
            raise BatchDxfImportError(f"钢束“{tendon_id}”：{error}") from error
        tendons.append(BatchTendon(
            id=tendon_id,
            elevation_id=tendon_id,
            plan_id=tendon_id,
            left_stress=1395,
            right_stress=1395,
            k=0.0015,
            mu=0.25,
            elastic_modulus=195000,
            elevation=elevation_profile,
            plan=plan_profile,
        ))

    # 所有点已统一换算为米，后续计算和结果展示均使用米。
    return BatchProject(
        defaults=BatchDefaults(unit="m"),
        elevation_profiles=[NamedProfile(id=tendon_id, points=profile.points) for tendon_id, profile in elevations.items()],
        plan_profiles=[NamedProfile(id=tendon_id, points=profile.points) for tendon_id, profile in plans.items()],
        tendons=tendons,
    )


def _read_labels(modelspace, scale: float) -> dict[str, list[tuple[float, float]]]:
    """读取编号图层中的单行文字插入点。"""
    mtexts = [entity for entity in modelspace if entity.dxf.layer == LAYER_TENDON_ID and entity.dxftype() == "MTEXT"]
    if mtexts:
        raise BatchDxfImportError("图层“钢束编号”仅支持单行文字 TEXT，不支持 MTEXT")
    labels: dict[str, list[tuple[float, float]]] = {}
    for entity in modelspace:
        if entity.dxf.layer != LAYER_TENDON_ID or entity.dxftype() != "TEXT":
            continue
        tendon_id = str(entity.dxf.text).strip()
        if not tendon_id:
            raise BatchDxfImportError("图层“钢束编号”存在空白文字")
        # TEXT 的 insert 对左对齐文字是插入点，但右对齐等文字应以实际对齐点为准。
        _, alignment_point, _ = entity.get_placement()
        labels.setdefault(tendon_id, []).append((float(alignment_point.x) * scale, float(alignment_point.y) * scale))
    if not labels:
        raise BatchDxfImportError("图层“钢束编号”未找到单行文字 TEXT")
    return labels


def _read_labeled_profiles(modelspace, layer: str, labels: dict[str, list[tuple[float, float]]], scale: float, tolerance: float) -> list[_LabeledProfile]:
    """读取指定图层的全部开放二维多段线，并匹配其最左端编号文字。"""
    polylines = [entity for entity in modelspace if entity.dxf.layer == layer and entity.dxftype() in {"LWPOLYLINE", "POLYLINE"}]
    if not polylines:
        raise BatchDxfImportError(f"图层“{layer}”未找到多段线")
    profiles: list[_LabeledProfile] = []
    for index, polyline in enumerate(polylines, start=1):
        if polyline.dxftype() == "POLYLINE" and not polyline.is_2d_polyline:
            raise BatchDxfImportError(f"图层“{layer}”第 {index} 条多段线仅支持二维多段线")
        is_closed = polyline.closed if polyline.dxftype() == "LWPOLYLINE" else polyline.is_closed
        if is_closed:
            raise BatchDxfImportError(f"图层“{layer}”第 {index} 条多段线必须为非闭合线")
        try:
            points = _normalize_direction(_extract_points(polyline, scale), f"{layer}第{index}条")
        except DxfImportError as error:
            raise BatchDxfImportError(str(error)) from error
        tendon_id = _match_label(points[0][:2], labels, tolerance, layer, index)
        profiles.append(_LabeledProfile(tendon_id, ProfileInput(mode="xyb", points=[ProfilePointInput(x=x, y=y, value=bulge) for x, y, bulge in points])))
    return profiles


def _match_label(point: tuple[float, float], labels: dict[str, list[tuple[float, float]]], tolerance: float, layer: str, index: int) -> str:
    """要求一条线形左端点只匹配一个编号文字。"""
    matched = [tendon_id for tendon_id, inserts in labels.items() if any(hypot(point[0] - x, point[1] - y) <= tolerance for x, y in inserts)]
    if not matched:
        raise BatchDxfImportError(f"图层“{layer}”第 {index} 条多段线的最左端点未匹配到“钢束编号”文字（容差 {tolerance:.3f} m）")
    if len(matched) > 1:
        raise BatchDxfImportError(f"图层“{layer}”第 {index} 条多段线的最左端点匹配到多个编号：{'、'.join(sorted(matched))}")
    return matched[0]


def _unique_profiles(profiles: list[_LabeledProfile], layer: str) -> dict[str, ProfileInput]:
    """校核同一图层内每个编号仅对应一条线形。"""
    result: dict[str, ProfileInput] = {}
    for item in profiles:
        if item.tendon_id in result:
            raise BatchDxfImportError(f"图层“{layer}”中编号“{item.tendon_id}”匹配到多条多段线")
        result[item.tendon_id] = item.profile
    return result


def _validate_label_coverage(labels: dict[str, list[tuple[float, float]]], elevations: dict[str, ProfileInput], plans: dict[str, ProfileInput]) -> None:
    """每个编号都必须在平、立面各匹配一条线形，避免遗漏或误导入。"""
    missing_elevation = sorted(set(plans) - set(elevations))
    missing_plan = sorted(set(elevations) - set(plans))
    unused = sorted(set(labels) - set(elevations) - set(plans))
    messages: list[str] = []
    if missing_elevation:
        messages.append(f"缺少立面线形：{'、'.join(missing_elevation)}")
    if missing_plan:
        messages.append(f"缺少平面线形：{'、'.join(missing_plan)}")
    if unused:
        messages.append(f"编号文字未匹配任何线形：{'、'.join(unused)}")
    if messages:
        raise BatchDxfImportError("；".join(messages))
