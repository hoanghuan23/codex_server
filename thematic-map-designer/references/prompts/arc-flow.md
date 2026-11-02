# Prompt bản đồ Arc Flow 3D — `arc_flow`

Áp dụng cùng [prompt chung](common.md). Từ dữ liệu được cung cấp, TỰ PHÂN TÍCH và TỰ THIẾT KẾ bản đồ luồng đi–đến có hướng bằng cung 3D trên bản đồ toàn màn hình.

Mục tiêu thị giác: các cung 3D nổi trên nền bản đồ dịu, có vệt sáng ngắn tự chạy dọc cung theo chiều nguồn → đích. Màu toàn tuyến biểu thị mức lưu lượng, chú giải tách từng mức thành một dòng màu và khoảng số. Không tạo nút chạy/tạm dừng. Áp dụng theo ngữ nghĩa dữ liệu thực; không mặc định lĩnh vực, địa điểm, tên cột, đơn vị hoặc các ngưỡng của một bộ dữ liệu mẫu.

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

## 3. Dựng cung 3D bằng deck.gl

- Dùng deck.gl `ArcLayer`, tích hợp với MapLibre GL JS qua overlay tương thích như `MapboxOverlay`. Ghim phiên bản các thư viện tương thích, đồng bộ camera và dùng API thực của phiên bản đã chọn. Dùng lớp chuẩn cho cung nền; lớp chuyển động có thể mở rộng shader bằng hook đúng phiên bản sau khi kiểm tra mã nguồn hoặc tài liệu và thử trên trình duyệt.
- Cung phải có độ cao thực trên bản đồ khi nghiêng camera; không thay bằng đường thẳng phẳng, đường cong 2D hoặc hiệu ứng CSS phủ lên canvas. Tự chọn độ cao, độ nghiêng và zoom theo phạm vi, để cả hai đầu và phần đỉnh cung đọc được trong khung nhìn ban đầu.
- Độ cao cung giúp tách tuyến, không tự mã hóa lưu lượng. Điều chỉnh theo khoảng cách với giới hạn hợp lý; xử lý luồng qua kinh tuyến 180° để không vòng sai quanh bản đồ.
- Giữ nguyên nền OpenFreeMap style Liberty theo prompt chung; chọn độ tương phản của cung và vệt sáng phù hợp với nền gốc, không tự đổi màu hoặc ẩn các lớp nền. Không giới hạn vùng di chuyển theo các điểm OD; fit chỉ là khung nhìn ban đầu hoặc thao tác định vị/vừa khung do người dùng chọn, không khóa camera hay tự fit lại khi resize.
- Hiển thị điểm đầu/cuối tại tọa độ thật và nhãn có chọn lọc theo zoom hoặc trạng thái chọn; tránh lặp nhãn tại nút dùng chung. A → B và B → A giữ ID, chiều và popup riêng; khi trùng cung, có thể dùng độ nghiêng cung khác nhau để chọn được từng chiều.
- Với `TextLayer` có nhãn tiếng Việt hoặc ký tự ngoài ASCII, dùng `characterSet: 'auto'` hoặc bộ ký tự bao phủ nhãn thực tế; bật SDF nếu dùng viền chữ. Kiểm tra cả nhãn chỉ xuất hiện sau khi chọn hoặc zoom, không chỉ lúc tải ban đầu.
- Cung biểu diễn quan hệ luồng, không khẳng định là tuyến đường di chuyển thực tế.

## 4. Vệt sáng tự chạy dọc cung

