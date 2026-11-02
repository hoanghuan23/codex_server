# Nguồn dữ liệu địa lý: kho cục bộ và tra cứu mạng

Đọc khi đầu ra web cần bổ sung geometry, mã ghép, nền bản đồ hoặc thư viện. Ưu tiên geometry được cấp → kho hành chính cục bộ phù hợp → nguồn mạng cho phần còn thiếu. Không tải một bộ ranh giới cố định cho mọi input. `webOptions.allowOnlineLookup` mặc định là `true`; yêu cầu không dùng mạng của người dùng hoặc giá trị `false` tắt tra cứu, kể cả việc tự thêm tài nguyên mạng mới vào trang, nhưng vẫn cho phép đọc kho cục bộ.

## Kho ranh giới hành chính cục bộ

- Kho có tên thực tế `administrative_division`, nằm cạnh thư mục `thematic-map-designer`. Từ đường dẫn tuyệt đối `SKILL.md` được caller chỉ định, lấy `skill_dir.parent / "administrative_division"`; không dùng đường dẫn tương đối với thư mục tạm chứa input/output. Không cần sao chép kho vào thư mục tạm.
- Mỗi quốc gia/lãnh thổ có thư mục mã ISO 3166-1 alpha-3 viết hoa; file theo mẫu `<ALPHA3>/<ALPHA3>_ADM<level>.geojson`, ví dụ `VNM/VNM_ADM1.geojson`, `USA/USA_ADM2.geojson`. Xác định mã từ ngữ cảnh quốc gia thật trong input; nếu mã/tên chưa đủ xác định thì không mặc định `VNM` từ tiếng Việt. Kiểm tra thư mục/file tồn tại trước khi đọc, không đoán URL tải trực tuyến.
- Chỉ liệt kê file của quốc gia liên quan và đọc cấp cần thiết. `ADM0` là quốc gia; các cấp `ADM1`, `ADM2`… theo phân cấp thực của từng nước. Tỉnh/thành phố cấp tỉnh thường ở `ADM1`, nhưng thành phố trực thuộc một tỉnh có thể ở cấp khác: kiểm tra `TYPE_<level>`, `ENGTYPE_<level>` và vùng cha, không mặc định mọi tên “thành phố” là `ADM1`.
- Dùng Python/JSON để đọc file một lần, xem metadata và danh sách properties gọn rồi trích các feature cần thiết; không in toàn bộ tọa độ vào ngữ cảnh hay quét tất cả quốc gia/cấp. Tái sử dụng geometry theo khóa quốc gia/cấp/phiên bản cho các chỉ tiêu, kỳ và lớp dùng cùng ranh giới. Không đọc/tải lại theo từng dòng quan sát.
- Các file đã kiểm tra có schema GADM: `GID_0`/`COUNTRY` cho quốc gia, `GID_<level>`/`NAME_<level>` cho vùng; có thể có `VARNAME_<level>`, `NL_NAME_<level>`, `CC_<level>`, `HASC_<level>`, `ISO_<level>` và thuộc tính cấp cha. Kiểm tra properties thực tế thay vì giả định mọi file đủ cột. `GID` là mã của bộ ranh giới, không mặc định bằng mã hành chính trong bảng; chỉ dùng mã tương thích hoặc bảng ánh xạ có căn cứ. Mã alpha-3 dùng chọn file, không bảo đảm mọi feature trong file đều có `GID_0` bằng mã thư mục; kiểm tra các phần rời/ngữ cảnh trước khi loại hoặc gộp feature, không làm mất phần ranh giới chỉ vì mã khác. Chuỗi `NA` trong trường mã/bí danh là thiếu dữ liệu, không phải một khóa ghép.
- Ghép mã trước; nếu dùng tên, chuẩn hóa Unicode, hoa/thường và khoảng trắng, thử tên/bí danh có trong file cùng cấp và vùng cha. Một số tên GADM viết liền như `AnGiang`; có thể dùng khóa bỏ khoảng trắng/dấu phân cách và khóa không dấu để tìm ứng viên, nhưng chỉ chấp nhận khi xác minh duy nhất đúng đối tượng. Giữ tên gốc trong giao diện; không lấy ứng viên gần nhất hoặc chỉ dựa vào tên để bỏ qua cấp/vùng cha.
- Kiểm tra phiên bản và phạm vi ranh giới ngay trong metadata/properties. Ví dụ kho `VNM_ADM1.geojson` hiện có tên bộ `gadm41_VNM_1` với 63 feature; không mặc định tương ứng dữ liệu theo một đợt sáp nhập khác. Không lấy năm quan sát làm năm ranh giới, thay vùng cũ bằng vùng mới cùng tên hoặc hợp nhất vùng nếu chưa có ánh xạ/phạm vi rõ ràng. Địa giới cục bộ sai cấp, sai phạm vi hoặc không phù hợp thời điểm được xem là chưa có ranh giới phù hợp cho quan sát đó.
- Nếu tất cả vùng cần thiết khớp với geometry hợp lệ, dùng ngay kho cục bộ và không tìm kiếm mạng để xác nhận/tải lại cùng ranh giới. Nếu thiếu file, file không đọc được, thiếu vùng hoặc không có phiên bản phù hợp, giữ các vùng đã khớp và chỉ tra nguồn mạng cho phần còn thiếu khi được phép. Tên mơ hồ thì giữ trạng thái chưa phân giải hoặc xác minh thêm ngữ cảnh, không dùng mạng như lý do để đoán khớp. Khi cấm mạng hoặc không đọc được kho, báo đúng phần thiếu và vẫn vẽ các vùng hợp lệ.
- Nhúng geometry đã chọn và các thuộc tính cần ghép vào `app.js` theo hợp đồng ba file; không sinh `fetch` tới đường dẫn máy chủ, `file://` hoặc thư mục `administrative_division` trong trình duyệt. Giữ đủ các phần Polygon/MultiPolygon; ghi nguồn file, phiên bản và attribution thực có trong cấu hình nguồn/panel thu gọn, không bịa URL hoặc giấy phép. Kho chỉ bổ sung địa lý, không bổ sung số liệu nghiệp vụ hay tạo thêm quan sát.

