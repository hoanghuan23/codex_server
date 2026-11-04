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