- Giữ cung nền nhìn thấy liên tục; thêm vệt sáng ngắn có đầu sáng, đuôi mờ dần tự chạy từ nguồn đến đích rồi lặp lại. Quầng sáng tĩnh có thể bổ trợ, nhưng không thay thế chuyển động dọc tuyến. Không nhấp nháy toàn tuyến hoặc chỉ đổi độ sáng cả cung cùng lúc.
- Các lớp dùng cùng dữ liệu, tọa độ, độ cao, độ nghiêng và số đoạn để vệt sáng bám đúng cung khi xoay, nghiêng, zoom hoặc resize; không chạy trên đường thẳng nối hai đầu hoặc đường cong 2D khác với cung nền.
- Màu gốc của viền và vệt sáng lấy từ cùng nhóm lưu lượng với lõi cung. Có thể tăng độ sáng hoặc pha trắng cục bộ ở đầu vệt, nhưng không đổi sang màu của nhóm khác. Tiết chế độ sáng ở vùng nhiều cung giao nhau, không làm mất màu phân lớp hoặc che nhãn.
- Mỗi layer có ID riêng nhưng cùng trỏ về khóa bản ghi gốc. Chỉ lớp cung tương tác nhận picking; các lớp viền trang trí đặt `pickable: false`, không chặn bấm/chạm hoặc tạo popup trùng.
- Dùng tham số tiến độ dọc cung và thời gian để di chuyển vệt theo đúng chiều nguồn → đích. Với shader hook, chỉ đọc biến có trong phạm vi hook của phiên bản đã chọn; không giả định biến toàn cục của shader có thể truy cập ở mọi hook. Không giả định thêm thuộc tính thời gian vào `ArcLayer` chuẩn là tự có animation.
- Chuyển động dựa trên thời gian thực, không số frame; cập nhật uniform/trạng thái thời gian cần thiết, không dựng lại bản đồ hoặc dữ liệu mỗi frame. Xử lý điểm lặp để vệt không chạy ngược từ đích về nguồn. Tốc độ chỉ mang tính minh họa nếu dữ liệu không có vận tốc/thời gian hành trình thật.
- Hiệu ứng tự chạy, không thêm nút chạy, tạm dừng hoặc điều khiển tốc độ. Tôn trọng `prefers-reduced-motion`; khi giảm chuyển động, dùng ký hiệu tĩnh phân biệt nguồn/đích. Dừng vòng lặp khi trang ẩn, tập hiển thị rỗng hoặc bản đồ bị tháo, và tiếp tục đúng lúc khi trở lại.
- Chú giải giải thích vệt sáng biểu thị hướng; popup luôn ghi nguồn → đích. Có thể bổ sung nhãn điểm đi/đến cho luồng đang chọn; không dùng màu hai đầu khác nhau để thay hướng vì màu đã mã hóa lưu lượng.

## 5. Màu theo lưu lượng và chú giải đồng bộ

- Màu chính của mỗi tuyến lấy từ số đo lưu lượng đang chọn, không lấy từ ID, địa danh, chiều đi hay màu ngẫu nhiên. Với `ArcLayer`, đặt `getSourceColor` và `getTargetColor` cùng màu của mức lưu lượng; dành chiều đi–đến cho vệt sáng.
- Mặc định phân lớp rời rạc với các mức thấp → trung bình → cao và màu đỏ → vàng → xanh; không mặc định màu đỏ là xấu hoặc xanh là tốt. Chọn ngưỡng từ dữ liệu theo quy tắc phù hợp như phân vị, hoặc giữ ngưỡng người dùng đã cấp. Không sao chép ngưỡng hay đơn vị của một ví dụ vào dữ liệu khác. Dữ liệu ít giá trị hoặc toàn bộ bằng nhau thì giảm số mức, không tạo nhóm rỗng.
- Chú giải hiển thị từng mức trên một dòng riêng: đoạn màu ngắn + tên mức + khoảng số, ví dụ cấu trúc `Thấp: <min> – <max>`. Có tiêu đề chỉ tiêu và đơn vị thật. Không dùng một thanh gradient chung hoặc chỉ ba mốc min/giữa/max để thay thế các dòng phân lớp; chỉ chuyển sang thang liên tục nếu người dùng yêu cầu rõ.
- Ngưỡng phân lớp phải bao phủ mọi giá trị dương hợp lệ, không hở hoặc chồng khoảng; quy định giá trị đúng ngưỡng thuộc khoảng nào. Nhãn có thể hiển thị ngưỡng hoặc min–max thực có trong từng mức; nếu dùng min–max thực có, giải thích ngắn cách đọc để khoảng không có quan sát không bị hiểu thành thiếu phân lớp. Không làm tròn gây sai nghĩa ranh giới.
- Dùng chung một cấu hình/hàm ánh xạ cho màu cung, viền, vệt sáng, highlight và từng dòng chú giải. Các tuyến trong cùng mức có cùng màu gốc; không nội suy màu liên tục bên trong nhóm. Phần giải thích hướng tách rõ khỏi phần giải thích màu lưu lượng.
- Mặc định giữ miền màu theo tập dữ liệu hợp lệ của chỉ tiêu và phạm vi so sánh đang dùng, để cùng giá trị không đổi màu chỉ vì lọc hoặc Top N. Nếu chủ động tính lại miền theo dữ liệu đang hiển thị, ghi rõ và cập nhật chú giải cùng lúc. Không dùng chung thang cho các chỉ tiêu khác đơn vị.
- Độ dày có thể bổ trợ lưu lượng bằng tỷ lệ đơn điệu có giới hạn, nhưng màu vẫn là kênh chính. Giữ tuyến nhỏ có thể chọn; không để highlight hoặc viền sáng che mất màu phân lớp. Giá trị 0 không có cung hoặc viền sáng khiến người xem hiểu thành luồng dương.

