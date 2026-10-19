# ZTE E2633 (máy WiFi) — tích hợp Home Assistant

Đọc danh sách máy đang kết nối WiFi của bộ phát **ZTE E2633** (bản China Mobile, phần mềm V1.0.4) thành một
cảm biến. Dùng cùng card `mikrotik-topo-lan-card` qua tuỳ chọn `access_points[].clients_sensor`, để biết
**máy nào vào WiFi, dùng băng tần nào, tín hiệu bao nhiêu**.

## Có gì
- **Mỗi máy WiFi là một thiết bị** (theo địa chỉ MAC, tên theo tên máy) với một thực thể theo dõi `device_tracker`: có mặt khi bộ phát
  còn thấy máy, «không ở nhà» khi vắng. Máy mới vào WiFi tự được thêm; máy đã từng thấy vẫn còn sau khi khởi động lại Home Assistant.
  Thuộc tính mỗi máy: `band`, `rssi`, `mode`, `assoc_s`, `ip_address`, `mac_address`, cùng mọi trường gốc khác của bộ phát.
- **Cảm biến theo từng máy**, nằm trong chính thiết bị của máy đó: Cường độ tín hiệu (dBm), Băng tần, Chế độ WiFi, Địa chỉ IP,
  Thời gian kết nối.
  **Không có tốc độ nhận/gửi theo máy**: bộ phát E2633 luôn trả 0 cho các trường tốc độ (đã thử khi máy đang xem video), nên
  tích hợp không tạo cảm biến đó. Tốc độ từng máy lấy từ router MikroTik (Kid Control) nếu cần. Máy vắng thì các cảm biến này «không có sẵn».
- **Hiển thị hết**: mọi trường bộ phát trả về cho máy hoặc cho bộ phát đều hiện (chuẩn hoá hoặc nguyên tên gốc trong thuộc tính của
  thực thể theo dõi / cảm biến **Bộ phát**), kể cả trường mới nếu phần mềm bộ phát thêm.
- Cảm biến **Máy WiFi** (tổng số máy, thuộc tính `clients` cho card MikroTik), **Máy WiFi 2.4G** và **Máy WiFi 5G** (đếm theo băng tần).
- Nút bánh răng (**Tuỳ chọn**): đổi chu kỳ đọc và kiểm chứng HTTPS mà không phải thêm lại.

## Chỉ đọc
- Không ghi cấu hình, không đổi mật khẩu, không bật/tắt gì trên bộ phát.
- Mỗi lần đọc chỉ đăng nhập tối đa một lần. Khi bộ phát **từ chối** đăng nhập (đăng nhập xong mà vẫn không đọc được danh sách máy),
  tích hợp **tạm ngừng 30 phút** và yêu cầu nhập lại mật khẩu để không gõ mật khẩu liên tục (tránh khoá tài khoản quản trị).
  **Mất mạng, bộ phát đang khởi động lại, mã HTTP lỗi hay phản hồi lạ không bị tạm ngừng**: đọc thất bại, thực thể chuyển «không có sẵn»
  (không chuyển «không ở nhà»), và tự đọc lại ở chu kỳ kế tiếp ngay khi bộ phát sống lại.
- Đọc thất bại luôn là **lỗi**, không bao giờ là «không có máy nào»: dữ liệu trả về sai khuôn bị coi là đọc hỏng.
- Phiên đăng nhập: khi gỡ tích hợp, phiên phía Home Assistant bị quên (xoá cookie). **Chưa có điểm đăng xuất phía bộ phát nào được kiểm
  chứng trên E2633** nên tích hợp không gửi yêu cầu đăng xuất đoán mò; phiên phía bộ phát tự hết hạn theo thời gian chờ của nó.
- Mật khẩu chỉ lưu trong cấu hình Home Assistant, không ghi vào log hay thông báo lỗi.

