"""Lớp mạng: đọc hỏng phải thành LỖI đúng loại, không thành «không có máy nào»; phiên được đóng/xoá đúng.

Chạy trên máy chủ giả cục bộ (không cần Home Assistant). Không chứng minh ZTE thật xử lý giống vậy.
"""
from __future__ import annotations

import io
import logging
import re
import unittest
import urllib.error

from may_chu_gia import MK, clients_lon, dung_may_chu  # noqa: E402
from zte_e2633.api import ZteE2633, ZteLoiDangNhap, ZteLoiKetNoi  # noqa: E402  (gói giả đã nạp bởi test_zte_e2633)
from zte_e2633.parser import DuLieuSaiKhuon, phan_tich_thiet_bi  # noqa: E402


class HoiPhucTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.may = dung_may_chu()
        cls.clients_goc = dict(cls.may.clients_json)
        cls.ap_goc = dict(cls.may.ap_json)

    @classmethod
    def tearDownClass(cls):
        cls.may.shutdown()
        cls.may.server_close()

    def setUp(self):
        self.may.che_do = ""
        self.may.het_phien_luot = 0
        self.may.dem_dang_nhap = 0
        self.may.ten = "user"
        self.may.clients_json = self.clients_goc

    def _client(self) -> ZteE2633:
        return ZteE2633(f"127.0.0.1:{self.may.server_port}", "user", MK, scheme="http", thoi_gian_cho=5)

    # ── Điểm 1: đọc hỏng là LỖI, không phải danh sách rỗng ───────────────────────────────────────────────
    def test_trang_dang_nhap_hoac_thieu_khoa_la_phien_mat_thi_loi_dang_nhap(self):
        """Không có khối dữ liệu nào: phiên mất. Đăng nhập lại đúng một lần, vẫn không có → bị từ chối."""
        self.may.clients_json = {"khong_co_clientsData": 1}
        with self.assertRaises(ZteLoiDangNhap):
            self._client().doc_thiet_bi()
        self.assertEqual(self.may.dem_dang_nhap, 1)

    def test_khoi_du_lieu_sai_kieu_la_loi_doc_khong_phai_danh_sach_rong_cung_khong_phai_tu_choi(self):
        """Có khoá clientsData nghĩa là phiên còn tốt; kiểu lạ là đọc hỏng (lỗi kết nối), không đăng nhập lại thêm."""
        for hong in ({"clientsData": "loi"}, {"clientsData": ["a"]}, {"clientsData": None}, {"clientsData": 7}):
            with self.subTest(hong=hong):
                self.may.clients_json = hong
                self.may.dem_dang_nhap = 0
                with self.assertRaises(ZteLoiKetNoi):
                    self._client().doc_thiet_bi()
                self.assertEqual(self.may.dem_dang_nhap, 1, "không được đăng nhập lại chỉ vì dữ liệu sai kiểu")

    def test_bo_phat_that_su_khong_co_may_nao_la_danh_sach_rong_hop_le(self):
        self.may.clients_json = {"clientsData": {"MGET_INST_NUM": 0}}
        self.assertEqual(self._client().doc_thiet_bi()["clients"], [])

    # ── Điểm 2: phân loại lỗi (từ chối đăng nhập ≠ mất mạng/trang lạ) và phiên ────────────────────────────
    def test_sai_mat_khau_la_tu_choi_dang_nhap(self):
        self.may.ten = "nguoi-khac"
        with self.assertRaises(ZteLoiDangNhap):
            self._client().doc_thiet_bi()

    def test_trang_khong_co_token_khong_phai_tu_choi_dang_nhap(self):
        """Bộ phát đang khởi động lại trả trang lạ: là lỗi kết nối (tự hồi phục), không phải bị từ chối."""
        self.may.che_do = "boot"
        with self.assertRaises(ZteLoiKetNoi):
            self._client().doc_thiet_bi()

    def test_ma_http_loi_o_trang_lay_token_la_loi_ket_noi_co_ghi_ma(self):
        self.may.che_do = "http500"
        with self.assertRaises(ZteLoiKetNoi) as cm:
            self._client().doc_thiet_bi()
        self.assertIn("500", str(cm.exception))

    def test_phan_hoi_khong_phai_http_thanh_loi_ket_noi(self):
        self.may.che_do = "rac"
        with self.assertRaises(ZteLoiKetNoi):
            self._client().doc_thiet_bi()

    def test_dong_ket_noi_giua_chung_thanh_loi_ket_noi(self):
        self.may.che_do = "rot"
        with self.assertRaises(ZteLoiKetNoi):
            self._client().doc_thiet_bi()

    def test_dang_xuat_xoa_phien_phia_may_khach(self):
        """E2633 chưa có điểm đăng xuất nào được kiểm chứng: đăng xuất = xoá cookie và cờ phiên, lần đọc sau đăng nhập mới."""
        c = self._client()
        c.doc_thiet_bi()
        self.assertEqual(self.may.dem_dang_nhap, 1)
        c.dang_xuat()
        self.assertEqual(len(c._jar), 0)
        c.doc_thiet_bi()
        self.assertEqual(self.may.dem_dang_nhap, 2)
        c.dang_xuat()
        c.dang_xuat()  # gọi lặp không lỗi

    def test_trang_token_rong_la_loi_ket_noi_khong_phai_tu_choi(self):
        self.may.che_do = "token_rong"
        with self.assertRaises(ZteLoiKetNoi):
            self._client().doc_thiet_bi()

    def test_khoi_bo_phat_khong_bat_buoc_sai_kieu_thi_van_doc_duoc_may(self):
        for hong in ({"apData": "loi"}, {"apData": None}, {"khong_co": 1}):
            with self.subTest(hong=hong):
                self.may.ap_json = hong
                kq = self._client().doc_thiet_bi()
                self.assertTrue(kq["clients"])
                self.assertEqual(kq["ap"], {})
        self.may.ap_json = self.ap_goc

    def test_phan_hoi_loi_http_duoc_dong(self):
        """HTTPError giữ socket mở nếu không đóng (ResourceWarning): _doc phải đóng nó trước khi ném lỗi của mình."""
        c = self._client()
        fp = io.BytesIO(b"loi")
        loi = urllib.error.HTTPError("http://x/", 500, "loi", {}, fp)

        def _mo(*_a, **_k):
            raise loi
        c._mo.open = _mo
        with self.assertRaises(ZteLoiKetNoi):
            c.doc_thiet_bi()
        self.assertTrue(fp.closed)

    # ── Điểm 3: kích thước ───────────────────────────────────────────────────────────────────────────────
    def test_150_may_van_doc_du(self):
        self.may.clients_json = clients_lon(150)
        self.assertEqual(len(self._client().doc_thiet_bi()["clients"]), 150)
        self.assertEqual(len(phan_tich_thiet_bi(clients_lon(150))), 150)


