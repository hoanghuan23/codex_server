---
name: thematic-map-designer
description: "Tạo bản đồ web tương tác toàn màn hình từ Excel, bảng, GeoJSON, văn bản hoặc nhiều lớp dữ liệu. Hỗ trợ Polygon, Point, Line và Arc Flow 3D bằng MapLibre GL JS. Không dùng cho bản đồ minh họa dạng ảnh."
---

# Prompt thiết kế bản đồ

Đọc `input` được cung cấp dưới dạng dữ liệu hoặc đường dẫn file. Mặc định `mode=analysis`. Tự thiết kế bản đồ và trả duy nhất JSON mã nguồn ba file `index.html`, `style.css`, `app.js`, theo cách dùng prompt của `test_excel_ai_map.py`. Các prompt bên dưới tự chứa hướng dẫn; không cần đọc file Python đó khi chạy skill. API chỉ hỗ trợ `output_format=web`.

## Chọn và kết hợp prompt web

1. Đọc và áp dụng [prompt chung](references/prompts/common.md) cho mọi bản đồ web.
2. Xác định mỗi dòng là vùng, đối tượng cố định, tuyến/hành trình hay luồng đi–đến. `supportedCharts` là danh sách tên loại được caller hỗ trợ, ví dụ `["choropleth", "point"]`; bỏ trường này thì hỗ trợ cả bốn loại, `[]` nghĩa là chưa hỗ trợ loại nào. Nếu người dùng đã chọn loại bản đồ, dùng prompt tương ứng và kiểm tra dữ liệu cần thiết; thiếu dữ liệu hoặc caller không hỗ trợ thì báo gọn trên bản đồ, không dựng giả để đáp ứng loại đã chọn.
3. Nếu chưa chọn, tự chọn trong các loại được hỗ trợ theo bảng dưới. Đọc prompt của loại đã chọn, không nạp mọi prompt hay tạo cấu hình trung gian.
4. Áp dụng prompt chung cùng prompt riêng để tạo sản phẩm cuối. Khi dữ liệu cần nhiều lớp, đọc prompt của từng loại lớp được dùng và kết hợp trên cùng bản đồ; không tạo nhiều gói đầu ra hoặc phần giải thích prompt.

| Loại bản đồ | Chọn khi | Prompt riêng |
| --- | --- | --- |
| Polygon — `choropleth` | Dữ liệu theo vùng địa lý hoặc có Polygon/MultiPolygon. Không bắt buộc có tọa độ trong bảng. | [polygon.md](references/prompts/polygon.md) |
| Point — `point` | Đối tượng có vị trí riêng, từ tọa độ/Point hoặc địa danh có thể xác minh. Đối tượng cố định qua nhiều kỳ vẫn là điểm. | [point.md](references/prompts/point.md) |
| Line — `map_line` | Có LineString/MultiLineString, mã/tên tuyến ghép được với mạng đường thật, hoặc chuỗi tọa độ mang ý nghĩa hành trình. | [line.md](references/prompts/line.md) |
| Arc Flow 3D — `arc_flow` | Mỗi dòng mô tả quan hệ có hướng giữa hai vị trí độc lập và có lưu lượng. | [arc-flow.md](references/prompts/arc-flow.md) |

Không chọn Line chỉ vì có nhiều tọa độ/ngày; không chọn Arc Flow chỉ vì có geometry tuyến. Nếu không có loại nào đủ căn cứ, hiển thị trạng thái thiếu dữ liệu theo prompt chung.

## Đọc đầu vào

- `analysis`: dùng `records`/GeoJSON thực hoặc `sheets` chứa các sheet Excel đã trích thành `{sheet, columns?, rows}`. Nếu không có `columns`, `rows` là các hàng gốc, gồm cả tiêu đề/ghi chú; xác định tiêu đề theo nội dung, không mặc định hàng đầu luôn là bảng dữ liệu. `source.sheetName` chỉ sheet chính đã được caller chọn; các sheet còn lại chỉ làm tham chiếu tọa độ/danh mục/ghi chú khi có khóa liên kết rõ ràng, không dựng thêm lớp độc lập từ chúng. Dùng tên sheet và ghi chú được cấp để hiểu đơn vị, nhóm và phạm vi; không mặc định tên file, tên sheet hay bộ dữ liệu mẫu cụ thể.
- `profile` là metadata để hiểu cột. Không ghép samples riêng từng cột thành bản ghi. Chỉ có `profile.head` thì ghi rõ dữ liệu mẫu; `profile.samplesIncluded=false` thì chỉ dùng metadata, không khôi phục dữ liệu bị ẩn hoặc vẽ dữ liệu giả.
- `text_analysis`: đọc [references/text-input.md](references/text-input.md), trích đúng địa danh, giá trị, chỉ tiêu, đơn vị và kỳ từ toàn văn `text` rồi chọn prompt bản đồ. Không tự bổ sung số còn thiếu; phân biệt năm dữ liệu và năm công bố.
- `composition`: đọc [references/composition.md](references/composition.md), dùng `layers`/`groups` được cấp để kết hợp các lớp có ý nghĩa xem chung. Áp dụng prompt riêng cho từng loại lớp; chỉ ghép thuộc tính khi có khóa và quan hệ phù hợp. Lớp chỉ có metadata phải báo chưa đủ dữ liệu để vẽ.

Khi vẽ nhiều lớp, giữ mỗi ID đúng một lần, sắp từ dưới lên: vùng/lưới → đường/cung → điểm/nhãn; thiếu căn cứ thì giữ thứ tự đầu vào trong cùng nhóm, không suy geometry từ tên file.

## Nguồn ranh giới hành chính

Ưu tiên geometry được cấp trong input. Nếu cần bổ sung ranh giới tỉnh/thành phố hoặc cấp hành chính khác, dùng kho `../administrative_division/` tính từ thư mục chứa `SKILL.md`, theo mẫu `<ALPHA3>/<ALPHA3>_ADM<level>.geojson`. Không tính đường dẫn từ working directory vì caller có thể chạy trong thư mục tạm. Đọc mục kho cục bộ trong [references/online-geography.md](references/online-geography.md) để chọn quốc gia, cấp và ghép vùng. Chỉ tra mạng cho phần không có ranh giới cục bộ phù hợp; đủ dữ liệu trong kho thì không tra cứu lại. `webOptions.allowOnlineLookup=false` vẫn cho phép đọc kho cục bộ, nhưng không được dùng mạng để bù phần thiếu.

## Tài liệu dùng khi cần

- Cần hiểu cấu trúc records, sheet Excel, GeoJSON, profile hoặc tùy chọn caller: [references/input-contract.md](references/input-contract.md).
- Cần popup có ảnh/biểu đồ, nhiều chỉ tiêu hoặc chú giải phức tạp: [references/presentation.md](references/presentation.md).
- Cần bổ sung hoặc ghép ranh giới, tọa độ, mạng tuyến: [references/online-geography.md](references/online-geography.md). Ranh giới hành chính ưu tiên kho `administrative_division` trước mạng; với `webOptions.allowOnlineLookup=false`, chỉ dùng tài nguyên được cấp hoặc cục bộ.
- Cần lưu hoặc kiểm tra JSON mã nguồn ba file ở caller: [references/web-output.md](references/web-output.md). Môi trường chỉ đọc vẫn trả JSON mã nguồn như bình thường.