## Cài đặt
1. HACS → ⋮ → Kho tuỳ chỉnh → `https://github.com/TriTue2011/zte_e2633` → loại *Integration* → Tải xuống. Hoặc chép thư mục
   `custom_components/zte_e2633` vào `config/custom_components/` của Home Assistant.
2. Khởi động lại Home Assistant. Vào **Cài đặt → Thiết bị & dịch vụ → Thêm tích hợp → ZTE E2633**.
3. Nhập địa chỉ (ví dụ `192.168.1.1`), tên đăng nhập và mật khẩu quản trị của bộ phát.
   Tích hợp đăng nhập thử một lần; báo lỗi thì không được thêm.
4. Tìm cảm biến **Máy WiFi** trong **Công cụ phát triển → Trạng thái** (tên thực thể phụ thuộc địa chỉ, ví dụ
   `sensor.zte_e2633_192_168_1_1_may_wifi`). Trạng thái là số máy; thuộc tính `clients` là danh sách máy.

Dùng trên card MikroTik:
```yaml
access_points:
  - name: ZTE WiFi
    port: ether2
    clients_sensor: sensor.zte_e2633_192_168_1_1_may_wifi
```

## Tuỳ chọn
- **Kiểm chứng chứng chỉ HTTPS**: mặc định tắt, vì bộ phát dùng chứng chỉ tự ký trong mạng nhà. Chỉ bật khi bộ phát
  có chứng chỉ hợp lệ.
- **Chu kỳ đọc**: 30–600 giây, mặc định 60.

## Dữ liệu cảm biến
| Thuộc tính | Nội dung |
|---|---|
| `clients` | Danh sách máy: `mac`, `ip`, `name`, `band` (`2.4G`/`5G`), `rssi` (dBm), `mode` |
| `ap` | Thông tin bộ phát: `mac`, `ip`, `name`, `firmware` |

`clients` và `ap` **không được ghi vào lịch sử (recorder)**: với khoảng 85 máy trở lên, danh sách vượt giới hạn 16 KB của recorder và
Home Assistant sẽ bỏ cả các thuộc tính còn lại. Thẻ vẫn đọc đủ danh sách từ trạng thái hiện tại; chỉ không có lịch sử của hai thuộc tính này.

## Trạng thái kiểm chứng (nói thật)
- Phần đọc JSON và luồng đăng nhập được kiểm bằng **máy chủ giả cục bộ** (`python3 -m unittest discover -s tests -p "test_*.py"`).
  Máy chủ giả mô phỏng đúng luồng đọc từ mã trang đăng nhập của thiết bị, nhưng **chưa kiểm trên ZTE thật**. Máy chủ giả do cùng
  tác giả viết theo cùng cách hiểu luồng nên không bắt được chỗ hiểu sai luồng; riêng các kiểu hỏng (mất mạng, trang lạ, mã 500,
  phản hồi rác, phiên hết hạn, bị từ chối) được mô phỏng thêm ở `tests/may_chu_gia.py`.
- Lớp điều phối (`ZteCoordinator`, thực thể theo dõi, cảm biến) được kiểm ở `tests/test_coordinator.py` bằng **lõi Home Assistant thật**
  (gói `homeassistant`, Python 3.13+) nói chuyện với máy chủ giả; thiếu gói thì file đó tự bỏ qua. Màn hình cấu hình (config flow) và việc
  thêm tích hợp vào một Home Assistant đang chạy **chưa chạy thử**; cần chủ máy thêm tích hợp trên Home Assistant thật và báo kết quả.
- Luồng đăng nhập (form có header `check` = SHA-256 của đúng body) đã được dùng để đọc danh sách máy WiFi thành công **một lần**
  trên bộ phát thật (17/10/2026) bằng script độc lập; chưa chạy lâu dài. Nếu bộ phát trả «页面过期» (trang hết hạn) thì luồng đã đổi
  theo bản phần mềm — mở issue kèm tên trường (không kèm giá trị) trong yêu cầu đăng nhập của trình duyệt.