class DocMucTest(unittest.TestCase):
    """«Có mục mà không đọc nổi mục nào» là đọc hỏng; chỉ khi bộ phát báo rõ 0 máy mới là «không có máy»."""

    def _may(self, mac="02:00:00:00:00:0%d", khoa="MacAddr", n=3):
        return {str(i): {khoa: mac % i, "HostName": "x"} for i in range(1, n + 1)}

    def test_bo_phat_doi_ten_truong_mac_la_loi_khong_phai_khong_co_may(self):
        with self.assertRaises(DuLieuSaiKhuon):
            phan_tich_thiet_bi({"clientsData": self._may(khoa="Mac")})

    def test_moi_muc_khong_phai_doi_tuong_la_loi(self):
        with self.assertRaises(DuLieuSaiKhuon):
            phan_tich_thiet_bi({"clientsData": {"1": "a", "2": "b"}})

    def test_moi_muc_co_mac_sai_khuon_la_loi(self):
        with self.assertRaises(DuLieuSaiKhuon):
            phan_tich_thiet_bi({"clientsData": self._may(mac="khong-phai-mac-%d")})

    def test_bao_so_may_lon_hon_0_ma_khong_co_muc_nao_la_loi(self):
        with self.assertRaises(DuLieuSaiKhuon):
            phan_tich_thiet_bi({"clientsData": {"MGET_INST_NUM": 3}})

    def test_mot_phan_muc_hong_thi_giu_muc_doc_duoc_va_ghi_log_debug_so_muc_bo(self):
        du = {"clientsData": {**self._may(n=2), "3": "rac", "4": {"MacAddr": "hong"}, "MGET_INST_NUM": 4}}
        with self.assertLogs("zte_e2633.parser", level="DEBUG") as log:
            ds = phan_tich_thiet_bi(du)
        self.assertEqual(len(ds), 2)
        self.assertTrue(any("2" in d and "bỏ" in d for d in log.output), log.output)
        self.assertFalse(any("hong" in d or "rac" in d for d in log.output), "log không chứa giá trị của bộ phát")

    def test_rong_hop_le_la_khong_co_may(self):
        for rong in ({"MGET_INST_NUM": 0}, {}, []):
            with self.subTest(rong=rong):
                self.assertEqual(phan_tich_thiet_bi({"clientsData": rong}), [])

    def test_tu_api_doi_ten_truong_thanh_loi_ket_noi_khong_dang_nhap_lai(self):
        may = dung_may_chu()
        try:
            may.clients_json = {"clientsData": self._may(khoa="Mac")}
            with self.assertRaises(ZteLoiKetNoi):
                ZteE2633(f"127.0.0.1:{may.server_port}", "user", MK, scheme="http", thoi_gian_cho=5).doc_thiet_bi()
            self.assertEqual(may.dem_dang_nhap, 1)
        finally:
            may.shutdown()
            may.server_close()


