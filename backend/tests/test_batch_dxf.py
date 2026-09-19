"""批量 DXF 编号文字关联测试。"""

import unittest
from io import StringIO

import ezdxf

from app.services.batch_dxf import BatchDxfImportError, import_batch_dxf


def create_batch_dxf() -> bytes:
    """创建两根钢束的最小测试图纸。"""
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    modelspace.add_lwpolyline([(0, 0, 0), (10, 1, 0)], format="xyb", dxfattribs={"layer": "立面"})
    modelspace.add_lwpolyline([(0, 10, 0), (10, 11, 0)], format="xyb", dxfattribs={"layer": "平面"})
    # 第二根反向绘制，用于确认匹配点取标准化后的最左端点。
    modelspace.add_lwpolyline([(25, 2, 0), (15, 2, 0)], format="xyb", dxfattribs={"layer": "立面"})
    modelspace.add_lwpolyline([(25, 12, 0), (15, 12, 0)], format="xyb", dxfattribs={"layer": "平面"})
    for text, point in [("T1", (0, 0)), ("T1", (0, 10)), ("T2", (15, 2)), ("T2", (15, 12))]:
        modelspace.add_text(text, dxfattribs={"layer": "钢束编号", "insert": point})
    stream = StringIO()
    document.write(stream)
    return stream.getvalue().encode("utf-8")


class BatchDxfImportTest(unittest.TestCase):
    def test_import_matches_text_labels_and_normalizes_direction(self) -> None:
        """同编号文字应配对平立面线形，反向线形应自动转正。"""
        project = import_batch_dxf(create_batch_dxf(), "m", 0.05)

        self.assertEqual([tendon.id for tendon in project.tendons], ["T1", "T2"])
        self.assertEqual(project.tendons[1].elevation.points[0].x, 15)
        self.assertEqual(project.tendons[1].plan.points[-1].x, 25)
        self.assertEqual(project.defaults.unit, "m")

    def test_import_rejects_unmatched_polyline(self) -> None:
        """每条线形左端均须在容差内匹配编号文字。"""
        document = ezdxf.new("R2010")
        modelspace = document.modelspace()
        modelspace.add_lwpolyline([(0, 0), (10, 0)], dxfattribs={"layer": "立面"})
        modelspace.add_lwpolyline([(0, 1), (10, 1)], dxfattribs={"layer": "平面"})
        modelspace.add_text("T1", dxfattribs={"layer": "钢束编号", "insert": (1, 0)})
        stream = StringIO()
        document.write(stream)

        with self.assertRaisesRegex(BatchDxfImportError, "未匹配到"):
            import_batch_dxf(stream.getvalue().encode("utf-8"), "m", 0.05)
