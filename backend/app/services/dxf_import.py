"""受限 DXF 钢束线形导入服务。"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import ezdxf
from ezdxf.filemanagement import dxf_stream_info
from ezdxf.lldxf.const import DXFError


LAYER_ELEVATION = "立面"
LAYER_PLAN = "平面"
ENDPOINT_TOLERANCE_M = 0.001
X_TOLERANCE_M = 1e-9


class DxfImportError(ValueError):
    """DXF 不符合本工具约定时抛出。"""


@dataclass(frozen=True)
class ImportedProfile:
    """导入后可直接写入 x/y/b 表格的一条线形。"""

    points: list[tuple[float, float, float]]


@dataclass(frozen=True)
class DxfImportResult:
    """DXF 导入的平面与立面结果。"""

    elevation: ImportedProfile
    plan: ImportedProfile


def import_dxf_profiles(content: bytes, unit: str) -> DxfImportResult:
    """读取 DXF 中约定图层的唯一开放二维多段线。"""
    if not content:
        raise DxfImportError("DXF 文件为空")
    if len(content) > 20 * 1024 * 1024:
        raise DxfImportError("DXF 文件不得大于 20 MB")

    scale = _unit_scale(unit)
    document = _read_document(content)
    modelspace = document.modelspace()
    elevation = _read_layer_polyline(modelspace, LAYER_ELEVATION, scale)
    plan = _read_layer_polyline(modelspace, LAYER_PLAN, scale)
    _validate_matching_endpoints(elevation, plan)
    return DxfImportResult(elevation=ImportedProfile(elevation), plan=ImportedProfile(plan))


def _unit_scale(unit: str) -> float:
    """将用户确认的图纸单位换算为计算内核使用的米。"""
    if unit == "m":
        return 1.0
    if unit == "mm":
        return 0.001
    raise DxfImportError("单位仅支持 m 或 mm")


def _read_document(content: bytes):
    """在内存中按 DXF 头部声明的编码读取图纸，避免上传文件落盘。"""
    try:
        header_text = content.decode("utf-8-sig", errors="surrogateescape")
        encoding = dxf_stream_info(StringIO(header_text)).encoding
        return ezdxf.read(StringIO(content.decode(encoding, errors="surrogateescape")))
    except (OSError, DXFError, UnicodeError) as error:
        raise DxfImportError("无法读取 DXF 文件，请确认文件未损坏且格式正确") from error


def _read_layer_polyline(modelspace, layer: str, scale: float) -> list[tuple[float, float, float]]:
    """读取一个固定图层中唯一的开放二维多段线。"""
    polylines = [
        entity
        for entity in modelspace
        if entity.dxf.layer == layer and entity.dxftype() in {"LWPOLYLINE", "POLYLINE"}
    ]
    if not polylines:
        raise DxfImportError(f"图层“{layer}”未找到多段线")
    if len(polylines) > 1:
        raise DxfImportError(f"图层“{layer}”检测到 {len(polylines)} 条多段线，请仅保留一条")

    polyline = polylines[0]
    if polyline.dxftype() == "POLYLINE" and not polyline.is_2d_polyline:
        raise DxfImportError(f"图层“{layer}”仅支持二维多段线")
    if polyline.closed:
        raise DxfImportError(f"图层“{layer}”的多段线必须为非闭合线")

    points = _extract_points(polyline, scale)
    if len(points) < 2:
        raise DxfImportError(f"图层“{layer}”的多段线至少需要两个节点")
    return _normalize_direction(points, layer)


def _extract_points(polyline, scale: float) -> list[tuple[float, float, float]]:
    """提取直线与 bulge 圆弧节点，并统一为米。"""
    if polyline.dxftype() == "LWPOLYLINE":
        raw_points = polyline.get_points("xyb")
        return [(float(x) * scale, float(y) * scale, float(bulge)) for x, y, bulge in raw_points]
    return [
        (
            float(vertex.dxf.location.x) * scale,
            float(vertex.dxf.location.y) * scale,
            float(vertex.dxf.get("bulge", 0.0)),
        )
        for vertex in polyline.vertices
    ]


def _normalize_direction(points: list[tuple[float, float, float]], layer: str) -> list[tuple[float, float, float]]:
    """统一为 x 递增；反向时同步反转并取反 bulge。"""
    if points[-1][0] < points[0][0] - X_TOLERANCE_M:
        normalized = [
            (points[old_index][0], points[old_index][1], 0.0 if index == len(points) - 1 else -points[old_index - 1][2])
            for index, old_index in enumerate(range(len(points) - 1, -1, -1))
        ]
    else:
        normalized = [(x, y, bulge if index < len(points) - 1 else 0.0) for index, (x, y, bulge) in enumerate(points)]

    for previous, current in zip(normalized, normalized[1:]):
        if current[0] <= previous[0] + X_TOLERANCE_M:
            raise DxfImportError(f"图层“{layer}”的 x 坐标必须严格递增，当前线形存在回头或重合节点")
    return normalized


def _validate_matching_endpoints(elevation: list[tuple[float, float, float]], plan: list[tuple[float, float, float]]) -> None:
    """校核平面与立面在同一里程范围内。"""
    start_difference = abs(elevation[0][0] - plan[0][0])
    end_difference = abs(elevation[-1][0] - plan[-1][0])
    if start_difference > ENDPOINT_TOLERANCE_M or end_difference > ENDPOINT_TOLERANCE_M:
        raise DxfImportError(
            "平面与立面的首尾 x 坐标不一致"
            f"（起点差 {start_difference:.6f} m，终点差 {end_difference:.6f} m，允许差 {ENDPOINT_TOLERANCE_M:.3f} m）"
        )
