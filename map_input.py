"""Đọc dữ liệu bản đồ, không phụ thuộc tên file hoặc tên sheet."""
import json
import math
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook


SUPPORTED_EXTENSIONS = {'.geojson', '.json', '.xlsx', '.docx', '.txt'}


@dataclass(frozen=True)
class MapInput:
    mode: str
    data: dict


def json_value(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Dữ liệu có số không hữu hạn (NaN/Infinity).')
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def read_excel(path):
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            sheets = []
            for sheet in workbook:
                # Giữ cả hàng tiêu đề, ghi chú và hàng trống trong bảng gốc.
                rows = [[json_value(cell) for cell in row] for row in sheet.values]
                if any(any(cell is not None and cell != '' for cell in row) for row in rows):
                    sheets.append({'sheet': sheet.title, 'rows': rows})
        finally:
            workbook.close()
    except (BadZipFile, KeyError, OSError) as exc:
        raise ValueError('Không đọc được Excel. Hãy kiểm tra file .xlsx có hợp lệ không.') from exc
    if not sheets:
        raise ValueError('Excel không có sheet chứa dữ liệu.')
    return {'sheets': sheets}


def read_word(path):
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    from docx.opc.exceptions import PackageNotFoundError

    try:
        document = Document(path)
        parts, table_count = [], 0
        for block in document.iter_inner_content():
            if isinstance(block, Paragraph):
                parts.append(block.text)
            elif isinstance(block, Table):
                table_count += 1
                parts.append(f'[Bảng {table_count}]')
                parts.extend('\t'.join(cell.text for cell in row.cells) for row in block.rows)
        text = '\n'.join(parts)
    except (BadZipFile, KeyError, OSError, PackageNotFoundError) as exc:
        raise ValueError('Không đọc được Word. Hãy kiểm tra file .docx có hợp lệ không.') from exc
    if not text.strip():
        raise ValueError('Word không có văn bản hoặc bảng để đọc. V1 chưa hỗ trợ OCR từ ảnh.')
    return {'text': text}


def read_text(path):
    try:
        text = Path(path).read_text(encoding='utf-8-sig')
    except UnicodeError as exc:
        raise ValueError('Không giải mã được TXT. Hãy lưu file bằng UTF-8 rồi thử lại.') from exc
    if not text.strip():
        raise ValueError('File TXT rỗng hoặc chỉ chứa khoảng trắng.')
    return {'text': text}


def invalid_constant(value):
    raise ValueError(f'JSON có giá trị không hợp lệ: {value}.')


def validate_geojson(value):
    """Kiểm tra cấu trúc và tọa độ WGS84, không sửa geometry của người dùng."""
    def fail(message):
        raise ValueError('GeoJSON không hợp lệ: ' + message)

    def sequence(item, minimum=0):
        if not isinstance(item, list) or len(item) < minimum:
            fail('mảng tọa độ hoặc danh sách đối tượng không hợp lệ.')

    def position(point):
        sequence(point, 2)
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in point):
            fail('tọa độ phải là số hữu hạn.')
        if not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
            fail('tọa độ phải dùng WGS84 theo [lng, lat]; không tự chuyển hệ tọa độ.')

    def line(points):
        sequence(points, 2)
        for point in points:
            position(point)

    def polygon(rings):
        sequence(rings, 1)
        for ring in rings:
            sequence(ring, 4)
            for point in ring:
                position(point)
            if ring[0] != ring[-1]:
                fail('vòng Polygon phải khép kín.')

    def geometry(item):
        if not isinstance(item, dict):
            fail('geometry phải là object.')
        kind = item.get('type')
        coordinates = item.get('coordinates')
        if kind == 'GeometryCollection':
            sequence(item.get('geometries'))
            for child in item['geometries']:
                geometry(child)
        elif kind == 'Point':
            position(coordinates)
        elif kind == 'MultiPoint':
            sequence(coordinates)
            for point in coordinates:
                position(point)
        elif kind == 'LineString':
            line(coordinates)
        elif kind == 'MultiLineString':
            sequence(coordinates)
            for points in coordinates:
                line(points)
        elif kind == 'Polygon':
            polygon(coordinates)
        elif kind == 'MultiPolygon':
            sequence(coordinates)
            for rings in coordinates:
                polygon(rings)
        else:
            fail('type geometry không được hỗ trợ.')

    def feature(item):
        if not isinstance(item, dict) or item.get('type') != 'Feature':
            fail('features phải chứa các Feature.')
        if 'geometry' not in item or 'properties' not in item:
            fail('Feature cần geometry và properties (có thể là null).')
        if item['properties'] is not None and not isinstance(item['properties'], dict):
            fail('properties phải là object hoặc null.')
        if item['geometry'] is not None:
            geometry(item['geometry'])

    if not isinstance(value, dict):
        fail('cần Feature, FeatureCollection hoặc geometry.')
    crs = value.get('crs')
    if crs is not None:
        name = crs.get('properties', {}).get('name', '') if isinstance(crs, dict) else ''
        if name not in ('EPSG:4326', 'urn:ogc:def:crs:OGC:1.3:CRS84', 'urn:ogc:def:crs:EPSG::4326'):
            fail('hệ tọa độ chưa được hỗ trợ; hãy chuyển sang WGS84.')
    if value.get('type') == 'FeatureCollection':
        sequence(value.get('features'))
        for item in value['features']:
            feature(item)
    elif value.get('type') == 'Feature':
        feature(value)
    else:
        geometry(value)


def read_geojson(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'),
                           parse_constant=invalid_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError('Không đọc được GeoJSON. File phải là JSON hợp lệ, mã hóa UTF-8.') from exc
    validate_geojson(value)
    return {'geojson': value}


def read_input(path, filename=None):
    path = Path(path)
    filename = filename or path.name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError('Chỉ hỗ trợ .geojson, .json (GeoJSON), .xlsx, .docx và .txt.')
    if path.stat().st_size == 0:
        raise ValueError('File tải lên rỗng.')
    readers = {'.geojson': read_geojson, '.json': read_geojson, '.xlsx': read_excel,
               '.docx': read_word, '.txt': read_text}
    try:
        data = readers[extension](path)
    except ValueError:
        raise
    except Exception as exc:
        # Các parser XML/ZIP có nhiều loại exception tùy phiên bản thư viện.
        raise ValueError(f'Không đọc được file {extension}. File có thể bị hỏng hoặc sai định dạng.') from exc
    data['source'] = {'fileName': filename}
    return MapInput('text_analysis' if extension in ('.docx', '.txt') else 'analysis', data)
