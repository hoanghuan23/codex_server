# Popup, nút chỉ số và chú giải

Các cấu trúc dưới đây mô tả quyết định trình bày. Đầu ra web mặc định phải triển khai chúng trong ba file HTML/JS/CSS; cấu hình JSON riêng chỉ dành cho `output_format=json`.

## Popup của một đối tượng

Mỗi suggestion có 1–4 `popupSuggestions`, mỗi phần tử chỉ có `name` và `confidence` 0–1; name không trùng, xếp giảm dần. Đánh giá các quan sát của một vùng/tuyến/điểm được bấm theo grain và binding, không theo số ngày hoặc số dòng của toàn bảng.

- `info`: mô tả, phân loại, quan sát đơn lẻ hoặc thiếu cơ sở dựng biểu đồ.
- `info_image`: có cột ảnh thực sự phù hợp.
- `bar`: so sánh độ lớn qua kỳ hoặc giá trị tổng hợp của đối tượng có ý nghĩa.
- `line`: cùng đối tượng có ít nhất hai mốc có số liệu và chỉ số theo thời gian có ý nghĩa.

Không tự trả đủ mọi kiểu. Không dùng ID, tọa độ hoặc thứ tự làm chỉ số; không ghép các measure khác đơn vị trong cùng biểu đồ mặc định. Không tự tạo trục phân loại hoặc cấu hình biểu đồ mà renderer popup chưa hỗ trợ. Bar/line ở đây khác với chartType map_line; không thêm reason/bindings vào popupSuggestions.

`popupContent` ở cấp kết quả analysis gồm titleField hoặc null, imageFields, descriptionFields, addressFields, linkFields; tất cả chỉ tham chiếu tên cột thật, danh sách rỗng khi không có. Nguồn thuộc tính chưa có bản đồ vẫn có thể có popupContent. Cột ảnh khác cột liên kết trang web; URL ảnh không bắt buộc có đuôi ảnh, có thể chuyển hướng/query. Một ô có thể chứa URL đơn, mảng URL hoặc URL phân cách xuống dòng/dấu chấm phẩy. Không tự sinh URL hoặc thông tin ngoài nguồn. Ứng dụng chỉ mở HTTP/HTTPS hợp lệ và hiển thị chuỗi mô tả như văn bản.

Renderer cần xác định đúng đối tượng qua ID ổn định hoặc tọa độ khi không có ID; các điểm cùng thành phố không tự là một đối tượng. Khoảng thiếu số liệu giữ khoảng trống, số 0 giữ số 0. Phép gộp bản ghi trùng kỳ theo aggDefault của từng measure; chưa xác định phép gộp thì báo thiếu cấu hình thay vì tự lấy trung bình. Mở popup/lọc thời gian dùng records tại ứng dụng, không gọi AI lại.

## Nút chọn chỉ số

`metricButtons` thiết kế riêng cho từng suggestion khi có ít nhất hai trường phù hợp; nếu ít hơn thì []. Mỗi phần tử chỉ có field, label tiếng Việt ngắn (1–80 ký tự), icon Unicode ngắn (tối đa 12 ký tự), color HEX #RRGGBB. Không lặp field, không tạo icon HTML/SVG/URL. Màu nút chỉ trang trí, không thay ánh xạ chú giải.

Polygon/Line chọn measure hoặc category phản ánh trạng thái tối đa 12 giá trị. Khi có nút, phải bao gồm value mặc định. Point chỉ chọn measure để điều chỉnh kích thước, nút đầu là chỉ số kích thước mặc định. Không chọn cột region, x, tọa độ, mã/ID, thời gian, ngữ cảnh địa lý hoặc cột nhóm tuyến. Nhãn giữ nguyên đơn vị; không tạo chỉ số mới. Arc Flow trả [].

## Chú giải thuộc cột và suggestion

Trong cùng request, thiết kế columns[].legend cho từng measure và category phù hợp để tô màu; cột khác null. Chú giải thuộc cột chứa nó, không thêm field hoặc legendSchemaVersion vào object. `aggregation` khớp aggDefault và `unit` khớp đơn vị cột; count dùng “bản ghi”. Không sửa aggDefault chỉ để dựng chú giải.

