# Tổ hợp lớp và liên kết thuộc tính

Đây là hợp đồng cấu hình nội bộ. Với đầu ra web mặc định, dùng các quyết định để xây giao diện và vẽ những lớp có records/geometry thực được cấp; lớp chỉ có metadata phải báo chưa đủ dữ liệu. Yêu cầu trả schema JSON bên dưới chỉ áp dụng khi `output_format=json`.

## Đầu vào

Payload gồm `workspaceRevision`, `layers`, `groups`, `newLayerIds`, `activeGroupId`. Tối đa 50 lớp trong một lần đánh giá. Mỗi lớp có id duy nhất và metadata: sourceKind (`spatial`/`attribute`), title, grain, chartType, available, geometryKinds, extent [west, south, east, north] hoặc null, columns, time, search_bar/search_fields, popupContent/popupSuggestions.

Columns chỉ chứa name, labelVi, role, geoLevel, country, unit, semanticType. Time chỉ gồm field, granularity, count. PopupContent chỉ là tên trường. Hợp đồng cấu hình `output_format=json` không cần records, geometry đầy đủ, giá trị mẫu hoặc URL ảnh thật; không yêu cầu gửi thêm để hoàn tất cấu hình. Đầu ra web có thể nhận records/geojson được cấp thêm theo `web-output.md`; thiếu thì hiển thị trạng thái chưa có dữ liệu thay vì giả lập lớp đã vẽ.

Groups có id, title và layerIds hợp lệ; không chứa nguồn attribute. newLayerIds chỉ chứa ID có trong layers, chưa thuộc nhóm hiện hữu và không trùng. activeGroupId là ID nhóm có thật hoặc null. Ứng dụng kiểm tra payload và giữ workspaceRevision để bỏ qua phản hồi tới muộn; AI không thêm revision vào schema phản hồi.

## Quyết định nhóm

Trả đúng một decision cho mỗi ID trong newLayerIds theo cùng thứ tự. Trường là `layerId`, không phải newLayerId. Không di chuyển lớp cũ hoặc gộp các nhóm cũ.

Đánh giá cả ích lợi xem chung và khả năng hiển thị từ grain, đơn vị, geometry, phạm vi, thời gian, mục đích và độ dễ đọc. Không ghép chỉ vì bbox giao nhau, geometry giống nhau hoặc tên file giống nhau. Khác geometry/cấp địa lý/đơn vị hoặc dữ liệu tĩnh với chuỗi thời gian vẫn có thể cùng bản đồ có ý nghĩa; không ép cùng đơn vị, cùng thời gian hoặc chung thang màu. Hiển thị chung không cần khóa join.

Đánh giá lớp mới với toàn bộ thành viên nhóm, kể cả các lớp mới khác dự kiến vào nhóm trong cùng phản hồi; không suy diễn tương thích bắc cầu. Thiếu bằng chứng thì undetermined. Lớp available false không được append/create; giữ undetermined với lý do.

| action | targetGroupId | newGroupKey |
| --- | --- | --- |
| `append_to_group` | ID nhóm đã có trong đầu vào. | null. |
| `create_group` cho một lớp riêng | null. | null. |
| `create_group` cho nhiều lớp mới cùng nhóm | null. | Cùng một key khác null cho tất cả lớp trong nhóm đó. |
| `undetermined` | null. | null. |

Không dùng append_to_group để tham chiếu nhóm mới chỉ đang được tạo trong phản hồi. Nếu có nhiều nhóm phù hợp, chọn độ phù hợp cao nhất; hòa thì ưu tiên activeGroupId, sau đó thứ tự nhóm đầu vào. groupTitle tiếng Việt phản ánh nội dung toàn nhóm, reason cụ thể, confidence 0–1. Nguồn attribute mới dùng undetermined và lý do chờ liên kết; không tạo geometry hay nhóm bản đồ cho nguồn đó.

## Liên kết thuộc tính độc lập với nhóm

Xét toàn bộ nguồn attribute cũ/mới với lớp spatial cũ/mới, hỗ trợ cả hai thứ tự import. Chỉ liên kết trực tiếp attribute → spatial available; một lớp có thể nhận nhiều nguồn. Không liên kết qua bảng trung gian, không gộp các lớp không gian chỉ vì cùng nhận nguồn thuộc tính.

Mỗi đề xuất attributeJoins gồm sourceId, targetLayerId, keyPairs, popupContent, popupSuggestions, confidence và reason. Mỗi cặp source/target tối đa một đề xuất; keyPairs có 1–8 cặp sourceField/targetField thật, không lặp cột trong cùng phía, không dùng metadata nội bộ. Chọn khóa theo ý nghĩa và grain, thêm ngữ cảnh địa điểm/mã khi tên đối tượng không đủ phân biệt. Không bịa giá trị hoặc số dòng khớp; confidence chỉ nói độ hợp lý về ngữ nghĩa.

Client so khớp cục bộ sau chuẩn hóa Unicode NFC, hoa/thường và khoảng trắng, giữ dấu tiếng Việt; khóa thiếu hoặc trỏ nhiều đối tượng không được tự ghép gần đúng. Một đối tượng có thể nhận nhiều dòng thuộc tính; ứng dụng giữ các mục, nguồn và ảnh không trùng. Không ghi đè dữ liệu gốc, nhân geometry hay thay bảng/export để phục vụ popup.

PopupContent của join tham chiếu cột nguồn attribute, không lấy tên cột đích thay thế. Chọn titleField hoặc null và các mảng imageFields/descriptionFields/addressFields/linkFields. Có ảnh phù hợp thì có thể đề xuất info_image; name popup chỉ là info/info_image/bar/line với confidence, không trùng và xếp theo độ phù hợp. Chỉ đề xuất bar/line khi metadata có cơ sở ở mức một đối tượng, không đòi xem toàn bộ dữ liệu. Không có join có cơ sở thì attributeJoins [], giải thích trong decision của nguồn mới nếu liên quan.

## Tìm kiếm và áp dụng

searchLayerIds bao gồm đầy đủ ID lớp spatial có search_bar true và search_fields hợp lệ trong hồ sơ, gồm cả lớp cũ. Không bỏ tìm kiếm chỉ vì có lớp khác cùng địa danh; không bật lại lớp đã tắt và không đưa nguồn attribute độc lập vào danh sách tìm kiếm của bản đồ.

Trả đúng schema composition: chỉ decisions, searchLayerIds, attributeJoins. Ứng dụng kiểm tra ID, quyền sở hữu nhóm, điều kiện available và revision trước khi áp dụng. Khi lỗi, giữ dữ liệu thành bản đồ riêng/nguồn chờ liên kết và báo nguyên nhân. Thứ tự vẽ kỹ thuật do renderer áp dụng: vùng/lưới dưới, tuyến giữa, điểm/nhãn trên.
