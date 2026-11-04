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

Biến môi trường của tiến trình được ưu tiên hơn `.env`. Khởi động lại server sau khi đổi cấu hình.

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

`GET /templates` yêu cầu header `X-API-Key` và trả các theme cùng `styles`, `typography` từ file cấu hình:

```text
templates/
  config.json
  vnexpress-light/
    typography.json
    light.json
  vnexpress-dark/
    typography.json
    dark.json
```

`config.json` khai báo `defaultTemplate`, `defaultTheme` và danh sách `templates`; mỗi template có `name`, `path`, `themes`. Loader đọc `typography.json` dùng chung và `<theme>.json` tương ứng, không cần `manifest.json`.

VnExpress được tách thành hai template có ID `vnexpress-light` (theme `light`) và `vnexpress-dark` (theme `dark`), mỗi thư mục có `typography.json` riêng để chỉnh font độc lập. Template mặc định là `vnexpress-light`, theme mặc định là `light`. Client dùng hai ID mới khi chọn template.

Thư mục `templates/` hiện được bỏ qua trong Git, nên cần sao chép các file này khi triển khai. Sau khi cập nhật mã Python, dừng tiến trình Uvicorn cũ và chạy lại bằng lệnh ở trên. Nếu vẫn gặp lỗi tìm `manifest.json`, kiểm tra đường dẫn mã trong traceback và thư mục chạy server để xác định bản cũ đang được nạp.

## Kiểm thử

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m unittest discover -s tests -v
```

Kiểm thử dùng Codex giả lập, không gọi AI thật.