Với Polygon/Line dùng phép gộp mặc định, suggestion.legend null để ứng dụng dùng chú giải của cột. Chỉ trả legend riêng ở suggestion khi phép gộp khác mặc định, khớp value, agg và đơn vị kết quả. Point/Arc Flow có suggestion.legend null. Không có measure/category tô màu thì legend null; renderer dùng màu hình học mặc định và vẫn có thể tạo ký hiệu trong chú giải.

### Số đo

Trả đủ aggregation, type, mode, title tiếng Việt không quá 160 ký tự, unit, domain, center, stops và reason không quá 800 ký tự. Reason giải thích họ màu, chiều màu và cơ sở mode, không chứa chỉ dẫn thực thi. Màu luôn là HEX #RRGGBB.

- `continuous` + `auto`: khi chưa có ngưỡng ngữ nghĩa đáng tin cậy. Domain [0, 1], center null, 2–12 stops ở vị trí tương đối từ 0 đến 1. Ứng dụng ánh xạ sang min/max sau lọc/tổng hợp, không dùng min/max mẫu như miền render.
- `continuous` + `semantic`: miền/mốc cố định có cơ sở từ ý nghĩa và đơn vị, center null. Không lấy max mẫu làm cực đại ngữ nghĩa.
- `diverging` + `semantic`: có center hữu hạn mang ý nghĩa thực sự, nằm giữa domain, có stop chính xác tại center và ít nhất một stop mỗi phía. Tối thiểu 3, tối đa 12 stops. Không dùng diverging auto hoặc trung điểm mẫu làm tâm.

Domain có hai số hữu hạn tăng dần; stops tăng nghiêm ngặt, hai stop biên trùng domain. Chọn màu theo đại lượng và chiều tăng, thống nhất giữa các cột cùng đại lượng. Thang tuần tự có độ sáng/cường độ thay đổi rõ; thang phân kỳ có hai phía phân biệt và tâm trung tính. Khi ngữ nghĩa chưa rõ, dùng họ màu trung tính với mode auto. Không mặc định giá trị cao là tốt/xấu, không biến liên tưởng màu thành ngưỡng cảnh báo chính thức. Tránh cầu vồng tùy tiện và dùng đỏ–xanh lá làm tín hiệu phân biệt duy nhất.

Chỉ giữ mốc semantic khi có căn cứ trong dữ liệu/ngữ cảnh được cấp. Không gọi dịch vụ ngoài để tìm ngưỡng, không bịa nguồn quy định, không đổi đơn vị. Biết họ màu phù hợp không đồng nghĩa với biết ngưỡng semantic.

### Phân loại

Category dùng type categorical, mode semantic; aggregation/unit/domain/center đều null. Stops có 1–12 giá trị gốc nguyên văn, mỗi giá trị một màu riêng; không đổi category thành số hoặc gộp các tên khác nhau. Ưu tiên categoryValues đầy đủ khi có; thiếu bằng chứng về toàn bộ tập giá trị thì không tuyên bố bao phủ mọi nhóm.

`combinations` luôn có ở legend categorical, [] nếu không có tổ hợp. Chỉ tạo tổ hợp từ các giá trị khác nhau thật sự cùng geometry và phạm vi thực tế; mỗi mục có values gồm các giá trị của stops và một màu riêng, khác mọi màu đơn/tổ hợp khác. Không phụ thuộc thứ tự dòng, không lặp tổ hợp đảo thứ tự, không chọn dòng đầu/cuối để bỏ các giá trị còn lại. Tối đa 64 tổ hợp. Không tạo nhóm “Nhiều giá trị”, không dùng sọc, không cộng hay lấy trung bình category.

Ứng dụng phải dùng cùng một ánh xạ cho hình học, chú giải và lớp lưới dẫn xuất. Lọc/chuyển chỉ số dùng cấu hình đã lưu: auto cập nhật miền thực tế, semantic giữ mốc cố định. Nếu legend không hợp lệ, ứng dụng báo hoặc dùng thang kỹ thuật được đánh dấu rõ; không sửa dữ liệu hay gọi AI lặp chỉ vì người dùng mở popup.
