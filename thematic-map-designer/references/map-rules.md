# Chọn bản đồ và ghép cột

Các tên trường trong tài liệu là cấu hình nội bộ. Với đầu ra web mặc định, triển khai các quyết định này trong `app.js`; chỉ trả cấu hình JSON khi `output_format=json`.

## Quyết định theo grain

Xác định mỗi dòng mô tả một vùng, đối tượng cố định, đoạn đường, bước trong hành trình hay luồng có hướng. Một đối tượng xuất hiện qua nhiều kỳ vẫn là một đối tượng. Không suy ra tuyến chỉ vì bảng có nhiều tọa độ hoặc nhiều ngày.

Chọn cấp địa lý mà chỉ số thực sự đo lường, không chỉ cột đầu tiên hay cột có nhiều giá trị nhất. Với quan sát cấp vùng con, dùng vùng con làm region, cấp cha làm ngữ cảnh. Không hạ cấp chỉ số tổng của vùng cha xuống các địa chỉ mô tả. Cột quốc gia thay đổi theo dòng thì country của vùng con là null; ứng dụng dùng cột quốc gia trên cùng dòng để phân giải.

Mỗi chartType tối đa một suggestion; `id` không trùng, confidence 0–1 và xếp giảm dần. `title` tương ứng là `Bản đồ Polygon`, `Bản đồ Line`, `Bản đồ Point`, `Bản đồ Arc Flow 3D`. `reason` giải thích lựa chọn theo grain và bằng chứng. Không có lựa chọn có cơ sở thì suggestions rỗng.

## Bốn loại bản đồ

| chartType | Điều kiện | Binding |
| --- | --- | --- |
| `choropleth` | Quan sát theo quốc gia, admin1, admin2 hoặc geometry area có sẵn. Không cần bảng có tọa độ. | `region`: cột geo đúng cấp, trừ geometry gốc cho phép null. `value`: measure hoặc category phù hợp, có thể null. |
| `point` | Các đối tượng có tọa độ riêng; đối tượng cố định qua nhiều kỳ vẫn dùng Point. | `lat`, `lng` bắt buộc là cột thật; `region` ưu tiên ID ổn định, nếu không có dùng cột tên/định danh phù hợp hoặc null. |
| `map_line` | Geometry line gốc, tuyến có tên/mã để ghép mạng đường, hoặc chuỗi tọa độ có ý nghĩa hành trình. | Chọn nhánh Line bên dưới. |
| `arc_flow` | Một dòng là luồng có hướng từ điểm đi tới điểm đến, đủ hai định danh, hai cặp tọa độ độc lập và lưu lượng. | `source`, `target`, `sourceLat`, `sourceLng`, `targetLat`, `targetLng`, `value`; thêm `time`, `group` khi có. |

Geometry không bắt buộc có measure mới được hiển thị. Với Polygon/Line không có measure/category phù hợp, để value/agg/legend null và metricButtons rỗng. Không tạo chỉ số từ mã hoặc số dòng để đủ điều kiện vẽ. Nếu đã chọn chỉ số nhưng một dòng có null, giữ đó là dữ liệu thiếu, không chuyển thành số 0.

### Các nhánh Line

- Geometry gốc: dùng đúng tuyến đã được cấp; region có thể null; value tùy chọn.
- Tên/mã tuyến: region là cột tên/mã tuyến, role category/geo/text/id; lat/lng/x null. Ứng dụng cần nguồn mạng đường và ngữ cảnh địa lý để ghép chính xác. Không mặc định quốc gia hay tự tìm tọa độ qua AI.
- Chuỗi tọa độ: lat/lng là cột tọa độ; region là nhóm hành trình/đối tượng di chuyển nếu có; x là thứ tự/thời gian nếu có, nếu không thì thứ tự dòng. Không nối khác nhóm; tọa độ hoặc thứ tự không hợp lệ làm ngắt đường. Các điểm cửa hàng cố định qua nhiều tháng không tự trở thành hành trình.

Có thể đề xuất cả Point và Line khi hai góc nhìn đều có ý nghĩa từ dữ liệu. Đường nối tọa độ không được mô tả là tuyến đường thực tế nếu không có geometry mạng đường.

### Arc Flow

