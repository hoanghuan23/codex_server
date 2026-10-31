# Tìm dữ liệu địa lý trên mạng

Đọc khi đầu ra web cần bổ sung geometry, mã ghép, nền bản đồ hoặc thư viện. Không tải một bộ ranh giới cố định cho mọi input. `webOptions.allowOnlineLookup` mặc định là `true`; yêu cầu không dùng mạng của người dùng hoặc giá trị `false` tắt tra cứu, kể cả việc tự thêm tài nguyên mạng mới vào trang.

## Chọn nguồn theo dữ liệu

Xác định đối tượng được đo, cấp địa lý, vùng cha và kỳ quan sát từ những gì input cung cấp. Dùng tên/mã cùng ngữ cảnh thực để tìm; không mặc định quốc gia từ ngôn ngữ giao diện. Không gửi toàn bộ bảng hay các số đo tới dịch vụ tra cứu.

| Đối tượng | Nguồn cần tìm và kiểm tra |
| --- | --- |
| Quốc gia/lãnh thổ | Ranh giới và mã ISO từ nguồn chính thức hoặc bộ dữ liệu công khai như Natural Earth; phân biệt quốc gia, lãnh thổ và vùng áp dụng riêng. |
| Tỉnh, huyện hoặc cấp hành chính khác | Nguồn hành chính chính thức, geoBoundaries hoặc bộ ranh giới có nguồn gốc và giấy phép phù hợp. Kiểm tra cấp, vùng cha và năm; cùng tên không đủ để ghép. |
| Địa danh, địa chỉ, cơ sở | Nguồn tọa độ công khai, dữ liệu mở hoặc dịch vụ geocoding phù hợp. Xác minh kết quả thuộc đúng địa điểm và đúng độ chi tiết; tuân thủ giới hạn truy vấn của dịch vụ, không đặt geocode hàng loạt không kiểm soát trong trình duyệt. |
| Đường, sông, tuyến | Dữ liệu đường/tuyến thật có mã hoặc tên và ngữ cảnh phù hợp. Không dùng đường thẳng nối hai địa danh để giả làm tuyến thực. |
| Luồng đi–đến | Xác minh từng đầu từ geometry hoặc tọa độ có nguồn; giữ nguyên quan hệ và lưu lượng trong input. Cung nối minh họa luồng, không phải đường đi thực tế. |
| Nhiều lớp | Giải quyết nguồn và khóa ghép cho từng lớp riêng; không áp nguồn của lớp thứ nhất cho mọi lớp. |

Các tên nguồn trên là gợi ý, không phải danh sách bắt buộc. Ưu tiên nguồn caller cung cấp. Với nguồn tự tìm, mở và kiểm tra dữ liệu thực thay vì chỉ dựa vào đoạn trích kết quả tìm kiếm; giữ URL, phiên bản/ngày ranh giới, trường ID/tên và attribution trong cấu hình JS. Kiểm tra điều kiện sử dụng trước khi chọn nguồn, không chọn dịch vụ cần khóa bí mật nếu caller chưa cung cấp cơ chế dùng khóa.

## Ghép và xác minh

1. Ưu tiên mã định danh ổn định. Nếu dùng tên, chuẩn hóa có kiểm soát và đối chiếu thêm cấp/vùng cha. Bỏ dấu, bí danh hoặc viết tắt chỉ dùng khi không tạo trùng và có bằng chứng cùng đối tượng; không tự sửa một tên lạ thành tên gần giống.
2. Kiểm tra geometry không rỗng, đúng Point/LineString/Polygon hoặc kiểu Multi tương ứng. Xác minh hệ tọa độ; GeoJSON dùng WGS84 theo thứ tự `[lng, lat]`. Kiểm tra extent hợp lý theo phạm vi đã xác minh.
3. Đối chiếu thời điểm: ranh giới lịch sử phải được ghi là lịch sử; không tự coi đó là địa giới hiện hành hoặc chuyển số liệu sang vùng mới. Không dùng ranh giới vùng cha thay vùng con còn thiếu.
4. Tính số đối tượng khớp, không khớp và mơ hồ từ phép ghép thực, không dùng `confidence` hoặc số dòng làm tỷ lệ ghép. Giữ ID gốc và số liệu nguyên vẹn. Không tạo thêm quan sát từ dữ liệu địa lý bổ sung.
5. Vẽ các đối tượng khớp; thông báo gọn các đối tượng chưa phân giải trong điều khiển bản đồ. Nếu nhiều địa điểm vẫn có thể khớp, để unresolved và chỉ hỏi ngữ cảnh còn thiếu khi nó thực sự ngăn dựng bản đồ có ý nghĩa.

Giữ geometry/tọa độ bổ sung trong cấu trúc phụ của `app.js` và ghép với records gốc bằng ID, không giả đó là cột được caller cung cấp.

## Tải và giới hạn mạng

Ưu tiên lấy geometry khi tạo trang rồi nhúng vào `app.js` nếu kích thước hợp lý. Với dữ liệu lớn hoặc môi trường chỉ đọc, có thể dùng URL tải trực tiếp đã kiểm tra trong trình duyệt; tránh URL trang xem, URL tạm hết hạn hoặc nguồn không hỗ trợ CORS. Kiểm tra đường dẫn trả dữ liệu thật, có timeout, bắt lỗi và nút thử lại. Không tải lại hình học mỗi lần đổi chỉ số hoặc mở popup.

Nếu nguồn đầu không phù hợp hoặc không truy cập được, tìm nguồn thay thế có cùng cấp/phạm vi. Không lặp vô hạn; sau các lựa chọn hợp lý vẫn thất bại, giữ thông báo gọn và nêu đúng nguyên nhân: thiếu ngữ cảnh, tên mơ hồ, không có geometry phù hợp, CORS hoặc quyền mạng. Không nói đã thử mạng khi công cụ chưa thực sự chạy, và không mở rộng sandbox chỉ vì skill cho phép tìm kiếm.

Không tự tìm số liệu nghiệp vụ thay cho ô thiếu, suy đơn vị từ kết quả tìm kiếm, cập nhật ngày quan sát hay thay ngưỡng chú giải. Với `samplesIncluded: false`, không dùng tra cứu để khôi phục tên/records/giá trị đã bị ẩn; chỉ metadata có thật và tài nguyên địa lý chung được phép sử dụng.