## 6. Tương tác và kiểm tra kết quả

- Tự chọn bộ lọc kỳ/nhóm, tìm điểm đi/đến, ngưỡng lưu lượng hoặc Top N khi dữ liệu đủ lớn; không thêm điều khiển không có cơ sở. Với Top N, nói rõ số luồng đang hiển thị và phạm vi sau bộ lọc; không mô tả phần đang chọn là toàn bộ dữ liệu.
- Hover hoặc bấm/chạm cung chọn đúng luồng, làm nổi cả cung và hai đầu tương ứng. Popup dùng điểm đi → điểm đến, lưu lượng, đơn vị, kỳ và nhóm thực tế; không chỉ cho phép chọn điểm mà bỏ tương tác trên cung.
- Popup DOM phải nổi trên canvas deck.gl theo prompt chung, kể cả khi `MapboxOverlay` dùng canvas riêng (`interleaved: false`). Kiểm tra thứ tự lớp của container chứa canvas so với popup; không dùng `depthTest` hoặc độ cao cung để sửa thứ tự chồng lớp DOM. Thử mở popup tại nơi nhiều cung/vệt sáng đi qua, kiểm tra nội dung và nút đóng trên desktop/mobile.
- Lọc hoặc đổi chỉ tiêu phải đồng bộ cung, viền, vệt sáng, chú giải, popup và trạng thái chọn; tập rỗng hiển thị trạng thái trống và xóa các lớp dữ liệu cũ.
- Trước khi trả kết quả, kiểm tra: cung có chiều cao 3D; vệt sáng thực sự thay đổi vị trí theo thời gian từ nguồn đến đích và không lệch cung khi đổi camera; chú giải có các dòng riêng và màu tuyến tại các giá trị biên khớp từng dòng; chọn được hai chiều OD; lọc không để lại viền hoặc highlight cũ. Kiểm tra lỗi khởi tạo/vẽ layer trong console; không quy lỗi shader hoặc thư viện thành thiết bị thiếu WebGL khi chưa có căn cứ. Chỉ báo đã kiểm chứng trên trình duyệt nếu thực sự chạy thử.

Đầu ra tuân thủ JSON ba file trong prompt chung. Mọi thư viện cần cho cung 3D và chuyển động được liên kết trong `index.html`; dữ liệu, cấu hình phân lớp/chú giải, logic cung, vệt sáng và tương tác nằm trong `app.js`, không yêu cầu npm/build hoặc thêm file ngoài hợp đồng.
