# Bản đồ nhiều lớp và liên kết thuộc tính

Mode `composition` nhận `layers` và có thể có `groups` để tạo một bản đồ web chứa các lớp có ý nghĩa xem chung. Áp dụng [prompt chung](prompts/common.md) và prompt riêng theo loại của từng lớp. Đầu ra là một JSON mã nguồn ba file theo [web-output.md](web-output.md).

## Đọc các lớp

- Dùng ID, tên, loại lớp, phạm vi và kỳ được cấp. Giữ ID ổn định, không suy geometry từ tên file.
- Mỗi lớp cần records/geometry hoặc tài nguyên thực truy cập được để vẽ. `available=false` hoặc chỉ có metadata thì báo gọn lớp chưa có dữ liệu; vẫn vẽ các lớp hợp lệ.
- Các lớp khác geometry, cấp địa lý hoặc đơn vị có thể cùng bản đồ; thiết kế chú giải/thang màu riêng khi cần. Không ghép lớp chỉ vì bbox giao nhau hoặc tên gần giống.
- Dùng `groups` được cấp làm ngữ cảnh bật/tắt lớp khi phù hợp. Không buộc mọi lớp có cùng đơn vị, thời gian hoặc chung thang màu; dữ liệu tĩnh vẫn có thể xem cùng dữ liệu theo kỳ.

## Ghép thuộc tính

Chỉ ghép nguồn thuộc tính với lớp không gian khi có khóa thật và quan hệ đúng đối tượng/cấp địa lý/kỳ. Xem tên/mã cùng ngữ cảnh vùng cha khi tên đối tượng không đủ phân biệt. Xem chung không cần khóa join.

Chuẩn hóa Unicode NFC, hoa/thường và khoảng trắng có kiểm soát, giữ dấu tiếng Việt. Khóa thiếu hoặc khớp nhiều đối tượng phải báo chưa phân giải, không tự ghép gần đúng. Không bịa số dòng khớp.

Giữ dữ liệu gốc và nguồn từng thuộc tính. Một đối tượng có nhiều dòng thuộc tính thì giữ các quan sát để lọc/xem popup, không nhân geometry hoặc ghi đè mất dữ liệu. Ảnh và liên kết chỉ dùng giá trị thật theo [presentation.md](presentation.md).

## Thứ tự và tương tác

Vẽ từ dưới lên: vùng/lưới → đường/cung → điểm/nhãn; xử lý lớp cung 3D theo cơ chế renderer tương thích. Mỗi ID lớp chỉ thêm một lần. Thiếu căn cứ phân loại thì giữ thứ tự đầu vào trong cùng nhóm.

Bộ bật/tắt lớp, tìm kiếm và lọc nằm trên bản đồ; tìm kiếm chỉ đưa tới đối tượng thực của lớp phù hợp. Không tự bật lại lớp người dùng đã tắt. Bộ lọc thời gian chỉ tác động lớp có kỳ tương ứng, không làm mất lớp tĩnh.

Fit phạm vi từ dữ liệu thực của các lớp đang hiển thị. Popup dùng đúng lớp/đối tượng được tương tác; lỗi một nguồn không làm mất các lớp còn lại.
