# Đầu ra web

Skill trả DUY NHẤT một JSON object chứa chính xác ba khóa `index.html`, `style.css`, `app.js`; giá trị là toàn bộ nội dung file dưới dạng chuỗi JSON. Không Markdown hay giải thích. API nhận `output_format=web` hoặc bỏ trường này để dùng mặc định.

Để tạo bản đồ, dùng [prompt chung](prompts/common.md) cùng prompt Polygon, Point, Line hoặc Arc Flow 3D được chọn theo `SKILL.md`. Các prompt riêng chỉ bổ sung cách dựng lớp; toàn bộ bản đồ dùng chung một gói ba file.

- `index.html`: HTML hoàn chỉnh có DOCTYPE, `lang="vi"`, charset, viewport và title. Liên kết `./style.css` và `<script src="./app.js" defer></script>`; không nhúng CSS/JS hoặc event handler nội bộ.
- `style.css`: bản đồ toàn màn hình, các overlay responsive và trạng thái loading/empty/error.
- `app.js`: dữ liệu, logic bản đồ và tương tác. Dùng script thường tương thích thư viện được nạp, không cần npm/build hay upload lại dữ liệu.

Dùng MapLibre GL JS và nền OpenFreeMap style Liberty (`https://tiles.openfreemap.org/styles/liberty`, URL nguyên văn trong `app.js`); thêm renderer tương thích khi cần cung 3D. Ghim phiên bản thư viện, xử lý lỗi tài nguyên mạng; geometry đã có vẫn được hiển thị khi nền lỗi. Không phụ thuộc `fetch` file dữ liệu cục bộ ngoài ba file.

## Caller lưu và kiểm tra

Skill trả nội dung ba file cả trong môi trường chỉ đọc, không cần ghi file hoặc chạy validator ở server. Caller dùng `scripts/web_output.py` (`parse_web_files`) để đọc JSON và lưu ba file UTF-8 vào thư mục `output`; helper vẫn đọc được ba khối Markdown của phản hồi cũ.

Từ thư mục skill, caller kiểm tra bằng:

`python3 scripts/validate.py --result <output-directory>`

Bộ kiểm tra xác nhận đủ file, liên kết HTML/CSS/JS và cú pháp JS nếu có Node. Khi có công cụ trình duyệt, kiểm thêm bản đồ render, kéo/zoom, popup, bộ lọc và màn hình hẹp. Kiểm tra tĩnh không xác nhận dữ liệu ghép đúng hoặc tài nguyên mạng tải thành công.