class NhatKyTest(unittest.TestCase):
    """Log debug của lớp API: mốc đăng nhập/đọc/lỗi, TUYỆT ĐỐI không có mật khẩu, token, cookie, MAC, IP, tên máy."""

    CAM = [MK, "tok-gia", "98765", "SID", "Check", "02:00:00:00", "127.0.0.1", "192.168", "Thiết bị WiFi", "user"]

    @classmethod
    def setUpClass(cls):
        cls.may = dung_may_chu()

    @classmethod
    def tearDownClass(cls):
        cls.may.shutdown()
        cls.may.server_close()

    def setUp(self):
        self.may.che_do = ""
        self.may.het_phien_luot = 0
        self.may.dem_dang_nhap = 0

    def _client(self):
        return ZteE2633(f"127.0.0.1:{self.may.server_port}", "user", MK, scheme="http", thoi_gian_cho=5)

    def _sach(self, log):
        van_ban = "\n".join(log.output)
        for cam in self.CAM:
            self.assertNotIn(cam, van_ban)
        self.assertIsNone(re.search(r"\b[0-9a-f]{32,}\b", van_ban))
        return van_ban

    def test_cac_moc_khi_doc_binh_thuong_va_khi_phien_het_han(self):
        c = self._client()
        with self.assertLogs("zte_e2633.api", level="DEBUG") as log:
            c.doc_thiet_bi()
            self.may.het_phien_luot = 1
            c.doc_thiet_bi()
        van_ban = self._sach(log)
        self.assertIn("bắt đầu đăng nhập", van_ban)
        self.assertIn("đăng nhập xong", van_ban)
        self.assertIn("phiên hết hạn", van_ban)
        self.assertRegex(van_ban, r"đọc xong \d+ máy")
        self.assertEqual(van_ban.count("phiên hết hạn"), 1)

    def test_phan_loai_loi_ghi_loai_va_ma_http_khong_ghi_dia_chi(self):
        self.may.che_do = "http500"
        with self.assertLogs("zte_e2633.api", level="DEBUG") as log:
            with self.assertRaises(ZteLoiKetNoi):
                self._client().doc_thiet_bi()
        van_ban = self._sach(log)
        self.assertIn("ZteLoiKetNoi", van_ban)
        self.assertIn("500", van_ban)
        self.may.che_do = ""
        self.may.ten = "nguoi-khac"
        with self.assertLogs("zte_e2633.api", level="DEBUG") as log:
            with self.assertRaises(ZteLoiDangNhap):
                self._client().doc_thiet_bi()
        self.assertIn("ZteLoiDangNhap", self._sach(log))
        self.may.ten = "user"


if __name__ == "__main__":
    unittest.main()