## Cách thu log gỡ lỗi đã che
Khi mở issue, đính kèm log để dễ tìm lỗi, nhưng **che trước khi đăng** (kho này công khai).

1. Bật log chi tiết, trong `configuration.yaml` rồi khởi động lại (hoặc dùng dịch vụ `logger.set_level`):
   ```yaml
   logger:
     default: warning
     logs:
       custom_components.zte_e2633: debug
   ```
   Log debug của tích hợp ghi các mốc ngắn, không có bí mật hay địa chỉ: bắt đầu đăng nhập, đăng nhập xong, phiên hết hạn nên đăng nhập lại,
   đọc xong N máy (chỉ số lượng), số mục máy bị bỏ vì sai khuôn, loại lỗi và mã HTTP.
2. Làm lỗi xảy ra một lần, rồi lọc đúng dòng của tích hợp và che:
   ```bash
   grep zte_e2633 config/home-assistant.log | python3 scripts/che_log.py > log_da_che.txt
   ```
   `scripts/che_log.py` (thư viện chuẩn, không cài thêm gì) thay MAC, IPv4, IPv6 bằng nhãn cố định (`MAC-1`, `IP-1`, …: vẫn thấy «cùng một máy»),
   thay tên máy bằng `TEN-n`, tên miền của bộ phát (trong URL hoặc trường `host`) bằng `HOST-n`, `user:pass@` trong URL bằng `***@`, và che mật khẩu, token, cookie phiên, header `Check`, giá trị băm 64 ký tự hex bằng `***`.
3. **Tự đọc lại `log_da_che.txt` trước khi đăng**; công cụ che theo khuôn (MAC, IP, tên trường nhạy cảm), không che hết được mọi thứ.
   Những thứ nó KHÔNG chắc chắn che: địa chỉ MAC dạng Cisco (`aabb.ccdd.ee03`) hoặc 12 ký tự liền (`aabbccddee04`); `entity_id` và
   `friendly_name` (thường chứa tên người hoặc tên máy, ví dụ `device_tracker.iphone_cua_lan`); mật khẩu nằm trong câu chữ tự do hoặc không
   đứng sau tên trường (`password`, `mat_khau`, `token`…); tên miền của bộ phát nếu không nằm trong URL hay trường `host`; tên người,
   email, tên mạng WiFi (SSID). Hãy tự tìm và xoá các thứ đó. Không bao giờ đăng log gốc, ảnh chụp trang quản trị của bộ phát, hay cookie
   của trình duyệt.
4. Nếu báo lỗi đăng nhập trên bộ phát thật, ghi thêm **tên trường** (không kèm giá trị) trong yêu cầu đăng nhập của trình duyệt.

## Thay đổi ở 0.7.0
- Đọc thất bại (dữ liệu sai khuôn, trang lạ, mã HTTP lỗi, phản hồi không phải HTTP) là lỗi → thực thể «không có sẵn», không chuyển «không ở nhà».
- Tạm ngừng đăng nhập 30 phút chỉ khi bộ phát **từ chối**; mất mạng hoặc bộ phát đang khởi động lại tự hồi phục, không bị tạm ngừng.
- Mã HTTP lỗi ở trang lấy token được ghi rõ trong thông báo; gỡ tích hợp thì quên phiên phía Home Assistant.
- `clients` và `ap` của cảm biến **Máy WiFi** không ghi vào recorder (tránh vượt 16 KB khi nhiều máy).
- Truyền `config_entry` cho coordinator (Home Assistant 2026.8 bỏ cách đoán ngầm).
- Bộ phát trả mục máy nhưng không đọc nổi mục nào (đổi tên trường, mục không phải đối tượng, `MGET_INST_NUM` > 0 mà không có mục) là lỗi đọc,
  không phải «không có máy»; chỉ khối rỗng hoặc `MGET_INST_NUM` = 0 mới là không có máy. Chỉ một phần mục hỏng thì giữ các mục đọc được và ghi
  log DEBUG số mục bị bỏ.
