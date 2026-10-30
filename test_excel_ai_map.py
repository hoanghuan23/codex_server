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
EXCEL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE / 'test dữ liệu khu vực.xlsx'
OUTPUT = BASE / 'output_weather_ai_map'
URL = os.getenv('CODEX_API_URL', 'http://127.0.0.1:8000/analyze')
MODEL = os.getenv('CODEX_MODEL', 'gpt-5.6-luna')


def read_excel(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    result = []
    for sheet in wb:
        rows = list(sheet.values)
        if not rows:
            continue
        # Dữ liệu bản đồ: hàng đầu là tên cột; các sheet khác cung cấp metadata.
        if sheet.title == 'dữ liệu ô nhiễm':
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
Từ dữ liệu Excel cung cấp, TỰ PHÂN TÍCH và TỰ ĐỀ XUẤT giao diện bản đồ phù hợp.
Không mặc định dữ liệu là số đo: phân loại cột địa lý, phân loại, định lượng, thời gian,
ID và văn bản; chọn biểu diễn phù hợp với ngữ nghĩa thực tế.

YÊU CẦU:
1. Xác định ý nghĩa từng cột, các nhóm dữ liệu, mức địa lý và phạm vi dữ liệu.
2. Tự chọn loại lớp bản đồ (Polygon, Point, Line hoặc kết hợp), cách tô màu và mức zoom.
3. Tự đề xuất chú giải: loại categorical/continuous, màu sắc, nhãn và thứ tự.
4. Tự đánh giá có cần thanh tìm kiếm không; nếu cần chọn cột tìm kiếm phù hợp.
5. Tự đề xuất bộ lọc, trạng thái hiển thị, nút chuyển đổi, điều khiển lớp và bộ đếm
   dựa trên dữ liệu, không thêm điều khiển vô nghĩa.
6. Tự chọn bố cục popup, tiêu đề, mô tả, điều kiện, ghi chú và trạng thái khi click.
7. Thiết kế giao diện responsive, có loading, empty và error state.
8. Dùng MapLibre GL JS với bản đồ nền OpenFreeMap. Nếu cần ranh giới quốc gia,
   dùng GeoJSON công khai thực tế, có kiểm tra mã quốc gia/địa danh và nguồn dữ liệu;
   không bịa tọa độ hay gán sai khu vực. Các đảo nhỏ không có Polygon có thể dùng
   Point có tọa độ xác thực, nếu không có phải nêu rõ là chưa định vị được.
9. Không suy diễn các giá trị trống thành dữ liệu thật. Phân biệt thông tin trong file
   với thông tin cập nhật từ Internet; dữ liệu visa có thể thay đổi, ghi chú thời điểm
   của dữ liệu, không khẳng định thông tin visa là quy định hiện hành.
10. Tạo giao diện có thể sử dụng được, dữ liệu từ Excel phải được nhúng trong JS
    hoặc dùng tài nguyên công khai; không yêu cầu người dùng upload lại file.
11. Tự quyết định bố cục và tính năng dựa trên dữ liệu, không cần hỏi lại.

OUTPUT BẮT BUỘC:
Trả về DUY NHẤT một JSON object hợp lệ, không markdown, không giải thích,
chứa chính xác ba khóa: "index.html", "style.css", "app.js".
Mỗi giá trị là toàn bộ nội dung file tương ứng dưới dạng JSON string.
index.html liên kết tới ./style.css và ./app.js (defer), không nhúng mã CSS/JS nội bộ.
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
    if not any(s['sheet'] == 'dữ liệu ô nhiễm' for s in excel_data):
        raise ValueError('Không tìm thấy sheet "Du lieu ban do"')
    prompt = (
        'Bạn là AI tạo ứng dụng bản đồ từ dữ liệu Excel.\n\n'
        + request + '\n\nDỮ LIỆU EXCEL (JSON trích xuất nguyên giá trị):\n'
        + json.dumps(excel_data, ensure_ascii=False, default=str, separators=(',', ':'))
    )
    print('Số ký tự prompt:', len(prompt))
    print('Nguồn:', EXCEL)
    if len(prompt) > 20000:
        print('CHÚ Ý: Nếu server.py còn giới hạn 20000 ký tự, hãy tăng giới hạn trước khi chạy.')
    response = requests.post(URL, headers={'X-API-Key': token},
                             json={'model': MODEL, 'prompt': prompt}, timeout=None)
    print('HTTP status:', response.status_code)
    response.raise_for_status()
    payload = response.json()
    if not payload.get('success'):
        raise RuntimeError('Codex thất bại: ' + str(payload)[:1200])
    raw = payload.get('result', '')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'raw_response.txt').write_text(raw, encoding='utf-8')
    files = parse_files(raw)
    for name in ('index.html', 'style.css', 'app.js'):
        path = OUTPUT / name
        path.write_text(files[name], encoding='utf-8')
        print('Đã tạo:', path)
    print('Mở output_ai_map/index.html để xem (nếu trình duyệt chặn tài nguyên, chạy python -m http.server).')

if __name__ == '__main__':
    main()
