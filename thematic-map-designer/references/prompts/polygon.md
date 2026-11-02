# Prompt bản đồ Polygon — `choropleth`

Áp dụng cùng [prompt chung](common.md). Từ dữ liệu được cung cấp, TỰ PHÂN TÍCH và TỰ THIẾT KẾ bản đồ vùng tương tác toàn màn hình.

## 1. Phân tích và ghép vùng

- Xác định đối tượng mỗi dòng là quốc gia/lãnh thổ, tỉnh/thành, huyện hoặc một vùng có Polygon/MultiPolygon thực. Chọn đúng cấp mà chỉ số đo lường; cấp cha chỉ làm ngữ cảnh.
- Dùng GeoJSON được cấp; nếu chưa có, ghép mã/tên địa danh với ranh giới công khai đã xác minh khi được phép tra cứu. Không bắt buộc bảng Excel có cột tọa độ.
- Ưu tiên mã định danh ổn định; dùng tên thì kiểm thêm vùng cha, cấp địa lý và thời điểm ranh giới. Không ghép mơ hồ hoặc lấy vùng cha thay vùng con chưa tìm được.
- Đọc ghi chú/điều kiện trong cùng dòng để giữ đúng phạm vi áp dụng. Không tô toàn quốc gia khi quan sát chỉ áp dụng một vùng con.
- Điều kiện gắn với địa điểm phi diện tích có thể dùng marker đã định vị thật và ghi rõ ý nghĩa điều kiện; không coi marker là bằng chứng toàn vùng áp dụng. Giữ mọi phần của ranh giới, chỉ bỏ đảo/phần phụ khi nguồn xác định rõ phạm vi loại trừ.
- Giữ riêng đối tượng, kỳ và nhóm. Chỉ gộp các dòng cùng vùng khi ý nghĩa chỉ số cho phép; không tô chồng nhiều kỳ như các quan sát đồng thời.

## 2. Biểu diễn

- Tự chọn tô màu định lượng hoặc phân loại theo trường thực tế. Không lấy ID, mã vùng hoặc STT làm chỉ số.
- Với chỉ số định lượng, chọn thang màu và cách chia khoảng phù hợp phân bố; chỉ số có mốc trung tâm có ý nghĩa có thể dùng thang phân kỳ.
- Với nhóm phân loại, dùng màu phân biệt và nhãn từ giá trị thực tế. Nếu chỉ có geometry, hiển thị các vùng mà không tạo chỉ số giả.
- Phân biệt vùng thiếu dữ liệu với giá trị `0`; vùng không có quan sát không được nhận giá trị của vùng gần nhất.
- Ranh giới, độ trong suốt và hiệu ứng hover/selected phải giúp đọc vùng nhỏ, không che toàn bộ bản đồ nền.

## 3. Tương tác và chú giải