- Thêm log DEBUG ngắn ở lớp API (không chứa bí mật/MAC/IP/tên máy); `HTTPError` được đóng để không rò socket.
- Thêm `scripts/che_log.py` (che cả `user:pass@` trong URL, tên miền bộ phát, mật khẩu có khoảng trắng/nháy; không che nhầm số phiên bản) và
  mục thu log đã che; thêm test mức coordinator và các kiểu hỏng mạng.

## Chưa kiểm trên bộ phát thật (biết rồi, chưa sửa vì sửa mù có thể làm hỏng)
- Sau khi đã có phiên, mọi lỗi HTTP (401/403…) hoặc JSON sai khuôn đều là lỗi kết nối và **không** đăng nhập lại. Nếu bộ phát báo hết phiên
  bằng mã HTTP thì thực thể kẹt «không có sẵn» tới khi nạp lại tích hợp. Cần quan sát bộ phát thật khi phiên hết hạn mới sửa đúng.
- «Đăng nhập xong mà vẫn không đọc được danh sách máy» gộp hai nguyên nhân (bị từ chối thật, lỗi tạm của bộ phát) và đều hỏi lại mật khẩu
  sau 30 phút tạm ngừng. Chưa có cách phân biệt đáng tin trên bộ phát thật.
- Mỗi lần nạp lại tích hợp hoặc đổi tuỳ chọn để lại một phiên mồ côi phía bộ phát (chưa có điểm đăng xuất được kiểm chứng), phiên tự hết hạn.
- Giả định «danh sách máy rỗng» là khối `{}`/`[]`/`MGET_INST_NUM` = 0 chưa được đối chiếu với bộ phát thật khi không có máy nào.
- Bộ phát thật chưa được kiểm; mọi test chạy trên máy chủ giả do cùng tác giả viết nên không bắt được chỗ hiểu sai luồng thật.

## Chuyển từ `zte_tracker` (bản cũ của kho này)
Kho này từng là bản sao của một dự án khác; nay chỉ chứa mã tự viết, tên tích hợp là `zte_e2633` (khác `zte_tracker`). Sau khi HACS cập nhật:
1. Xoá tích hợp `zte_tracker` cũ trong **Thiết bị & dịch vụ** và thêm **ZTE E2633** (nhập lại địa chỉ, tài khoản, mật khẩu).
2. Cảm biến mới là `sensor.zte_e2633_<địa chỉ>_may_wifi`; sửa `clients_sensor` trong card cho khớp.
3. Thực thể theo dõi từng máy (`device_tracker`) có lại, nhưng tên thực thể có thể khác bản cũ; kiểm tra lại các tự động hoá dùng chúng.

## Icon
Icon/logo là nhãn hiệu của ZTE Corporation, dùng để nhận diện thiết bị. Home Assistant đời mới đọc icon của tích hợp tuỳ chỉnh từ thư mục
`brand/` trong tích hợp; bản cũ hơn có thể vẫn hiện «icon not available» (chỉ là hiển thị).

## Phát triển
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
Test lớp điều phối cần gói `homeassistant` (Python 3.13+): `uv venv --python 3.13 && uv pip install homeassistant` rồi chạy lệnh trên bằng Python của môi trường đó.

Chạy bằng `pytest`: nếu môi trường có `pytest-homeassistant-custom-component`, plugin này chặn socket và đổi vòng lặp sự kiện nên hàng chục test
lỗi dù mã đúng. Chạy `pytest tests -p no:homeassistant` (tắt plugin) thì đạt như `unittest`. Không thêm được `conftest.py` để tự xử lý, vì plugin chạy
trước và can thiệp cả vòng lặp sự kiện của các test `IsolatedAsyncioTestCase`; `unittest discover` mới là cách chạy chính.