Bảy binding bắt buộc là bảy cột khác nhau. source/target có role id/category/text/geo; các cột tọa độ có role geo với point_lat/point_lng hoặc measure khi metadata thực sự yêu cầu; value có role measure và không phải tọa độ, ID hoặc nhóm lưu lượng. time có role time; group là cột phân nhóm thật. Không dùng một cặp tọa độ cho cả hai đầu, không suy ra OD từ geometry tuyến, không tự join sheet hoặc geocode điểm còn thiếu.

Phép gộp theo ý nghĩa lưu lượng; chưa rõ dùng null. Giữ hai chiều độc lập, không gộp hai địa điểm cùng tên nhưng khác tọa độ. Ứng dụng kiểm tra dòng hợp lệ, tọa độ, lưu lượng không âm và hai đầu không trùng vị trí; ngưỡng khả dụng mặc định là 70% dòng hợp lệ, cần phép gộp khi OD lặp. AI không khẳng định tỷ lệ hợp lệ nếu profile chưa cung cấp.

Trong hợp đồng này Arc Flow chỉ đề xuất popup `info`, metricButtons [], suggestion.legend null, geographicScopes []. Phân vị, màu, chuyển động, chiều cao cung và Top N do code của renderer xử lý; không trả các ngưỡng hoặc tùy chọn này ngoài schema.

## Phạm vi địa lý thực sự

Đọc địa danh cùng điều kiện/ghi chú trong cùng dòng và các dòng ngoài head được cung cấp. Không bỏ hậu tố hoặc điều kiện giới hạn để tô toàn quốc gia. Cùng mã quốc gia chưa chắc cùng vùng áp dụng. Không suy ra ranh giới hành chính hoặc thay đổi lịch sử địa giới từ kiến thức ngoài dữ liệu; ứng dụng phân giải nguồn và thời điểm ranh giới.

Chỉ choropleth dùng `geographicScopes`; loại khác trả []. Mỗi ngoại lệ giữ `sourceValue` nguyên văn của region, tối đa một mục cho mỗi giá trị, gồm:

- `render: boundary` nếu có vùng xác định: targetName là vùng thực sự cần tra, geoLevel đúng cấp, country là quốc gia cha hoặc null khi thay đổi theo dòng. Không tìm được vùng con thì không tô quốc gia cha thay thế.
- `render: marker` cho điều kiện phi diện tích có địa danh làm mốc. Ký hiệu chỉ minh họa điều kiện, không khẳng định toàn vùng áp dụng. Không bịa vị trí cửa khẩu/sân bay. label ngắn, không thêm hậu tố “lớp riêng”; ứng dụng xử lý cách trình bày.
- `render: unresolved` nếu chưa xác định được địa danh/phạm vi, targetName và geoLevel null; giữ thông tin để ứng dụng báo chưa phân giải.

`geometryPart: all` là mặc định; chỉ dùng largest khi nguồn nói rõ đảo/khối đất chính và loại trừ các phần khác của địa giới. Mọi mục đều có label và reason. Marker/vùng con khác nhau không phải tổ hợp category của cả quốc gia, kể cả categoryGroups nhóm cùng mã cha.

## Tìm kiếm và điều hướng khu vực

`search_bar` dựa vào lợi ích tìm đối tượng, số đối tượng khác nhau và độ phân tán; không dùng số ngày, số dòng hay ngưỡng đếm cố định. `search_fields` ưu tiên tên định danh chính, sau đó ngữ cảnh giúp phân biệt; chỉ dùng mã khi thiếu tên. Loại measure, time, tọa độ, metadata nội bộ khỏi tìm kiếm. Không có cột đáng tin cậy thì false và []. False vẫn có thể kèm các trường hợp lệ nếu chưa nên bật mặc định.

`regionNavigation` chỉ dùng khi có cột quốc gia đáng tin cậy và bộ lọc khu vực hữu ích; cột đó gán geo/country. Trả countryField và các ID region/subregion hợp lệ trong schema, ưu tiên tiểu vùng có dữ liệu trước châu lục. Dựa vào countryRegions nếu có; không coi tỉnh/thành là quốc gia. Thiếu cơ sở hoặc ứng dụng không hỗ trợ thì null. Tìm kiếm và điều hướng không cần gọi AI lại khi người dùng thao tác.
