"""Đọc văn bản TXT, nhờ Codex tự thiết kế bản đồ và xuất index.html/style.css/app.js.
Chạy: python test_text_ai_map.py [duong_dan_txt]
Mặc định đọc report_chiso_phatrien_connguoi.txt trong thư mục chứa script.
Yêu cầu: pip install requests python-dotenv
"""
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parent
TEXT_FILE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BASE / 'report_chiso_phatrien_connguoi.txt'
OUTPUT = BASE / 'output_text_ai_map'
URL = os.getenv('CODEX_API_URL', 'http://127.0.0.1:8000/analyze')
MODEL = os.getenv('CODEX_MODEL', 'gpt-5.6-luna')

request = """
Đóng vai trò chuyên gia GIS, trực quan hóa dữ liệu và thiết kế UI/UX.
Từ nội dung file văn bản TXT cung cấp, TỰ PHÂN TÍCH và TỰ ĐỀ XUẤT giao diện bản đồ phù hợp.
Văn bản có thể là báo cáo, đoạn văn hoặc danh sách, không nhất thiết có bảng hay cột.
Trích xuất địa danh, chỉ tiêu, giá trị, đơn vị, thời gian và nguồn được nêu trong văn bản;
phân biệt dữ liệu địa lý, phân loại, định lượng và mô tả để chọn biểu diễn phù hợp.

YÊU CẦU:
1. Xác định các thực thể địa lý, ý nghĩa từng chỉ tiêu, nhóm dữ liệu và phạm vi dữ liệu.
   Gắn đúng giá trị với địa danh và chỉ tiêu; đọc đúng dấu phẩy thập phân trong văn bản.
   Phân biệt năm của dữ liệu với năm công bố báo cáo, nếu văn bản có nêu.
2. Tự chọn loại lớp bản đồ (Polygon, Point, Line hoặc kết hợp), cách tô màu và mức zoom.
3. Tự đề xuất chú giải: loại categorical/continuous, màu sắc, nhãn và thứ tự.
4. Tự đánh giá có cần thanh tìm kiếm không; nếu cần chọn trường tìm kiếm phù hợp.
5. Tự đề xuất bộ lọc, trạng thái hiển thị, nút chuyển đổi, điều khiển lớp và bộ đếm
   dựa trên dữ liệu, không thêm điều khiển vô nghĩa.
6. Tự chọn bố cục popup, tiêu đề, mô tả, điều kiện, ghi chú và trạng thái khi click.
7. Thiết kế giao diện responsive, có loading, empty và error state.
8. Dùng MapLibre GL JS với bản đồ nền OpenFreeMap. Nếu cần ranh giới quốc gia,
   dùng GeoJSON công khai thực tế, có kiểm tra mã quốc gia/địa danh và nguồn dữ liệu;
   không bịa tọa độ hay gán sai khu vực. Các đảo nhỏ không có Polygon có thể dùng
   Point có tọa độ xác thực, nếu không có phải nêu rõ là chưa định vị được.
9. Chỉ trích xuất dữ liệu được nêu rõ; thông tin thiếu phải để trống/null, không gán 0
   hay tự bổ sung giá trị. Phân biệt thông tin trong file với thông tin từ Internet;
   ghi rõ nguồn và thời điểm dữ liệu nếu có, không tự coi là dữ liệu hiện hành.
10. Tạo giao diện có thể sử dụng được, dữ liệu trích xuất từ TXT phải được nhúng trong JS
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
    if not TEXT_FILE.is_file():
        raise FileNotFoundError(f'Không tìm thấy file TXT: {TEXT_FILE}')
    text_data = TEXT_FILE.read_text(encoding='utf-8-sig')
    if not text_data.strip():
        raise ValueError(f'File TXT rỗng hoặc chỉ chứa khoảng trắng: {TEXT_FILE}')
    token = os.getenv('CODEX_API_TOKEN')
    if not token:
        raise RuntimeError('Thiếu CODEX_API_TOKEN trong môi trường/.env')
    prompt = (
        'Bạn là AI tạo ứng dụng bản đồ từ dữ liệu văn bản TXT.\n\n'
        + request + '\n\nNỘI DUNG FILE TXT:\n'
        + text_data
    )
    print('Số ký tự prompt:', len(prompt))
    print('Nguồn:', TEXT_FILE)
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
    print(f'Mở {OUTPUT / "index.html"} để xem (nếu trình duyệt chặn tài nguyên, chạy python -m http.server).')

if __name__ == '__main__':
    main()
