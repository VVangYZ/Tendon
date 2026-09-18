"""DXF 钢束线形导入测试。"""

import unittest
from io import StringIO

import ezdxf

from app.services.dxf_import import DxfImportError, import_dxf_profiles


def create_dxf(layers: dict[str, list[list[tuple[float, float, float]]]]) -> bytes:
    """创建包含指定轻量多段线的最小 DXF 测试文件。"""
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    for layer, polylines in layers.items():
        for points in polylines:
            modelspace.add_lwpolyline(points, format="xyb", dxfattribs={"layer": layer})
    stream = StringIO()
    document.write(stream)
    return stream.getvalue().encode("utf-8")


class DxfImportTest(unittest.TestCase):
    def test_import_accepts_legacy_2d_polyline(self) -> None:
        """旧式二维 POLYLINE 也应按同一约定导入。"""
        document = ezdxf.new("R2010")
        modelspace = document.modelspace()
        modelspace.add_polyline2d([(0, 0), (2, 0)], dxfattribs={"layer": "立面"})
        modelspace.add_polyline2d([(0, 1), (2, 1)], dxfattribs={"layer": "平面"})
        stream = StringIO()
        document.write(stream)

        result = import_dxf_profiles(stream.getvalue().encode("utf-8"), "m")

        self.assertEqual(result.elevation.points, [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)])
        self.assertEqual(result.plan.points, [(0.0, 1.0, 0.0), (2.0, 1.0, 0.0)])

    def test_import_converts_mm_and_reverses_bulge(self) -> None:
        """导入应换算单位，并在反向时正确处理 bulge。"""
        content = create_dxf(
            {
                "立面": [[(0, 0, 0), (1000, 200, 0.2), (2000, 0, 0)]],
                "平面": [[(2000, 0, 0.1), (1000, 100, 0.2), (0, 0, 0)]],
            }
        )

        result = import_dxf_profiles(content, "mm")

        self.assertEqual(result.elevation.points, [(0.0, 0.0, 0.0), (1.0, 0.2, 0.2), (2.0, 0.0, 0.0)])
        self.assertEqual(result.plan.points, [(0.0, 0.0, -0.2), (1.0, 0.1, -0.1), (2.0, 0.0, 0.0)])

    def test_import_rejects_multiple_polylines_in_target_layer(self) -> None:
        """同一目标图层存在多条多段线时应拒绝导入。"""
        content = create_dxf(
            {
                "立面": [[(0, 0, 0), (2, 0, 0)]],
                "平面": [[(0, 0, 0), (2, 0, 0)], [(0, 1, 0), (2, 1, 0)]],
            }
        )

        with self.assertRaisesRegex(DxfImportError, "检测到 2 条多段线"):
            import_dxf_profiles(content, "m")

    def test_import_rejects_mismatched_station_range(self) -> None:
        """平面与立面首尾里程不一致时应拒绝导入。"""
        content = create_dxf(
            {
                "立面": [[(0, 0, 0), (2, 0, 0)]],
                "平面": [[(0.01, 0, 0), (2, 0, 0)]],
            }
        )

        with self.assertRaisesRegex(DxfImportError, "首尾 x 坐标不一致"):
            import_dxf_profiles(content, "m")
