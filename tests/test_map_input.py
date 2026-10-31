"""Các bộ đọc giữ giá trị thực và ngữ cảnh, không gọi AI."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from docx import Document
from openpyxl import Workbook

from map_input import read_input


class MapInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_excel_keeps_all_nonempty_sheets_and_raw_values(self):
        path = self.root / 'tên bất kỳ.xlsx'
        book = Workbook()
        main = book.active
        main.title = 'Số liệu 2024'
        main.append(['Ghi chú: dữ liệu kiểm thử'])
        main.append(['Địa danh', 'Giá trị', 'Kỳ', 'Đơn vị'])
        main.append(['Huế', 0, datetime(2024, 1, 1), 'người'])
        main.append(['Đà Nẵng', None, datetime(2024, 2, 1), 'người'])
        coordinates = book.create_sheet('Vị trí')
        coordinates.append(['Địa danh', 'lng', 'lat'])
        coordinates.append(['Huế', 107.59, 16.46])
        book.create_sheet('Trống')
        book.save(path)
        book.close()
        result = read_input(path)
        self.assertEqual(result.mode, 'analysis')
        self.assertEqual(result.data['source']['fileName'], path.name)
        self.assertEqual([s['sheet'] for s in result.data['sheets']], ['Số liệu 2024', 'Vị trí'])
        rows = result.data['sheets'][0]['rows']
        self.assertEqual(rows[0][0], 'Ghi chú: dữ liệu kiểm thử')
        self.assertEqual(rows[2], ['Huế', 0, '2024-01-01T00:00:00', 'người'])
        self.assertIsNone(rows[3][1])

    def test_word_keeps_paragraph_table_order_and_empty_cells(self):
        path = self.root / 'báo cáo.docx'
        document = Document()
        document.add_paragraph('Báo cáo kiểm thử năm 2024')
        table = document.add_table(rows=2, cols=3)
        for cell, value in zip(table.rows[0].cells, ['Khu vực', 'Số lượng', 'Ghi chú']):
            cell.text = value
        for cell, value in zip(table.rows[1].cells, ['Huế', '0', '']):
            cell.text = value
        document.add_paragraph('Kết thúc báo cáo.')
        document.save(path)
        result = read_input(path)
        text = result.data['text']
        self.assertEqual(result.mode, 'text_analysis')
        self.assertIn('Huế\t0\t', text)
        self.assertLess(text.index('Báo cáo kiểm thử'), text.index('[Bảng 1]'))
        self.assertLess(text.index('Huế\t0'), text.index('Kết thúc'))

    def test_utf8_bom_text_preserves_vietnamese(self):
        path = self.root / 'văn bản.TXT'
        path.write_text('Huế: 0 người; Đà Nẵng: chưa có dữ liệu.', encoding='utf-8-sig')
        result = read_input(path)
        self.assertEqual(result.data['text'], 'Huế: 0 người; Đà Nẵng: chưa có dữ liệu.')
        self.assertEqual(result.mode, 'text_analysis')

    def test_geojson_preserves_geometry_and_properties(self):
        for extension in ('.geojson', '.json'):
            with self.subTest(extension=extension):
                path = self.root / ('đổi tên' + extension)
                value = {'type': 'FeatureCollection', 'features': [
                    {'type': 'Feature', 'properties': {'Tên': 'Huế', 'Số': 0, 'Thiếu': None},
                     'geometry': {'type': 'Point', 'coordinates': [107.59, 16.46]}}]}
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                self.assertEqual(read_input(path).data['geojson'], value)

    def test_geojson_accepts_supported_geometry_types(self):
        ring = [[100, 10], [101, 10], [101, 11], [100, 10]]
        geometries = [
            {'type': 'MultiPoint', 'coordinates': [[0, 0], [107, 16]]},
            {'type': 'LineString', 'coordinates': [[100, 10], [101, 11]]},
            {'type': 'MultiLineString', 'coordinates': [[[100, 10], [101, 11]]]},
            {'type': 'Polygon', 'coordinates': [ring]},
            {'type': 'MultiPolygon', 'coordinates': [[ring]]},
            {'type': 'GeometryCollection', 'geometries': [
                {'type': 'Point', 'coordinates': [0, 0, 3]}]},
        ]
        for geometry in geometries:
            with self.subTest(kind=geometry['type']):
                path = self.root / 'geometry.geojson'
                path.write_text(json.dumps(geometry), encoding='utf-8')
                self.assertEqual(read_input(path).data['geojson'], geometry)

    def test_geojson_rejects_malformed_geometry_and_unknown_crs(self):
        cases = [[], {'hello': 'world'}, {'type': 'FeatureCollection', 'features': [1]},
                 {'type': 'Point', 'coordinates': [16]},
                 {'type': 'Point', 'coordinates': [500000, 2000000]},
                 {'type': 'Point', 'coordinates': [True, 16]},
                 {'type': 'LineString', 'coordinates': [[107, 16]]},
                 {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
                 {'type': 'Point', 'coordinates': [0, 0],
                  'crs': {'properties': {'name': 'EPSG:3857'}}}]
        path = self.root / 'invalid.json'
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ValueError):
                path.write_text(json.dumps(value), encoding='utf-8')
                read_input(path)
        path.write_text('{"type":"Point","coordinates":[NaN,0]}', encoding='utf-8')
        with self.assertRaises(ValueError):
            read_input(path)

    def test_empty_corrupt_and_unsupported_files_report_errors(self):
        for filename, contents in [('empty.txt', b''), ('space.txt', b' \n'),
                                   ('bad.txt', b'\xff\xfe'), ('bad.xlsx', b'not xlsx'),
                                   ('bad.docx', b'not docx'), ('bad.json', b'{oops'),
                                   ('old.xls', b'xls'), ('old.doc', b'doc')]:
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                path = self.root / filename
                path.write_bytes(contents)
                read_input(path)

    def test_empty_workbook_and_image_only_word_are_rejected(self):
        path = self.root / 'empty.xlsx'
        book = Workbook()
        book.save(path)
        book.close()
        with self.assertRaisesRegex(ValueError, 'không có sheet'):
            read_input(path)
        path = self.root / 'empty.docx'
        Document().save(path)
        with self.assertRaisesRegex(ValueError, 'OCR'):
            read_input(path)
