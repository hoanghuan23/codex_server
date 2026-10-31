# Dữ liệu đầu vào cho bản đồ web

Nhận dữ liệu hoặc đường dẫn file qua `input`. API gửi object; khi dùng trực tiếp skill có thể đọc bảng/Excel từ file được cấp. Đầu ra luôn là JSON mã nguồn ba file theo [web-output.md](web-output.md).

## Các dạng dữ liệu

- `records`: danh sách object, mỗi object là một dòng; giữ nguyên tên cột, kiểu, giá trị, đơn vị và kỳ quan sát.
- `geojson`: Feature/FeatureCollection hoặc geometry thực được cấp, gồm cả properties cần cho bản đồ. Metadata mô tả geometry không thay thế được geometry để vẽ.
- `sheets`: danh sách sheet Excel đã trích `{sheet, columns?, rows}`; `rows` có thể là object theo tên cột hoặc mảng ô theo thứ tự `columns`. Khi không có `columns`, giữ các hàng gốc gồm cả tiêu đề, ghi chú và hàng trống; xác định bảng theo nội dung, không mặc định hàng đầu luôn là tiêu đề. `source.sheetName` chỉ sheet dữ liệu chính; sheet khác cung cấp tọa độ/danh mục/ghi chú khi có khóa liên kết rõ ràng, không trở thành lớp độc lập. Không tự join khi chưa có khóa và quan hệ phù hợp. Caller cũ vẫn có thể gửi `records`.
- `text` trong mode `text_analysis`: toàn văn cần trích địa danh và số liệu theo [text-input.md](text-input.md).
- `layers`/`groups` trong mode `composition`: dữ liệu và ngữ cảnh từng lớp theo [composition.md](composition.md).

GeoJSON dùng WGS84 theo `[lng, lat]`; vĩ độ trong [-90, 90], kinh độ trong [-180, 180]. Tọa độ phẳng cần metadata để chuyển hệ, không tự coi là kinh/vĩ độ.

## Loại bản đồ và tùy chọn

`supportedCharts` là danh sách tên loại bản đồ, ví dụ:

```json
{"supportedCharts": ["choropleth", "point", "map_line", "arc_flow"]}
```

Bỏ trường này thì hỗ trợ cả bốn loại; danh sách con giới hạn các loại được dùng. Danh sách rỗng nghĩa là chưa hỗ trợ loại nào: hiển thị trạng thái phù hợp, không tự chuyển về mặc định. Danh sách chỉ chứa các tên trên, không cần slot, binding hoặc registry cấu hình.

`webOptions.layout` mặc định `"map-only"`; chỉ thay sang `"dashboard"` khi caller yêu cầu rõ. `webOptions.allowOnlineLookup` mặc định `true`; giá trị `false` tắt tra cứu và tự thêm tài nguyên mạng mới. `source` có thể ghi tên file, sheet, đơn vị hoặc ghi chú nguồn để dùng trên bản đồ.

## Profile tùy chọn

`profile` giúp hiểu dữ liệu, không bắt buộc khi đã có records/geometry hoặc văn bản đầy đủ. Các trường thường gặp:

- `rowCount`: số dòng; `columns`: metadata cột với `name`, `inferredType`, `nullPct`, `uniqueCount`, `uniqueCountCapped`, `min`, `max`, `commaDecimal` và gợi ý thời gian khi có.
- `columns[].samples`/`distinctValues`/`categoryValues`: mẫu hoặc tập giá trị từng cột. Mẫu của các cột không nhất thiết cùng dòng; không ghép chúng thành records.
- `head`: các dòng đầu đúng quan hệ cùng dòng. Nếu chỉ có head, bản đồ phải ghi rõ dữ liệu mẫu và không coi đó là toàn bộ tập dữ liệu.
- `samplesIncluded=false`: chỉ dùng metadata còn lại, không khôi phục giá trị bị ẩn hoặc lấy dữ liệu nghiệp vụ trên mạng thay thế.

Không khẳng định độ phủ, số dòng ghép đúng hoặc quan hệ giữa các cột từ thống kê thiếu. Chỉ có metadata mà không có dữ liệu đủ để vẽ thì tạo trạng thái thiếu dữ liệu trên bản đồ.
