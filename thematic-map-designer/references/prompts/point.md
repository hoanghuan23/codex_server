# Prompt bản đồ Point — `point`

Áp dụng cùng [prompt chung](common.md). Từ dữ liệu được cung cấp, TỰ PHÂN TÍCH và TỰ THIẾT KẾ bản đồ điểm tương tác toàn màn hình.

## 1. Phân tích và xác định vị trí

- Xác định mỗi điểm là đối tượng nào: cơ sở, trạm, cửa hàng, sự kiện hoặc địa điểm khác. Dùng ID ổn định để phân biệt các đối tượng trùng tên.
- Ưu tiên tọa độ hoặc Point/MultiPoint thực được cấp. GeoJSON dùng thứ tự `[lng, lat]`; kiểm tra kinh độ trong [-180, 180], vĩ độ trong [-90, 90] và hệ tọa độ.
- Tọa độ thiếu, không phải số hoặc sai phạm vi không trở thành `0`. Tọa độ bằng `0` vẫn hợp lệ khi đúng vị trí; không dùng phép kiểm tra truthy để loại số 0.
- Nếu chỉ có địa danh/địa chỉ, tra nguồn công khai khi được phép và xác minh đúng địa điểm, vùng cha và độ chi tiết. Không đặt điểm ngẫu nhiên hoặc dùng tâm vùng để giả tọa độ chính xác của cơ sở.
- Một đối tượng cố định xuất hiện qua nhiều kỳ vẫn là điểm. Dùng kỳ để lọc/cập nhật thuộc tính, không tự nối các dòng thành hành trình.

## 2. Biểu diễn

- Tự chọn circle/marker, màu phân loại hoặc thang màu định lượng theo thuộc tính thật. Kích thước cố định nếu không có chỉ số phù hợp.
- Khi dùng kích thước để biểu diễn độ lớn, chọn tỷ lệ và giới hạn dễ đọc, kèm chú giải; không dùng ID hoặc tọa độ làm độ lớn.
- Tự đánh giá gom cụm theo mật độ và mức zoom. Số đếm cụm là số đối tượng/quan sát thực được biểu diễn, không phải số kỳ lặp của cùng một đối tượng khi đang hiển thị một kỳ.
- Điểm có vị trí nhưng thiếu chỉ số vẫn giữ trạng thái thiếu dữ liệu rõ ràng; không chuyển giá trị thiếu thành 0.

## 3. Tương tác và chú giải

- Tự chọn tìm đối tượng, lọc nhóm, chọn chỉ tiêu/kỳ hoặc bật/tắt lớp khi có ích; không thêm điều khiển từ trường không tồn tại.
- Nếu gom cụm, cho phép nhấn cụm để zoom/xem chi tiết; đối tượng riêng mở popup theo thao tác phù hợp trên desktop/mobile.
- Popup dùng tên, thuộc tính, chỉ tiêu, đơn vị, thời gian, địa chỉ và ghi chú thực tế. Chú giải phản ánh màu/kích thước đang hiển thị.
- Báo gọn số đối tượng thiếu/sai tọa độ hoặc chưa định vị được từ quá trình kiểm tra thực; vẫn hiển thị các điểm hợp lệ.

Tạo bản đồ bằng lớp circle/symbol hoặc marker phù hợp của MapLibre. Đầu ra tuân thủ JSON ba file trong prompt chung.
