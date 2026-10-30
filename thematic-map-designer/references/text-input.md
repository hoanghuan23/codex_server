# Trích văn bản rồi phân tích bản đồ

Mode text_analysis nhận `text` và `supportedCharts`. Text là nội dung đã được ứng dụng đọc từ tài liệu; không gửi file nhị phân vào hợp đồng này. Đọc toàn văn, trích bảng và phân tích bảng đó theo text-analysis.schema.json; không yêu cầu lượt phân tích thứ hai. Với đầu ra web mặc định, nhúng bảng và cấu hình trong `app.js`, tạo giao diện HTML/CSS. Chỉ trả cấu trúc JSON dưới đây khi caller yêu cầu `output_format=json`.

Trả `fields` (tên cột duy nhất), `rows` (mảng ô theo đúng thứ tự fields), `analysis` (hợp đồng analysis). Mỗi dòng có đúng số ô như fields; ô chỉ có string, number, boolean hoặc null. Tên cột rõ nghĩa bằng tiếng Việt, không có metadata nội bộ. Mọi name/binding/search_fields/metricButtons.field trong analysis chỉ tham chiếu fields vừa tạo. Ứng dụng ghép fields với từng row để tạo records, không yêu cầu AI thêm records ngoài schema.

## Giữ đúng quan sát

Xác định khóa đối tượng × kỳ × ngữ cảnh. Gộp các câu nói cùng quan sát vào một dòng; khác kỳ là dòng khác. Không lặp dòng hoặc toàn bảng. Thu thập đủ chỉ số độc lập, không dừng ở số liệu đầu tiên trong câu. Giải các tham chiếu tiếp nối theo đúng chủ thể và từng chỉ số, kể cả khi mốc tham chiếu nằm sau trong tài liệu.

Các diễn đạt cùng đại lượng, đơn vị và kỳ dùng chung cột. Phân biệt chỉ số độc lập với ghi chú về nguyên nhân, phạm vi hay nguồn. Nếu chỉ một đối tượng có số liệu thuộc một phân nhóm/nguyên nhân, giữ giới hạn trong Ghi chú; không nhân đôi cùng giá trị thành cả chỉ số chung và chỉ số có hậu tố nguyên nhân. Chỉ tách tổng và phân nhóm khi tài liệu cho phép phân tích chúng độc lập. Số phân nhóm không tự thành tổng đầy đủ và không được cộng hai lần.

Không gộp các chỉ số khác nghĩa chỉ vì cùng đơn vị. Không loại một chỉ số độc lập chỉ vì ít đối tượng có dữ liệu. Ghi chú chứa số vẫn là text nếu số đó chỉ giải thích phạm vi, không phải số đo độc lập.

## Số liệu trực tiếp và suy diễn xác định

Giữ số trực tiếp thành number, đơn vị trong tên cột/metadata; không chuyển đơn vị. Có thể tính giá trị khi tài liệu cung cấp đủ quan hệ định lượng và mốc để có nghiệm duy nhất, đúng chỉ số, đơn vị, kỳ và ngữ cảnh:

- Cao/thấp hơn lượng d: A = B ± d.
- Cao/thấp hơn p phần trăm: A = B × (1 ± p/100).
- Bằng q phần trăm: A = B × q/100; gấp k lần: A = B × k; bằng một phần k: A = B / k.
- Giải ngược hoặc giải chuỗi quan hệ khi có nghiệm duy nhất, không chia cho 0. Phần trăm tương đối khác điểm phần trăm.

Điền kết quả vào chính cột chỉ số, không xuất công thức thay cho số và không tự làm tròn số chính xác. Không tự đặt công thức ngoài quan hệ trong nguồn. Nếu mốc thiếu, quan hệ mơ hồ/mâu thuẫn hoặc chỉ biết khoảng mà chưa có giá trị đại diện, dùng null cho ô đó và giữ các chỉ số khác. Không dùng kiến thức bên ngoài để bổ sung mốc.

Số 0 chỉ áp dụng cho đúng chỉ số/phạm vi được nói rõ là không có. Không có dữ liệu là null. Một phân nhóm bằng 0 không làm tổng mọi nhóm bằng 0. Kỳ có năm giữ theo nguồn, tháng có năm dùng YYYY-MM, ngày có năm dùng YYYY-MM-DD; thiếu năm không tự thêm. Năm xuất bản hoặc mốc lịch sử trong ghi chú không tự trở thành kỳ quan sát.

Nếu không có quan sát cụ thể, fields và rows rỗng; analysis vẫn đủ trường: columns/suggestions/search_fields rỗng, search_bar false, regionNavigation null, popupContent với titleField null và các danh sách rỗng. Giải thích thiếu dữ liệu trong grain, không tạo bản đồ giả.

Trước khi xuất, đối chiếu toàn văn: đủ đối tượng/chỉ số/kỳ, đúng phạm vi, không trùng nghĩa, không mất số trực tiếp hoặc số tính duy nhất được. Không xuất các bước suy luận. Sau khi tạo bảng, áp dụng các quy tắc map-rules.md và presentation.md cho analysis; xuất web hoặc JSON theo `output_format` trong SKILL.md.
