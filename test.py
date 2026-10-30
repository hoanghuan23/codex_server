import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = "http://127.0.0.1:8000/analyze"

response = requests.post(
    url,
    headers={
        "X-API-Key": os.environ["CODEX_API_TOKEN_TEST"]
    },
    json={
        "model": "gpt-5.6-luna",
        "prompt": "xin chào, bạn là ai"
    },
    timeout=150
)

print("Status:", response.status_code)
print("Response:", response.json(['result']))

# import os
# import re
# import requests
# from pathlib import Path
# from dotenv import load_dotenv

# load_dotenv()

# url = "http://127.0.0.1:8000/analyze"

# html_old = Path("ban_do_ha_noi.html").read_text(encoding="utf-8")

# request = """
# Cải tiến bản đồ HTML hiện tại để hiển thị dữ liệu thời tiết theo khu vực hành chính.
# 1. Tìm kiếm trên Internet và bổ sung dữ liệu GeoJSON ranh giới hành chính Hải Phòng và Ninh Bình sau sáp nhập năm 2025 (Nam Định cũ thuộc Ninh Bình mới). Giữ nguyên ranh giới Hà Nội. Sử dụng dữ liệu địa lý thực tế, không tự tạo tọa độ giả.

# 2. Hiển thị dữ liệu thời tiết giả lập cho 3 khu vực:
#    - Hà Nội: Nhiệt độ trung bình 25°C, lượng mưa 150 mm.
#    - Hải Phòng: Nhiệt độ trung bình 27°C, lượng mưa 170 mm.
#    - Ninh Bình: Nhiệt độ trung bình 26°C, lượng mưa 160 mm.

# 3. Sử dụng bản đồ Choropleth để tô màu Polygon theo giá trị dữ liệu. Giá trị thấp có màu nhạt, giá trị cao có màu đậm. Giữ đường viền phân biệt các khu vực.
# 4. Tạo hai nút chuyển đổi chỉ số "Nhiệt độ trung bình" và "Lượng mưa". Mặc định hiển thị nhiệt độ. Khi chuyển đổi, màu sắc các Polygon và chú giải phải tự động cập nhật mà không tải lại trang.
# 5. Tạo chú giải bản đồ dạng thanh màu gradient, hiển thị tên chỉ số, khoảng giá trị và đơn vị tương ứng (°C hoặc mm).
# 6. Khi nhấp vào Polygon, hiển thị popup gồm tên khu vực, nhiệt độ trung bình và lượng mưa. Làm nổi bật chỉ số đang được chọn.
# 7. Tự động điều chỉnh góc nhìn bản đồ để hiển thị đầy đủ cả 3 khu vực.
# 8. Giữ nguyên bản đồ nền OpenFreeMap, sử dụng MapLibre GL JS và bảo toàn các chức năng hiện có. Ưu tiên tái sử dụng mã nguồn, không viết lại những phần không cần thiết.
# 9. Nếu không tìm được dữ liệu ranh giới chính xác, hiển thị thông báo lỗi rõ ràng, không sử dụng dữ liệu giả.
# 10. Trả về toàn bộ mã HTML hoàn chỉnh, có thể chạy trực tiếp.
# """

# prompt = f"""
# Bạn là chuyên gia lập trình bản đồ GIS.

# Dưới đây là mã HTML của chương trình hiện tại:
# <existing_html>
# {html_old}
# </existing_html>

# nhiệm vụ:
# {request}

# QUY TẮC:
# - Trả về duy nhất mã HTML hoàn chỉnh.
# - Bắt đầu bằng <!DOCTYPE html>.
# - Kết thúc bằng </html>.
# - Không giải thích.
# - Không sử dụng Markdown.
# - Không đặt code trong ```html.
# """

# response = requests.post(
#     url,
#     headers={
#         "X-API-Key": os.environ["CODEX_API_TOKEN"]
#     },
#     json={
#         "model": "gpt-5.6-luna",
#         "prompt": prompt
#     },
# )

# print("Status:", response.status_code)

# response.raise_for_status()

# data = response.json()

# if not data.get("success"):
#     raise RuntimeError("Codex xử lý thất bại")

# html = data["result"].strip()

# # Xóa Markdown code fence nếu AI vẫn trả về
# html = re.sub(
#     r"^```(?:html)?\s*",
#     "",
#     html,
#     flags=re.IGNORECASE
# )
# html = re.sub(r"\s*```$", "", html)

# # Kiểm tra HTML cơ bản
# if not re.search(r"<!doctype html", html, re.IGNORECASE):
#     raise ValueError(
#         "AI không trả về HTML hoàn chỉnh:\n"
#         + html[:1000]
#     )

# # Lưu thành file HTML
# output = Path("ban_do_du_lieu_khu_vuc.html")
# output.write_text(html, encoding="utf-8")

# print(f"Đã tạo file: {output.resolve()}")