# Codex Server

API FastAPI nhận prompt, gọi Codex CLI và trả kết quả văn bản.

## Cài đặt

Yêu cầu Python 3.10 trở lên và Codex CLI đã cài đặt, đăng nhập trên máy chạy server.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Đặt `CODEX_API_TOKEN` trong `.env` trước khi chạy. Nếu đã có `.env`, giữ file hiện tại và cập nhật khi cần.

| Biến môi trường | Ý nghĩa | Mặc định |
| --- | --- | --- |
| `CODEX_API_TOKEN` | Token xác thực cho API | Bắt buộc |
| `CODEX_CLI_PATH` | Đường dẫn đầy đủ tới CLI dùng để chạy yêu cầu | Tự tìm trong `PATH` |

Biến môi trường của tiến trình được ưu tiên hơn `.env`. Khởi động lại server sau khi đổi cấu hình.

Trên Windows, server mặc định chỉ dùng `codex.cmd` của bản cài qua npm; không tự chuyển sang `codex.exe`. Nếu Uvicorn không tìm thấy CLI, đặt `CODEX_CLI_PATH` trong `.env` thành đường dẫn đầy đủ tới `codex.cmd` rồi khởi động lại server. Kiểm tra đăng nhập trong cùng môi trường chạy server bằng `codex.cmd login status`; nếu báo chưa đăng nhập, chạy `codex.cmd login` tại đó.

## Chạy server

```bash
source .venv/bin/activate
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Tài liệu API: http://127.0.0.1:8000/docs.

Nếu cần mở tunnel bằng Cloudflare:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

## Gọi API

Gửi `POST /analyze` với header `X-API-Key` trùng `CODEX_API_TOKEN` và JSON có `prompt`, `model` là các chuỗi không rỗng. Server truyền nguyên giá trị `model` do client gửi cho Codex CLI, không tự chọn model hay dùng model mặc định. Thiếu `model` trả HTTP 422.

`/analyze` không chọn template mặc định. Trường `template` là tùy chọn, mặc định `null` và hiện không tham gia xử lý prompt.

```bash
curl http://127.0.0.1:8000/analyze \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-your-api-token' \
  -d '{"prompt":"Xin chào, bạn là ai?","model":"your-model-id"}'
```

Phản hồi thành công:

```json
{"success": true, "result": "Nội dung trả về từ Codex"}
```

Token sai hoặc thiếu trả HTTP 401; nội dung yêu cầu không hợp lệ trả HTTP 422; Codex kết thúc với lỗi trả HTTP 500.

Mỗi yêu cầu chạy Codex trong thư mục tạm riêng, dùng sandbox `read-only` và bật tìm kiếm web. Prompt được truyền qua stdin để hỗ trợ nội dung lớn. Thư mục tạm được dọn sau khi xử lý.

## Template

`GET /templates` yêu cầu header `X-API-Key` và trả danh sách mẫu. Gọi `GET /templates/mau_01` với cùng header để lấy nội dung ba file `html`, `css`, `js`:

```text
templates/
  config.json
  mau_01/
    index.html
    style.css
    app.js
```

`config.json` khai báo `defaultTemplate` và danh sách `templates`; mỗi mẫu có `name` và `path`. ID mặc định là `mau_01`. Loader chỉ đọc `index.html`, `style.css` và `app.js` trong thư mục mẫu, không dùng theme hay typography.

Sau khi cập nhật mã Python, dừng tiến trình Uvicorn cũ và chạy lại bằng lệnh ở trên để nạp API mới.

## Kiểm thử

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Kiểm thử dùng Codex giả lập, không gọi AI thật.

## Endpoint sinh nội dung chung

`POST /generate` dùng chung cho HTML, nội dung video và các yêu cầu sinh nội dung
khác. Endpoint này thay thế `/generate-html` và `/generate-video`; client cần đổi
URL gọi API sang `http://127.0.0.1:8000/generate`. Hai URL cũ đã được gỡ bỏ.

Request nhận JSON `{"prompt":"...","model":"your-model-id"}` và header
`X-API-Key` như `/analyze`. Client gửi đầy đủ yêu cầu, ngữ cảnh và định dạng kết quả
mong muốn trong `prompt`. Endpoint không nhận trường `template` và không tải
các template bản đồ. `/analyze` và `/templates` vẫn hoạt động như cũ.

Ví dụ sinh HTML:

```bash
curl http://127.0.0.1:8000/generate \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-your-api-token' \
  -d '{"prompt":"Sinh một trang HTML hoàn chỉnh có bộ đếm và nút tăng/giảm bằng JavaScript. Nhúng CSS và JavaScript trong HTML. Chỉ trả mã HTML, không bọc Markdown, không giải thích.","model":"your-model-id"}'
```

Phản hồi JSON:

```json
{"success":true,"result":"<!DOCTYPE html><html>...</html>"}
```

`result` là văn bản Codex trả về, không được kiểm tra hay chuyển đổi định dạng.
Với HTML, client có thể dùng `srcdoc` của iframe có `sandbox="allow-scripts"`
để preview tương tác; API không lưu hay tạo URL lưu trữ trang. Với video, client
truyền prompt và ngữ cảnh video, rồi dùng HyperFrames trong dự án client để
preview/render; server không tự render MP4.

Token sai hoặc thiếu trả HTTP 401; thiếu `prompt`/`model`, chuỗi rỗng hoặc trường
không hỗ trợ trả HTTP 422; Codex chạy lỗi trả HTTP 500; không khởi chạy được CLI
trả HTTP 503. Khởi động lại Uvicorn sau khi cập nhật để nạp endpoint mới.
