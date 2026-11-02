# Tạo bản đồ từ file

Web local tối giản: chọn **một file** → **Tạo bản đồ** → mở bản đồ hoặc lấy ba file trong thư mục `output_*`. Không cần sửa tên file hay tên sheet trong script test. Giao diện không có ô prompt; chương trình tự phân tích rồi gọi prompt dựng bản đồ.

## Cài đặt

Yêu cầu Python 3.10 trở lên; server `/analyze` cần Codex CLI đã đăng nhập. Node.js là tùy chọn, dùng để kiểm tra cú pháp JavaScript trước khi công bố bản đồ.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Nếu chưa có `.env`, sao chép `.env.example` thành `.env`, rồi đặt `CODEX_API_TOKEN` trùng với token của server. Ứng dụng cũng đọc biến môi trường; không đưa token vào HTML/JS.

## Chạy

Terminal thứ nhất, chạy API hiện có:

```bash
source .venv/bin/activate
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Terminal thứ hai, chạy giao diện:

```bash
source .venv/bin/activate
python3 -m uvicorn ui_server:app --host 127.0.0.1 --port 8001 --reload
```

Mở **http://127.0.0.1:8001**, chọn file và nhấn **Tạo bản đồ**. Nếu đã có API chạy ở máy khác, đặt `CODEX_API_URL` tới `/analyze` của API đó; chỉ cần chạy terminal giao diện. Máy API cần có phiên bản skill trong repo này để hiểu `input.sheets` và mặc định nền Liberty.

Với Excel, chọn file sẽ hiển thị một danh sách **Chọn sheet**, chỉ gồm tên các sheet trong file. Chọn sheet muốn dùng rồi nhấn **Tạo bản đồ**.

Đọc tên sheet chạy local, chưa gọi AI. Sheet đã chọn được giữ làm dữ liệu chính trong cả hai bước AI; các sheet khác chỉ cung cấp tọa độ/danh mục/ngữ cảnh khi có khóa rõ ràng. Mở giao diện tại cổng **8001**; cổng 8000 là API phân tích. Nếu gặp “Not Found” khi đọc sheet, khởi động lại `ui_server` bằng lệnh trên rồi tải lại trang; `--reload` tự nạp thay đổi mã Python trong những lần chỉnh sửa sau.

Chạy một worker cho giao diện; hàng đợi/trạng thái nằm trong bộ nhớ của tiến trình. Mỗi lần chỉ chạy một tác vụ, không cần frontend framework hay bước build.

## Dữ liệu và kết quả

- `.geojson`, `.json`: chỉ chấp nhận GeoJSON hợp lệ, WGS84 theo `[lng, lat]`. Không tự chuyển hệ tọa độ.
- `.xlsx`: đọc tất cả sheet không rỗng, giữ hàng gốc gồm tiêu đề và ghi chú. UI cho chọn tên sheet trước khi chạy; caller cũ không gửi lựa chọn thì AI vẫn tự chọn sheet. Sheet tọa độ/danh mục chỉ hỗ trợ khi có khóa liên kết rõ ràng. Công thức dùng giá trị cache đã lưu trong Excel, không chạy tính toán lại.
- `.docx`: đọc văn bản và bảng theo thứ tự trong tài liệu; chưa hỗ trợ `.doc`, OCR hoặc nội dung chỉ có trong ảnh.
- `.txt`: UTF-8, hỗ trợ BOM. Chưa hỗ trợ `.xls` hoặc nhiều file/layer độc lập.

Lời gọi AI đầu trả `candidates`, `selectedChart`, `reason`, `missingData`, `selectedSheet`. Nếu không đủ dữ liệu để chọn loại, chương trình báo phần cần bổ sung. Lời gọi thứ hai dùng skill hiện có, giới hạn một loại chính: Polygon (`choropleth`), Point (`point`), Line (`map_line`) hoặc Arc Flow 3D (`arc_flow`).

Cho phép xác minh tọa độ, ranh giới và mạng tuyến từ nguồn địa lý công khai; không bổ sung số liệu nghiệp vụ từ Internet. Vị trí không xác minh được cần được báo trên bản đồ; không tự bịa dữ liệu. Mọi bản đồ dùng nền Liberty `https://tiles.openfreemap.org/styles/liberty`. Nền, thư viện CDN và tài nguyên địa lý công khai cần Internet.