- Tự chọn tìm khu vực, lọc nhóm, chọn chỉ tiêu hoặc kỳ quan sát khi dữ liệu hỗ trợ; mọi điều khiển nằm trên bản đồ.
- Bắt sự kiện trên lớp `fill` của dữ liệu, hoặc hit-test bằng `queryRenderedFeatures` giới hạn đúng layer đã tồn tại. Toàn bộ phần tô của vùng phải bấm/chạm được, không chỉ đường viền hay nhãn; vùng thiếu giá trị vẫn mở tên vùng và trạng thái thiếu dữ liệu. Dùng khóa trong `feature.properties` để tra bản ghi; dùng `feature.id` chỉ khi đã bảo đảm khớp với khóa cấu hình nguồn.
- Có ba trạng thái rõ ràng: bình thường, hover và selected. Hover đổi con trỏ và nhấn nhẹ vùng; rời chuột chỉ xóa hover, không xóa selected. Selected có viền tương phản, dày khoảng 3–4 px, rõ trên cả vùng màu sáng/tối và nền bản đồ; có thể thêm viền sáng bên dưới. Giữ màu tô theo chỉ tiêu để vẫn đối chiếu được chú giải.
- Dựng lớp `line` riêng cho viền selected, nằm trên các lớp tô và viền vùng thông thường để không bị vùng lân cận che. Ưu tiên lọc theo khóa ổn định trong `properties`, ví dụ `map.setFilter('regions-selected', ['==', ['get', 'regionId'], selectedId])`; thuộc tính và ID layer trong ví dụ phải được thay bằng khóa thực tế. Viền phải đi theo geometry Polygon/MultiPolygon thật, gồm các phần rời, không vẽ hình chữ nhật bounds, vòng tròn hoặc marker thay ranh giới. Nếu dùng `feature-state` thì cấu hình ID theo prompt chung và áp lại state sau khi thay nguồn khi cần.
- Chọn kết quả tìm kiếm phải gọi cùng hàm chọn vùng như click: bỏ chọn vùng cũ, cập nhật khóa selected, cập nhật viền và popup, rồi `fitBounds` theo geometry với padding tránh các overlay và mức zoom hợp lý. Tìm tên hỗ trợ không dấu, không phân biệt hoa/thường; nhiều vùng trùng tên phải kèm vùng cha để chọn đúng, không tự lấy kết quả đầu khi còn mơ hồ. Không lọc ẩn toàn bộ các vùng còn lại chỉ để biểu thị tìm kiếm.
- Viền selected tồn tại sau khi chuột rời vùng, kéo/zoom hoặc đổi chỉ tiêu/kỳ nếu vùng vẫn còn trong dữ liệu đang xem. Chọn vùng khác phải chuyển viền và popup sang vùng đó. Đóng popup hoặc nút “Toàn vùng” xóa lựa chọn và viền đồng bộ; bộ lọc loại vùng đang chọn thì đóng popup và bỏ chọn.
- Khi đổi chỉ tiêu/kỳ, cập nhật màu vùng, chú giải, đơn vị và popup. Dùng cùng thang khi cần so sánh các kỳ; nếu tính lại theo bộ lọc thì thể hiện rõ phạm vi thang hiện tại.
- Popup dùng tên/mã vùng, chỉ tiêu, giá trị, đơn vị, kỳ và ghi chú thực tế. Hiển thị rõ ô thiếu dữ liệu.
- Báo gọn các vùng không khớp hoặc có tên mơ hồ trong overlay thu gọn, dựa trên kết quả ghép thực.

## 4. Kiểm tra tương tác trước khi trả kết quả

Nếu có trình duyệt, kiểm tra các hành vi dưới đây trên bản đồ đã tải dữ liệu; nếu không có thì rà soát luồng sự kiện, khóa và thứ tự layer trong mã, không coi kiểm tra cú pháp là đã kiểm chứng tương tác:

- Bấm phần trong của ít nhất hai vùng: mỗi lần mở đúng tên và số liệu của vùng đó, đồng thời chuyển viền selected; thử cả vùng có khóa chuỗi và ID `0` nếu dữ liệu có.
- Tìm rồi chọn một vùng: thấy đầy đủ ranh giới nổi bật, camera tới đúng vùng và popup trùng với khi bấm vùng đó. Các vùng lân cận vẫn hiển thị để đối chiếu.
- Rời chuột, kéo/zoom và đổi chỉ tiêu: viền vùng đã chọn còn rõ, popup và chú giải cập nhật đúng. Chọn vùng khác hoặc đóng popup không để lại viền cũ hay phát sinh thao tác đóng popup cũ xóa lựa chọn mới.
- Thử từ khóa không khớp, vùng thiếu giá trị/geometry và thao tác chạm trên màn hình hẹp: báo đúng trạng thái, không lỗi JS và overlay không chặn bản đồ ngoài phần panel.

Tạo bản đồ bằng lớp fill/line phù hợp của MapLibre. Đầu ra tuân thủ JSON ba file trong prompt chung.
