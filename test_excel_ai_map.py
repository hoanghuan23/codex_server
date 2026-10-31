"""Đọc Excel, nhờ Codex tự thiết kế bản đồ và xuất index.html/style.css/app.js.
Chạy: python test_excel_ai_map.py [duong_dan_excel]
Yêu cầu: pip install requests python-dotenv openpyxl
"""
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from openpyxl import load_workbook

load_dotenv()
BASE = Path(__file__).resolve().parent
EXCEL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE / 'metro_arc_flow_gia_lap.xlsx'
OUTPUT = BASE / 'output_metro_arc_flow_3D'
URL = os.getenv('CODEX_API_URL', 'http://127.0.0.1:8000/analyze')
MODEL = os.getenv('CODEX_MODEL', 'gpt-5.6-luna')
SHEET_NAME = "Luu_luong_OD"


def read_excel(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    result = []
    for sheet in wb:
        rows = list(sheet.values)
        if not rows:
            continue
        # Dữ liệu bản đồ: hàng đầu là tên cột; các sheet khác cung cấp metadata.
        if sheet.title == SHEET_NAME:
            headers = [str(v).strip().replace('\n', ' ') if v is not None else f'column_{i}'
                       for i, v in enumerate(rows[0])]
            data = [dict(zip(headers, [cell_value(x) for x in row])) for row in rows[1:]
                    if any(x is not None for x in row)]
            result.append({'sheet': sheet.title, 'columns': headers, 'rows': data})
        elif sheet.title in ('Danh muc', 'Van ban hien thi'):
            result.append({'sheet': sheet.title,
                           'rows': [[cell_value(v) for v in row] for row in rows[:100]]})
    wb.close()
    return result


def cell_value(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return v.isoformat() if hasattr(v, 'isoformat') else str(v)

request = """
Đóng vai trò chuyên gia GIS, trực quan hóa dữ liệu và thiết kế UI/UX.

Từ dữ liệu Excel cung cấp, TỰ PHÂN TÍCH và TỰ ĐỀ XUẤT bản đồ trực quan hóa phù hợp.
Không mặc định dữ liệu là số đo: phân loại cột địa lý, phân loại, định lượng,
thời gian, ID và văn bản; chọn cách biểu diễn phù hợp với ngữ nghĩa thực tế.

YÊU CẦU:

1. Phân tích dữ liệu:
- Xác định ý nghĩa các cột, nhóm dữ liệu, phạm vi và cấp độ địa lý.
- Tự chọn loại bản đồ phù hợp: Polygon, Point, Line hoặc kết hợp.
- Tự đề xuất màu sắc, kiểu hiển thị, mức zoom và cách thể hiện dữ liệu.

2. Bố cục bản đồ:
- Bản đồ phải chiếm toàn bộ màn hình (100vw, 100vh).
- Không tạo header, footer, tiêu đề trang, dashboard, sidebar cố định
  hoặc các khối nội dung độc lập bên ngoài bản đồ.
- Không tạo phần giới thiệu, thống kê tổng quan hay mô tả dài phía trên bản đồ.
- Tất cả thành phần giao diện phải được hiển thị dạng overlay
  trực tiếp trên bản đồ.
- Ưu tiên giao diện gọn gàng, trực quan, không che khuất dữ liệu địa lý.

3. Các chức năng tương tác:
- AI tự đánh giá và đề xuất những chức năng thực sự cần thiết
  dựa trên đặc điểm dữ liệu đầu vào.
- Có thể bao gồm: tìm kiếm khu vực, bộ lọc dữ liệu, lựa chọn chỉ tiêu,
  chuyển đổi lớp bản đồ, điều khiển thời gian và chú giải.
- Tất cả chức năng phải nằm trực tiếp trên bản đồ dưới dạng
  floating control, dropdown, popup hoặc panel có thể thu gọn.
- Không tạo chức năng không có ý nghĩa đối với dữ liệu.
- Các chức năng được đề xuất phải hoạt động thực tế.

4. Chú giải và popup:
- AI tự đề xuất chú giải categorical hoặc continuous phù hợp.
- Chú giải hiển thị nổi trên bản đồ, ưu tiên vị trí góc dưới.
- Popup xuất hiện khi người dùng tương tác với đối tượng địa lý.
- Tự quyết định nội dung popup theo các trường dữ liệu thực tế.
- Không tạo bảng thống kê hoặc khối thông tin riêng ngoài bản đồ.

5. Dữ liệu và địa lý:
- Dùng MapLibre GL JS với bản đồ nền OpenFreeMap.
- Nếu cần ranh giới địa lý, sử dụng GeoJSON thực tế từ nguồn công khai.
- Không tự bịa tọa độ, ranh giới hoặc giá trị dữ liệu.
- Không suy diễn giá trị trống thành dữ liệu thật.
- Dữ liệu Excel phải được nhúng vào JS hoặc sử dụng tài nguyên công khai.
- Không yêu cầu người dùng upload lại dữ liệu.

6. Trải nghiệm sử dụng:
- Giao diện responsive trên desktop và mobile.
- Các điều khiển phải gọn, dễ sử dụng và không chồng chéo.
- Có trạng thái loading, empty và error khi cần thiết.
- Tự quyết định vị trí các thành phần overlay sao cho hợp lý.
- Không cần hỏi lại người dùng.

NGUYÊN TẮC BẮT BUỘC:
Sản phẩm cuối cùng là MỘT BẢN ĐỒ TƯƠNG TÁC TOÀN MÀN HÌNH,
không phải trang dashboard hay website báo cáo.
Mọi thông tin, công cụ và tương tác đều phải nằm trong bản đồ.
AI được tự do đề xuất tính năng và thiết kế nhưng phải tuân thủ
nguyên tắc bố cục này.

OUTPUT BẮT BUỘC:
Trả về DUY NHẤT một JSON object hợp lệ, không markdown, không giải thích,
chứa chính xác ba khóa: "index.html", "style.css", "app.js".
Mỗi giá trị là toàn bộ nội dung file tương ứng dưới dạng JSON string.
index.html liên kết tới ./style.css và ./app.js (defer),
không nhúng mã CSS/JS nội bộ.
Mã JS phải tương thích với các thư viện được nạp trong index.html.
"""

def parse_files(raw):
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError('AI không trả JSON hợp lệ. Đã lưu raw_response.txt để kiểm tra.') from e
    required = {'index.html', 'style.css', 'app.js'}
    if not isinstance(obj, dict) or not required.issubset(obj):
        raise ValueError('AI không trả đủ 3 file: index.html, style.css, app.js')
    for name in required:
        if not isinstance(obj[name], str) or not obj[name].strip():
            raise ValueError(f'Nội dung file {name} rỗng hoặc không phải chuỗi')
    if not re.search(r'<!doctype html', obj['index.html'], re.I):
        raise ValueError('index.html không có DOCTYPE')
    return obj


def main():
    if not EXCEL.is_file():
        raise FileNotFoundError(f'Không tìm thấy Excel: {EXCEL}')
    token = os.getenv('CODEX_API_TOKEN')
    if not token:
        raise RuntimeError('Thiếu CODEX_API_TOKEN trong môi trường/.env')
    excel_data = read_excel(EXCEL)
    if not any(s['sheet'] == SHEET_NAME for s in excel_data):
        raise ValueError('Không tìm thấy sheet "Du lieu ban do"')
    prompt = (
        'Bạn là AI tạo ứng dụng bản đồ từ dữ liệu Excel.\n\n'
        + request + '\n\nDỮ LIỆU EXCEL (JSON trích xuất nguyên giá trị):\n'
        + json.dumps(excel_data, ensure_ascii=False, default=str, separators=(',', ':'))
    )
    print('Số ký tự prompt:', len(prompt))
    print('Nguồn:', EXCEL)
    response = requests.post(URL, headers={'X-API-Key': token},
                             json={'model': MODEL, 'prompt': prompt}, timeout=None)
    print('HTTP status:', response.status_code)
    if not response.ok:
        print('Chi tiết lỗi từ server:', response.text)
    response.raise_for_status()
    payload = response.json()
    if not payload.get('success'):
        raise RuntimeError('Codex thất bại: ' + str(payload)[:1200])
    raw = payload.get('result', '')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = parse_files(raw)
    for name in ('index.html', 'style.css', 'app.js'):
        path = OUTPUT / name
        path.write_text(files[name], encoding='utf-8')
        print('Đã tạo:', path)
    print('Mở output_ai_map/index.html để xem (nếu trình duyệt chặn tài nguyên, chạy python -m http.server).')

if __name__ == '__main__':
    main()
