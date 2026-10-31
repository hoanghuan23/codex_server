# Prompt bản đồ Arc Flow 3D — `arc_flow`

Áp dụng cùng [prompt chung](common.md). Từ dữ liệu được cung cấp, TỰ PHÂN TÍCH và TỰ THIẾT KẾ bản đồ luồng đi–đến có hướng bằng cung 3D trên bản đồ toàn màn hình.

## 1. Phân tích luồng đi–đến

- Xác định mỗi dòng là một luồng từ điểm đi (`source`) đến điểm đến (`target`), có hai vị trí độc lập và một số đo lưu lượng (`value`). Tên cột có thể khác; giữ tên thật trong dữ liệu.
- Dùng ID/tên nguồn–đích, tọa độ/Point có sẵn và các trường kỳ/nhóm nếu có. Không dùng một cặp tọa độ cho cả hai đầu hoặc lấy ID, số thứ tự hay nhóm lưu lượng làm số đo.
- Nếu đầu luồng chỉ có địa danh, chỉ bổ sung tọa độ từ nguồn công khai đã xác minh khi được phép. Giữ tọa độ bổ sung trong cấu trúc phụ ghép bằng ID, không giả đó là cột số liệu đầu vào.
- Một geometry tuyến hoặc một bảng các điểm độc lập không tự tạo quan hệ OD hay lưu lượng. Nếu thiếu quan hệ nguồn–đích hoặc số đo, báo thiếu dữ liệu để vẽ luồng.

## 2. Kiểm tra và gộp dữ liệu

- Kiểm tra hai cặp tọa độ đúng hệ và phạm vi, GeoJSON theo `[lng, lat]`. Tọa độ bằng `0` không tự là lỗi; tọa độ thiếu không chuyển thành 0.
- Loại khỏi lớp cung các dòng thiếu/sai tọa độ, lưu lượng thiếu, không hữu hạn hoặc âm, hoặc hai đầu trùng vị trí; báo số dòng và nguyên nhân từ kiểm tra thực.
- Giữ lưu lượng `0` là giá trị 0; không dựng độ rộng tối thiểu khiến người xem hiểu thành luồng dương. Có thể không vẽ cung 0 và cho biết trong chú giải/trạng thái.
- Giữ riêng A → B và B → A. Không gộp hai địa điểm chỉ vì cùng tên khi ID/tọa độ khác nhau.
- Chỉ gộp OD lặp khi cùng kỳ, cùng nhóm, cùng đơn vị và lưu lượng có ý nghĩa cộng dồn. Không cộng tổng và các phân nhóm của chính tổng đó hai lần.

## 3. Cung 3D và chiều luồng

- Dùng MapLibre GL JS với renderer cung 3D tương thích, ví dụ deck.gl `ArcLayer` qua `MapboxOverlay`; nạp đúng các thư viện/phiên bản và đồng bộ camera với bản đồ.
- Cung phải có độ cao thực trên bản đồ khi nghiêng camera; không thay bằng đường thẳng phẳng hoặc đường cong chỉ vẽ trong mặt phẳng tọa độ.
- Thể hiện rõ chiều đi–đến bằng màu nguồn/đích, mũi tên hoặc chuyển động có chú giải; không chỉ dựa vào độ cao cung. Hai chiều cùng OD phải có cách phân biệt khi tương tác.
- Độ rộng/độ trong suốt và màu phản ánh lưu lượng/nhóm với tỷ lệ dễ đọc. Tự chọn độ nghiêng, zoom và độ cao cung phù hợp phạm vi, không làm luồng nhỏ mất khả năng tương tác.
- Cung biểu diễn quan hệ luồng, không khẳng định là tuyến đường di chuyển thực tế. Chỉ thêm điểm đầu/cuối nếu có vị trí thật và giúp đọc bản đồ.

## 4. Tương tác và chú giải

- Tự chọn bộ lọc kỳ/nhóm, tìm điểm đi/đến, ngưỡng lưu lượng hoặc Top N khi dữ liệu đủ lớn; không thêm điều khiển không có cơ sở.
- Với Top N, nói rõ số luồng đang hiển thị và phạm vi sau bộ lọc; không mô tả phần đang chọn là toàn bộ dữ liệu.
- Popup khi hover/nhấn cung dùng điểm đi, điểm đến, lưu lượng, đơn vị, kỳ và nhóm thực tế. Tương tác phải hoạt động trên cả desktop/mobile.
- Chú giải giải thích chiều nguồn–đích và thang lưu lượng. Lọc hoặc đổi chỉ tiêu phải cập nhật cung, chú giải và popup; tập rỗng hiển thị trạng thái trống.

Đầu ra tuân thủ JSON ba file trong prompt chung. Mọi thư viện cần cho cung 3D được liên kết trong `index.html`, dữ liệu và logic nằm trong `app.js`.
