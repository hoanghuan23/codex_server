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
- Khi đổi chỉ tiêu/kỳ, cập nhật màu vùng, chú giải, đơn vị và popup. Dùng cùng thang khi cần so sánh các kỳ; nếu tính lại theo bộ lọc thì thể hiện rõ phạm vi thang hiện tại.
- Popup dùng tên/mã vùng, chỉ tiêu, giá trị, đơn vị, kỳ và ghi chú thực tế. Hiển thị rõ ô thiếu dữ liệu.
- Báo gọn các vùng không khớp hoặc có tên mơ hồ trong overlay thu gọn, dựa trên kết quả ghép thực.

Tạo bản đồ bằng lớp fill/line phù hợp của MapLibre. Đầu ra tuân thủ JSON ba file trong prompt chung.
