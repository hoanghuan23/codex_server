# Đầu ra web: HTML, JavaScript, CSS

Áp dụng khi `output_format=web` hoặc caller không chỉ định định dạng. Sản phẩm là ba file UTF-8 cùng thư mục:

- `index.html`: HTML hoàn chỉnh có DOCTYPE, `lang="vi"`, charset, viewport, tiêu đề và nội dung trang. Liên kết `./style.css` và `<script src="./app.js" defer></script>`.
- `style.css`: toàn bộ CSS của ứng dụng, bố cục responsive và trạng thái loading/empty/error có thể đọc được.
- `app.js`: dữ liệu được cấp, cấu hình và logic tương tác. Dùng script thường để có thể mở file HTML trực tiếp; không yêu cầu npm/build hay upload lại dữ liệu đã được cấp.

Không nhúng logic JavaScript, event handler hoặc khối CSS trực tiếp trong HTML. Dữ liệu và cấu hình có thể là object/array JavaScript trong `app.js`; đó không phải lý do xuất thêm file JSON. Không để TODO, mã giả hoặc điều khiển không hoạt động.

## Dữ liệu để vẽ

`profile` chứa metadata, không thay cho dữ liệu đầy đủ. Payload có thể thêm `records` (mảng object theo tên cột gốc) và `geojson` (Feature/FeatureCollection với geometry thật). Với nhiều lớp, mỗi lớp có thể có records/geojson riêng. Chỉ nhúng dữ liệu caller cấp và cho phép sử dụng.

Nếu chỉ có `profile.head`, có thể hiển thị bảng mẫu với nhãn rõ số dòng mẫu; không tuyên bố đó là toàn bộ dữ liệu. Các `columns[].samples`/distinctValues không có quan hệ cùng dòng nên không được ghép thành records. Với `samplesIncluded: false`, bỏ qua cả head/records nếu payload vô tình còn chứa chúng. Với văn bản, dùng các quan sát được trích theo `text-input.md`.

Tọa độ hợp lệ hoặc GeoJSON được cấp cho phép vẽ trực tiếp. Chỉ có địa danh mà thiếu geometry/nguồn ghép đã được cấp: hiển thị dữ liệu trong bảng và thông báo chưa có ranh giới/tọa độ; không geocode theo trí nhớ hoặc lấy tâm quốc gia để thay cho vùng con. Geometry được biết là tồn tại ở ứng dụng nhưng không có trong input cũng chưa đủ để vẽ trang độc lập.

Nếu có thư viện bản đồ/tài nguyên được caller cung cấp, ưu tiên dùng đúng thư viện và nguồn đó. Không tự thêm dịch vụ bên ngoài hoặc URL dữ liệu địa lý. Nếu không có thư viện mà đã có geometry/tọa độ hợp lệ, có thể dùng SVG/canvas trong trang làm bản đồ tương tác không nền; phải giữ hình học và phạm vi dữ liệu thật. Việc không dùng mạng khi tạo file không ngăn trình duyệt nạp tài nguyên mà caller đã chỉ định, nhưng phải có trạng thái lỗi khi không tải được.

## Hành vi giao diện

Triển khai chú giải, popup, lọc/tìm kiếm, chuyển chỉ số và điều khiển lớp khi có ý nghĩa theo dữ liệu. Thao tác dùng dữ liệu trong JS, không gọi AI lại. Thay chỉ số phải cập nhật cả biểu diễn và chú giải; không tự thêm phép gộp khi chưa biết ngữ nghĩa. Có trạng thái khi không có kết quả hoặc chưa đủ geometry; không tính số dòng thành số đối tượng nếu grain khác nhau.

Hiển thị chuỗi dữ liệu bằng `textContent` hoặc DOM tương đương. Không đưa trực tiếp dữ liệu vào `innerHTML`, `eval` hay event handler. URL ảnh/liên kết chỉ dùng HTTP/HTTPS hợp lệ, không chạy nội dung của ô như mã. Giữ số 0, null, đơn vị, phạm vi quan sát và quy tắc popup trong các tài liệu mode.

## Khi không ghi file trực tiếp được

Trả đúng ba khối sau, thay phần mô tả bằng **toàn bộ mã nguồn**, không có JSON bao ngoài hay lời giải thích. Dòng mở khối dùng chính xác tên file; dấu đóng khối nằm riêng một dòng. Nếu cần dấu backtick trong mã, không đặt riêng một dòng có đúng ba backtick.

````text
```html filename=index.html
<!DOCTYPE html>
... toàn bộ HTML ...
```
```javascript filename=app.js
... toàn bộ JavaScript ...
```
```css filename=style.css
... toàn bộ CSS ...
```
````

Caller dùng `scripts/web_output.py` (`parse_file_blocks`) để tách và lưu ba file. Không trả `OK <path>` khi chưa ghi được file. Nếu ghi được trực tiếp, không cần dán mã vào chat.

## Kiểm tra

Từ thư mục skill, chạy `python3 scripts/validate.py --format web --mode <mode> --input <input> --result <output-directory>`; đặt đường dẫn có khoảng trắng trong dấu nháy.

Bộ kiểm tra yêu cầu đủ ba file, HTML nối đúng CSS/JS, không có mã nhúng hoặc file phụ bị thiếu; kiểm cú pháp JS bằng Node nếu đã cài. Nó không xác minh ý nghĩa dữ liệu, đúng phép gộp, CSS trong trình duyệt, tỷ lệ ghép geometry hay tài nguyên mạng. Có công cụ trình duyệt thì kiểm thêm trang thật và các thao tác chính; không nói đã kiểm trình duyệt nếu chỉ chạy validator.
