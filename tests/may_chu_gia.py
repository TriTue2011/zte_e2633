"""Máy chủ giả có thêm các kiểu hỏng của đường mạng, dùng chung cho các test hồi phục.

Dựng trên `GiaZte` của test_zte_e2633 (đúng luồng đăng nhập đã đọc từ mã trang). `che_do` chọn cách hỏng:
  ""        : bình thường
  "rot"     : đóng kết nối ngay, không trả gì (mất mạng giữa chừng)
  "rac"     : trả byte không phải HTTP
  "boot"    : trang chủ trả HTML không có _sessionTOKEN (bộ phát đang khởi động lại / trang lạ)
  "http500" : trang chủ trả mã 500
  "token_rong": trang lấy token trả về rỗng
"""
from __future__ import annotations

import json
import pathlib
import threading
from http.server import HTTPServer

from test_zte_e2633 import FIX, GiaZte, MK  # noqa: F401  (MK để các test import lại)


class GiaZteLoi(GiaZte):
    def _hong(self, gui_trang: bool) -> bool:
        """True nếu đã xử lý xong yêu cầu này theo kiểu hỏng."""
        che_do = self.server.che_do
        if che_do == "rot":
            self.close_connection = True
            return True
        if che_do == "rac":
            self.wfile.write(b"khong phai http\r\n\r\n")
            self.close_connection = True
            return True
        if gui_trang and che_do == "boot":
            self._gui(200, "<html>he thong dang khoi dong</html>")
            return True
        if gui_trang and che_do == "http500":
            self._gui(500, "loi may chu")
            return True
        return False

    def do_GET(self):
        if self._hong(gui_trang=self.path == "/"):
            return
        if self.server.che_do == "token_rong" and self.path.startswith("/function_module/login_module/login_page/logintoken_lua.lua"):
            return self._gui(200, "<response></response>", "text/xml")
        super().do_GET()

    def do_POST(self):
        if self._hong(gui_trang=False):
            return
        super().do_POST()


def dung_may_chu() -> HTTPServer:
    may = HTTPServer(("127.0.0.1", 0), GiaZteLoi)
    may.ten = "user"
    may.che_do = ""
    may.het_phien_luot = 0
    may.dem_dang_nhap = 0
    may.clients_json = json.loads((FIX / "zte_e2633_clients.json").read_text(encoding="utf-8"))
    may.ap_json = json.loads((FIX / "zte_e2633_ap.json").read_text(encoding="utf-8"))
    threading.Thread(target=may.serve_forever, daemon=True).start()
    return may


def clients_lon(so_may: int) -> dict:
    """JSON GetALLClients giả với `so_may` máy, tên dài tối đa (64 ký tự có dấu) — trường hợp xấu nhất cho kích thước."""
    ten_dai = ("Thiết bị WiFi thử nghiệm có tên rất dài để đo kích thước tối đa " * 3)[:64]
    return {"clientsData": {
        str(i): {"MacAddr": f"02:00:00:00:{i // 256:02x}:{i % 256:02x}", "HostName": ten_dai, "IpAddr": f"192.168.88.{i % 250 + 2}",
                 "Rssi": "-47", "AccessType": "2", "WirelessMode": "802.11ax", "AssocTime": str(1000 + i),
                 "RxRateBps": "0", "TxRateBps": "0"}
        for i in range(1, so_may + 1)
    }}
