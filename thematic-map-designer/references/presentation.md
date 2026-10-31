# Popup, tương tác và chú giải

Đọc khi dữ liệu cần popup có ảnh/biểu đồ, nhiều chỉ tiêu hoặc cách tô màu phức tạp. Triển khai trực tiếp trong `app.js` theo [prompt chung](prompts/common.md).

## Popup của đúng đối tượng

Chọn tên, mô tả, địa chỉ, chỉ tiêu, kỳ và ghi chú từ các trường thật. Phân biệt đối tượng bằng ID ổn định hoặc tọa độ phù hợp; cùng thành phố/tên chưa chắc là cùng đối tượng.

Chỉ thêm ảnh/liên kết khi có URL thật. URL ảnh có thể có query hoặc chuyển hướng, không bắt buộc đuôi ảnh; ô có thể chứa mảng URL hoặc URL phân cách xuống dòng/dấu chấm phẩy. Kiểm tra giao thức HTTP/HTTPS trước khi hiển thị/mở; mô tả hiển thị như văn bản, không chèn HTML từ dữ liệu.

Chỉ thêm biểu đồ nhỏ trong popup khi giúp đọc quan sát của chính đối tượng được bấm: cột để so sánh các giá trị cùng nghĩa/đơn vị, đường để xem cùng chỉ số qua ít nhất hai mốc thời gian. Không ghép các chỉ số khác đơn vị vào cùng thang mặc định; ID, tọa độ và STT không là số đo. Giữ khoảng trống ở kỳ thiếu dữ liệu, giữ đúng giá trị 0; không tự gộp dòng trùng kỳ khi chưa rõ phép gộp.

## Tìm kiếm và chọn chỉ tiêu

Tìm kiếm theo tên/định danh đối tượng và ngữ cảnh giúp phân biệt; không chọn số đo, thời gian hay tọa độ làm ô tìm kiếm theo thói quen. Quyết định có cần tìm kiếm dựa trên số đối tượng và độ phân tán, không dựa riêng số dòng/ngày.

Chỉ tạo nút chọn chỉ tiêu khi có nhiều trường phù hợp. Nhãn giữ đơn vị; đổi chỉ tiêu phải cập nhật biểu diễn, chú giải và popup đồng bộ. Không gọi AI lại khi thao tác.

## Màu và chú giải

- Thang định lượng tự động dựa trên dữ liệu thực sau lọc/gộp; không dùng min/max của vài mẫu để khẳng định miền toàn tập.
- Ngưỡng hoặc tâm phân kỳ cố định chỉ dùng khi có căn cứ trong dữ liệu/ngữ cảnh, giữ đúng đơn vị. Không tự tìm ngưỡng trên mạng hoặc coi cực đại mẫu là giới hạn có ý nghĩa nghiệp vụ.
- Chọn thang tuần tự có độ sáng/cường độ rõ; thang phân kỳ có tâm trung tính khi tâm có ý nghĩa. Không mặc định giá trị cao là tốt/xấu hoặc dùng đỏ–xanh lá làm tín hiệu phân biệt duy nhất.
- Phân loại dùng giá trị gốc và màu phân biệt, không biến category thành số để cộng/trung bình. Nếu cùng đối tượng/kỳ thật sự có nhiều nhóm, biểu diễn rõ các nhóm thay vì lấy dòng đầu/cuối và làm mất dữ liệu.
- Chú giải luôn khớp hình học đang hiển thị; giải thích màu/kích thước, đơn vị và giá trị thiếu. Giữ mốc cố định khi có căn cứ; nếu đổi miền theo bộ lọc thì nói rõ phạm vi thang hiện tại.
