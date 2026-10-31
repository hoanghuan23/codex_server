# Prompt bản đồ Line — `map_line`

Áp dụng cùng [prompt chung](common.md). Từ dữ liệu được cung cấp, TỰ PHÂN TÍCH và TỰ THIẾT KẾ bản đồ tuyến/hành trình tương tác toàn màn hình.

## 1. Chọn nguồn đường

- Nếu có LineString/MultiLineString, dùng geometry gốc, giữ đúng các đoạn và thuộc tính.
- Nếu có tên/mã tuyến, ghép với mạng đường/tuyến thực có nguồn khi được phép tra cứu; kiểm tra tên/mã, vùng cha và phạm vi. Không mặc định quốc gia từ ngôn ngữ giao diện.
- Nếu có chuỗi tọa độ, chỉ nối khi các dòng thực sự là các bước của một hành trình/đối tượng di chuyển. Nhiều điểm cố định hoặc nhiều kỳ quan sát không đủ để tạo tuyến.
- Dữ liệu đi–đến có lưu lượng thuộc Arc Flow khi cần thể hiện quan hệ có hướng; không tự biến hai đầu OD thành tuyến đường thực tế.

## 2. Dựng tuyến đúng quan hệ

- Với chuỗi tọa độ, nhóm theo chuyến/hành trình/đối tượng trước, rồi sắp theo thứ tự hoặc thời gian thực. Chỉ dùng thứ tự dòng khi dữ liệu thể hiện đó là thứ tự hành trình.
- Kiểm tra hệ tọa độ và `[lng, lat]`. Không chuyển tọa độ thiếu thành `0`; không nối khác nhóm hoặc bắc cầu qua tọa độ/thứ tự không hợp lệ. Giữ ngắt đoạn để phản ánh dữ liệu thiếu.
- Không tự chọn một thứ tự khi các mốc mâu thuẫn hoặc không đủ căn cứ; báo gọn phần tuyến không dựng được.
- Đường nối các tọa độ chỉ biểu diễn hành trình giữa các mốc. Chỉ mô tả là tuyến đường thực tế khi có geometry mạng đường xác minh được.
- Không gộp tuyến khác kỳ/nhóm hoặc cộng thuộc tính không có ý nghĩa cộng dồn.

## 3. Biểu diễn và tương tác

- Tự chọn màu theo tuyến/nhóm hoặc chỉ tiêu, độ rộng theo số đo khi có ý nghĩa; geometry không có số đo vẫn hiển thị được với kiểu đường cố định.
- Dùng tương phản, độ trong suốt và trạng thái hover/selected phù hợp để đọc các tuyến giao nhau. Có thể thêm điểm đầu/cuối khi tọa độ thật và giúp hiểu hành trình.
- Tự chọn tìm tuyến, lọc nhóm/kỳ, bật/tắt lớp hoặc chọn chỉ tiêu khi dữ liệu hỗ trợ; tất cả nằm trên bản đồ.
- Popup dùng tên/mã tuyến, nhóm/chuyến, kỳ và thuộc tính thật. Không tự tính hoặc gắn nhãn chiều dài, thời gian di chuyển hay tốc độ như số liệu gốc khi input không có.
- Chú giải phản ánh màu/độ rộng thực tế; đổi chỉ tiêu/lọc phải cập nhật đồng bộ. Báo gọn tuyến chưa khớp, đoạn thiếu hoặc dữ liệu sai từ kiểm tra thực.

Tạo bản đồ bằng lớp line phù hợp của MapLibre. Đầu ra tuân thủ JSON ba file trong prompt chung.
