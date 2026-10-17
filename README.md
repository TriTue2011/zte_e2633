# ZTE E2633 (máy WiFi) — tích hợp Home Assistant

Đọc danh sách máy đang kết nối WiFi của bộ phát **ZTE E2633** (bản China Mobile, phần mềm V1.0.4) thành một
cảm biến. Dùng cùng card `mikrotik-topo-lan-card` qua tuỳ chọn `access_points[].clients_sensor`, để biết
**máy nào vào WiFi, dùng băng tần nào, tín hiệu bao nhiêu**.

## Chỉ đọc
- Không ghi cấu hình, không đổi mật khẩu, không bật/tắt gì trên bộ phát.
- Mỗi lần đọc chỉ đăng nhập tối đa một lần. Sau lỗi đăng nhập, tích hợp **tạm ngừng 30 phút** để không gõ
  mật khẩu liên tục (tránh khoá tài khoản quản trị).
- Mật khẩu chỉ lưu trong cấu hình Home Assistant, không ghi vào log hay thông báo lỗi.

## Cài đặt
1. Chép thư mục `custom_components/zte_e2633` vào `config/custom_components/` của Home Assistant, hoặc thêm repo này
   vào HACS dưới dạng kho tuỳ chỉnh (loại Integration).
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

## Trạng thái kiểm chứng (nói thật)
- Phần đọc JSON và luồng đăng nhập được kiểm bằng **máy chủ giả cục bộ** (`python3 -m unittest discover -s tests -p "test_*.py"`).
  Máy chủ giả mô phỏng đúng luồng đọc từ mã trang đăng nhập của thiết bị, nhưng **chưa kiểm trên ZTE thật**.
- Phần giao diện cấu hình và cảm biến của Home Assistant **chưa chạy thử**: môi trường kiểm không có Home Assistant.
  Cần chủ máy thêm tích hợp trên Home Assistant thật và báo kết quả.
- Nếu ZTE trả «页面过期» (trang hết hạn) sau khi đăng nhập, nguyên nhân có thể là khác biệt giữa luồng này và
  trình duyệt. Khi đó cần bản ghi yêu cầu mạng lúc đăng nhập bằng trình duyệt (chỉ tên trường, không giá trị).

## Phát triển
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