Sau khi kiểm tra đủ ba file, liên kết HTML và cú pháp JS (nếu có Node), chương trình công bố:

```text
output_<ten_file>_<YYYYMMDD_HHMMSS>_<ma_tac_vu>/
├── index.html
├── style.css
└── app.js
```

Thời gian đặt tên thư mục theo Việt Nam. File tải lên và thư mục xây dựng tạm được dọn sau tác vụ. Dữ liệu nguồn được nhúng trong `app.js`; mở bằng nút **Mở bản đồ** để dùng HTTP thay vì `file://`.

Thư mục kết quả vẫn còn sau khi khởi động lại, nhưng V1 không lưu lịch sử hay khôi phục tác vụ đang chạy. Để xem kết quả cũ bằng HTTP, có thể chạy `python3 -m http.server 8080 --directory <thu_muc_output>` rồi mở http://127.0.0.1:8080.

| Cấu hình | Mặc định |
| --- | --- |
| `CODEX_API_URL` | `http://127.0.0.1:8000/analyze` |
| `CODEX_API_TOKEN` | Bắt buộc khi tạo tác vụ |
| `CODEX_MODEL` | `gpt-5.6-luna`; server truyền rõ model cho cả bước phân tích và dựng bản đồ |
| `CODEX_TIMEOUT` | 900 giây cho mỗi lời gọi AI |
| `MAP_OUTPUT_DIR` | Thư mục dự án |
| `MAP_MAX_UPLOAD_MB` | 10 MB; có thể tăng cho dữ liệu lớn |
| `SKILL_DIR` | `thematic-map-designer` trong dự án |

Đổi model bằng `CODEX_MODEL` trong môi trường hoặc `.env` trên máy chạy API `/analyze`, rồi khởi động lại API. Cấu hình này được truyền qua `codex exec --model`, ưu tiên hơn model mặc định của Codex CLI.

## API giao diện

- `POST /api/excel/sheets`: multipart `file` (`.xlsx`), chỉ trả tên sheet dạng `{"sheets":["Tên sheet 1","Tên sheet 2"]}`. Không trích dữ liệu hoặc gọi AI.
- `POST /api/jobs`: multipart với trường `file`, trả HTTP 202 và `{job_id}`. Excel có thể gửi thêm `selected_sheet`; server kiểm tra và đặt `input.source.sheetName` để giữ sheet người dùng chọn. Bỏ trường này để dùng luồng tự chọn cũ. Trả 409 khi có tác vụ đang chạy, kèm `detail.job_id` để tiếp tục theo dõi.
- `GET /api/jobs/{job_id}`: trả `status`, `message`, `analysis`, `error`, `output_dir`, `preview_url`. Trạng thái: `reading`, `analyzing`, `generating`, `validating`, `completed`, `needs_data`, `failed`.
- `GET /outputs/{job_id}/{filename}`: chỉ phục vụ `index.html`, `style.css`, `app.js` của tác vụ hoàn tất trong phiên hiện tại.

Token và giao tiếp tới `/analyze` do Python xử lý. API `/analyze` cùng các script test cũ giữ nguyên hợp đồng.

## Kiểm thử

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Các kiểm thử tự động dùng API giả lập, không tiêu thụ lượt gọi AI. Kiểm tra tĩnh không thay thế việc kiểm tra dữ liệu địa lý, tải nền, popup và cung 3D trên trình duyệt với đầu ra AI thực.
