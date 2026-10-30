# Hợp đồng đầu vào và metadata

Các trường đầu ra dưới đây mô tả cấu hình nội bộ. Chỉ xuất cấu hình thành file khi caller yêu cầu `output_format=json`; mặc định dùng cấu hình để tạo ba file web theo `web-output.md`. Đầu vào web có thể thêm `records`/`geojson` để cung cấp dữ liệu thực; profile riêng không đủ để vẽ toàn bộ dữ liệu.

## Payload phân tích bảng

Ứng dụng gửi object gồm `profile` và `supportedCharts`. `supportedCharts` là object có key là loại bản đồ, mỗi loại có `slots` xác định các role được phép; định dạng nằm trong `../schemas/supported-charts.json`. Khi không có registry riêng, dùng registry đi kèm; dự án đích cần loại bỏ loại bản đồ chưa có renderer trước khi gọi AI.

`profile.rowCount` là số dòng; `profile.columns` là danh sách metadata cột. Mỗi cột có `name` nguyên văn, `inferredType` (`number`, `text`, `date`), `nullPct` (0–100), `uniqueCount`, `uniqueCountCapped`, `min`, `max`, `dateHint`, `temporalGranularity`, `commaDecimal`. Thống kê thiếu có thể được bỏ qua; thiếu thống kê không cho phép tự khẳng định độ phủ hay quan hệ chưa được quan sát.

`profile.samplesIncluded` cho biết có gửi giá trị dữ liệu hay không. Khi được phép gửi, profile có thể có:

- `columns[].samples`: một số giá trị của từng cột; các mẫu giữa hai cột không nhất thiết cùng dòng.
- `head`: các dòng đầu để đọc quan hệ cùng dòng; không đại diện cho mọi đối tượng.
- `columns[].distinctValues`: danh sách giá trị phân biệt đầy đủ nếu số lượng không quá 300; không coi danh sách bị cắt là đầy đủ.
- `columns[].categoryValues`: danh sách phân loại đầy đủ nếu không quá 12 nhóm.
- `scopeRows`: ngữ cảnh của các dòng có địa danh kèm giới hạn/phạm vi, kể cả ngoài head; `scopeRowsTruncated` báo bị cắt.
- `categoryGroups`: các nhóm gồm `entityField`, `categoryField`, `combinations`; mỗi tổ hợp có `values` và `entities`. Đây là bằng chứng gợi ý, vẫn phải kiểm tra grain và phạm vi thực tế.
- `columns[].countryRegions`: `matchedValueCount`, `valueCount`, `countryCount` và `regions` với `id`, `countryCount`; đếm quốc gia khác nhau, không phải số dòng/ngày.

Nếu `samplesIncluded: false`, ứng dụng bỏ toàn bộ các giá trị ở trên, kể cả giá trị gián tiếp trong categoryGroups và scopeRows. AI dùng metadata còn lại, giảm độ chắc chắn khi cần; không yêu cầu mở khóa dữ liệu mẫu để tiếp tục. Cờ này chỉ điều khiển dữ liệu gửi trong request phân tích.

Nếu nhận trực tiếp records qua công cụ agent, dùng parser/profile của môi trường để tạo hồ sơ tương đương từ dữ liệu được cấp. Không đọc file hay nguồn dữ liệu ngoài phạm vi được cung cấp. Luồng API mặc định nhận profile, không yêu cầu AI chép lại toàn bộ records.

## Geometry có sẵn

Ứng dụng parse GeoJSON và gửi properties đã profile cùng `profile.spatial`:

- `nativeGeometry: true`.
- `geometryKinds`: các giá trị `area`, `line`, `point`.
- `coordinateBindings`: `{lat, lng}` nếu ứng dụng đã trích tọa độ Point thành cột trong profile.

Area dùng `choropleth`, line dùng `map_line`. Với geometry area/line gốc, `bindings.region` và `value` có thể `null` khi không có thuộc tính phù hợp. Point dùng tên cột trong coordinateBindings; ứng dụng cần trích tọa độ trước khi phân tích nếu chưa có cột. Không bịa cột tên địa danh, ID hay tọa độ. Ứng dụng tách dữ liệu trộn loại geometry thành lớp riêng khi renderer yêu cầu.

Geometry giữ trong ứng dụng, không cần gửi toàn bộ cho AI. Tọa độ địa lý dùng độ với lat trong [-90, 90], lng trong [-180, 180]; GeoJSON lưu theo thứ tự [lng, lat]. Không coi tọa độ phẳng của hệ quy chiếu khác là kinh/vĩ độ; việc chuyển hệ cần metadata và code của ứng dụng.

## Đầu ra analysis

Các trường cấp gốc là `datasetTitle`, `grain`, `columns`, `suggestions`, `search_bar`, `search_fields`, `regionNavigation`, `popupContent`. Trả đủ trường theo schema, dùng `null` hoặc `[]` nơi không áp dụng.

`columns` chứa mỗi tên cột đầu vào đúng một lần. Với mỗi cột:

| Trường | Cách điền |
| --- | --- |
| `name` | Tên cột nguyên văn, kể cả dấu và khoảng trắng. |
| `role` | `geo`, `time`, `measure`, `category`, `id`, `text`, `ignore`. |
| `labelVi` | Nhãn tiếng Việt hoặc null; không thay name. |
| `geoLevel` | `country`, `admin1`, `admin2`, `point_lat`, `point_lng`, `h3` hoặc null. |
| `country` | Quốc gia ngữ cảnh khi thực sự cố định; null nếu khác nhau theo dòng hoặc chưa rõ. |
| `timeParse` | `iso`, `excel_serial`, `unix_s`, `unix_ms`, `text` hoặc null. |
| `granularity` | `day`, `week`, `month`, `quarter`, `year` hoặc null. |
| `unit` | Đơn vị gốc; null nếu không xác định được. Không chuyển đổi giá trị. |
| `unitSource` | `explicit` khi ghi rõ, `inferred` khi đủ ngữ cảnh, `unknown` khi unit null. |
| `aggDefault` | `sum`, `mean`, `min`, `max`, `count` hoặc null. |
| `semanticType` | Nhãn ngữ nghĩa ngắn cho measure khi có cơ sở; cột khác dùng null. |
| `legend` | Cấu hình chú giải của measure/category phù hợp; cột khác null. |

ID, STT, mã vùng và số thứ tự không phải measure dù toàn bộ giá trị là số. Tọa độ gán geo/point_lat hoặc point_lng. Tên chỉ số có từ chỉ thời gian không tự thành time. Kỳ thiếu năm dùng `timeParse: text`, không tự thêm năm hiện tại.

Số đo cộng dồn dùng sum khi grain cho phép; mean chỉ dùng khi trung bình không trọng số có ý nghĩa. Không cộng tỷ lệ, nhiệt độ, tốc độ hay số tồn kho qua nhiều kỳ theo thói quen. Tỷ lệ cần mẫu số/trọng số mà hợp đồng chưa hỗ trợ dùng aggDefault null; không tự chọn mean để lấp chỗ thiếu. Count đếm bản ghi, không thay cho chỉ số nghiệp vụ và không tạo cột count giả.

`suggestions[].bindings` luôn có đủ `region`, `value`, `lat`, `lng`, `x`, `y`, `series`, `source`, `target`, `sourceLat`, `sourceLng`, `targetLat`, `targetLng`, `time`, `group`. Slot không áp dụng trả null. `y` và `series` của bốn loại bản đồ mặc định đều null; không nhét cấu hình biểu đồ popup vào đây.