## Chọn nguồn theo dữ liệu

Chỉ thực hiện tra mạng sau khi kiểm tra nguồn được cấp và kho cục bộ: ranh giới hành chính đã khớp thì bỏ qua bước này. Với phần còn thiếu, xác định đối tượng được đo, cấp địa lý, vùng cha và kỳ quan sát từ input. Dùng tên/mã cùng ngữ cảnh thực để tìm; không mặc định quốc gia từ ngôn ngữ giao diện. Không gửi toàn bộ bảng hay các số đo tới dịch vụ tra cứu.

| Đối tượng | Nguồn cần tìm và kiểm tra |
| --- | --- |
| Quốc gia/lãnh thổ | Ranh giới và mã ISO từ nguồn chính thức hoặc bộ dữ liệu công khai như Natural Earth; phân biệt quốc gia, lãnh thổ và vùng áp dụng riêng. |
| Tỉnh, huyện hoặc cấp hành chính khác | Nguồn hành chính chính thức, geoBoundaries hoặc bộ ranh giới có nguồn gốc và giấy phép phù hợp. Kiểm tra cấp, vùng cha và năm; cùng tên không đủ để ghép. |
| Địa danh, địa chỉ, cơ sở | Nguồn tọa độ công khai, dữ liệu mở hoặc dịch vụ geocoding phù hợp. Xác minh kết quả thuộc đúng địa điểm và đúng độ chi tiết; tuân thủ giới hạn truy vấn của dịch vụ, không đặt geocode hàng loạt không kiểm soát trong trình duyệt. |
| Đường, sông, tuyến | Dữ liệu đường/tuyến thật có mã hoặc tên và ngữ cảnh phù hợp. Không dùng đường thẳng nối hai địa danh để giả làm tuyến thực. |
| Luồng đi–đến | Xác minh từng đầu từ geometry hoặc tọa độ có nguồn; giữ nguyên quan hệ và lưu lượng trong input. Cung nối minh họa luồng, không phải đường đi thực tế. |
| Nhiều lớp | Giải quyết nguồn và khóa ghép cho từng lớp riêng; không áp nguồn của lớp thứ nhất cho mọi lớp. |

Các tên nguồn trên là gợi ý cho phần còn thiếu sau khi kiểm tra kho cục bộ, không phải danh sách bắt buộc. Ưu tiên nguồn caller cung cấp. Với nguồn tự tìm, mở và kiểm tra dữ liệu thực thay vì chỉ dựa vào đoạn trích kết quả tìm kiếm; giữ URL, phiên bản/ngày ranh giới, trường ID/tên và attribution trong cấu hình JS. Kiểm tra điều kiện sử dụng trước khi chọn nguồn, không chọn dịch vụ cần khóa bí mật nếu caller chưa cung cấp cơ chế dùng khóa.

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
