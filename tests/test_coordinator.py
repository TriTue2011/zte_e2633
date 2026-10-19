"""Mức coordinator và thực thể trên Home Assistant THẬT (lớp lõi của HA), máy chủ ZTE giả cục bộ.

Cần gói `homeassistant` (Python 3.13+); thiếu thì cả file được bỏ qua. Không cần pytest-homeassistant-custom-component.
Máy chủ giả KHÔNG chứng minh ZTE thật xử lý giống vậy.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.json import json_bytes

    from custom_components.zte_e2633 import ZteCoordinator
    from custom_components.zte_e2633.device_tracker import ZteMayTracker
    from custom_components.zte_e2633.sensor import ZteMayWifiSensor
    CO_HA = True
except ImportError:  # không có Home Assistant trong môi trường kiểm
    CO_HA = False

from may_chu_gia import MK, clients_lon, dung_may_chu  # noqa: E402

MAC_DAU = "02:00:00:00:00:01"  # máy đầu tiên trong fixture
GIOI_HAN_RECORDER = 16384  # homeassistant.components.recorder.db_schema.MAX_STATE_ATTRS_BYTES


@unittest.skipUnless(CO_HA, "không có Home Assistant")
class CoordinatorTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.may = dung_may_chu()
        cls.clients_goc = dict(cls.may.clients_json)

    @classmethod
    def tearDownClass(cls):
        cls.may.shutdown()
        cls.may.server_close()

    async def asyncSetUp(self):
        self.may.che_do = ""
        self.may.het_phien_luot = 0
        self.may.dem_dang_nhap = 0
        self.may.ten = "user"
        self.may.clients_json = self.clients_goc
        self._thu_muc = tempfile.TemporaryDirectory()
        self.hass = HomeAssistant(self._thu_muc.name)
        self.entry = ConfigEntry(
            version=1, minor_version=1, domain="zte_e2633", title="thu", source="user", unique_id=None,
            discovery_keys={}, subentries_data=None, options={},
            data={"host": f"127.0.0.1:{self.may.server_port}", "ten": "user", "mat_khau": MK, "xac_minh_ssl": False},
        )
        self.entry.async_start_reauth = MagicMock()
        self.cc = ZteCoordinator(self.hass, self.entry)
        # Máy chủ giả chạy HTTP thường (bộ phát thật chạy HTTPS).
        self.cc.client._goc = f"http://127.0.0.1:{self.may.server_port}"

    async def asyncTearDown(self):
        await self.hass.async_stop(force=True)
        self._thu_muc.cleanup()

    def _tracker(self, mac: str = MAC_DAU) -> "ZteMayTracker":
        return ZteMayTracker(self.cc, self.entry, mac)

    # ── Điểm 1: đọc hỏng không đổi trạng thái thiết bị ───────────────────────────────────────────────────
    async def test_doc_hong_khong_doi_trang_thai_thiet_bi(self):
        await self.cc.async_refresh()
        self.assertTrue(self.cc.last_update_success)
        tracker = self._tracker()
        self.assertTrue(tracker.available)
        self.assertTrue(tracker.is_connected)
        du_cu = self.cc.data

        for che_do in ("rot", "rac", "boot"):
            with self.subTest(che_do=che_do):
                self.may.che_do = che_do
                self.may.het_phien_luot = 1  # phiên hết hạn → phải đăng nhập lại, chạm đúng kiểu hỏng
                await self.cc.async_refresh()
                self.assertFalse(self.cc.last_update_success)
                self.assertIs(self.cc.data, du_cu, "đọc hỏng không được thay dữ liệu cũ bằng dữ liệu rỗng")
                self.assertFalse(tracker.available, "thực thể phải «không có sẵn», không phải «không ở nhà»")

    async def test_du_lieu_may_hong_la_loi_va_thiet_bi_khong_chuyen_vang(self):
        """Dữ liệu sai kiểu: lỗi đọc thường — không chuyển «vắng», không tạm ngừng, không đòi nhập lại mật khẩu."""
        await self.cc.async_refresh()
        du_cu = self.cc.data
        tracker = self._tracker()
        self.may.clients_json = {"clientsData": "loi"}
        truoc = self.may.dem_dang_nhap
        await self.cc.async_refresh()
        self.assertFalse(self.cc.last_update_success)
        self.assertIs(self.cc.data, du_cu)
        self.assertFalse(tracker.available)
        self.entry.async_start_reauth.assert_not_called()
        self.assertEqual(self.may.dem_dang_nhap, truoc, "phiên còn tốt thì không đăng nhập lại")
        self.may.clients_json = self.clients_goc  # dữ liệu tốt trở lại → đọc được ngay ở lượt kế tiếp
        await self.cc.async_refresh()
        self.assertTrue(self.cc.last_update_success)
        self.assertTrue(tracker.available)
        self.assertTrue(tracker.is_connected)

    async def test_bo_phat_doi_ten_truong_khong_lam_moi_thiet_bi_chuyen_vang(self):
        """Có mục nhưng không đọc nổi mục nào (đổi tên trường MAC): lỗi đọc, giữ dữ liệu cũ, không «not_home» hàng loạt."""
        await self.cc.async_refresh()
        du_cu = self.cc.data
        tracker = self._tracker()
        self.may.clients_json = {"clientsData": {k: {"Mac": v["MacAddr"]} for k, v in self.clients_goc["clientsData"].items()
                                                  if isinstance(v, dict)}}
        truoc = self.may.dem_dang_nhap
        await self.cc.async_refresh()
        self.assertFalse(self.cc.last_update_success)
        self.assertIs(self.cc.data, du_cu)
        self.assertFalse(tracker.available)
        self.entry.async_start_reauth.assert_not_called()
        self.assertEqual(self.may.dem_dang_nhap, truoc)

    async def test_may_thuc_su_roi_wifi_thi_chuyen_vang(self):
        """Đối chứng: đọc THÀNH CÔNG mà máy không còn trong danh sách thì mới là «vắng»."""
        await self.cc.async_refresh()
        tracker = self._tracker()
        self.assertTrue(tracker.is_connected)
        moi = {k: v for k, v in self.clients_goc["clientsData"].items() if not (isinstance(v, dict) and v.get("MacAddr") == MAC_DAU)}
        self.may.clients_json = {"clientsData": moi}
        await self.cc.async_refresh()
        self.assertTrue(self.cc.last_update_success)
        self.assertTrue(tracker.available)
        self.assertFalse(tracker.is_connected)

    # ── Điểm 2/4: phiên hết hạn, backoff ─────────────────────────────────────────────────────────────────
    async def test_phien_het_han_dang_nhap_lai_dung_mot_lan(self):
        await self.cc.async_refresh()
        self.assertEqual(self.may.dem_dang_nhap, 1)
        self.may.het_phien_luot = 1
        await self.cc.async_refresh()
        self.assertTrue(self.cc.last_update_success)
        self.assertEqual(self.may.dem_dang_nhap, 2)

    async def test_mat_mang_khong_dat_backoff_va_hoi_phuc_ngay_khi_bo_phat_song_lai(self):
        await self.cc.async_refresh()
        for che_do in ("rot", "boot"):
            self.may.che_do = che_do
            self.may.het_phien_luot = 1  # buộc đăng nhập lại để chạm trang lạ
            await self.cc.async_refresh()
            self.assertFalse(self.cc.last_update_success)
        self.entry.async_start_reauth.assert_not_called()
        self.may.che_do = ""
        truoc = self.may.dem_dang_nhap
        await self.cc.async_refresh()
        self.assertTrue(self.cc.last_update_success, "bộ phát sống lại là phải đọc được ngay, không đợi hết backoff")
        self.assertGreater(self.may.dem_dang_nhap, truoc, "lần này phải thật sự đăng nhập, không bị chặn bởi backoff")

    async def test_bi_tu_choi_dang_nhap_thi_backoff_roi_het_han_hoi_phuc(self):
        gia = MagicMock()
        gia.monotonic.return_value = 1000.0
        with patch("custom_components.zte_e2633.time", gia):
            self.may.ten = "nguoi-khac"  # máy chủ giả từ chối tài khoản
            await self.cc.async_refresh()
            self.assertFalse(self.cc.last_update_success)
            self.assertEqual(self.may.dem_dang_nhap, 1)
            self.entry.async_start_reauth.assert_called_once()

            self.may.ten = "user"  # đã sửa nhưng còn trong thời gian tạm ngừng: KHÔNG được gõ mật khẩu nữa
            gia.monotonic.return_value = 1000.0 + 60
            await self.cc.async_refresh()
            self.assertFalse(self.cc.last_update_success)
            self.assertEqual(self.may.dem_dang_nhap, 1, "đang tạm ngừng thì không được đăng nhập")

            gia.monotonic.return_value = 1000.0 + 1801  # hết thời gian tạm ngừng
            await self.cc.async_refresh()
            self.assertTrue(self.cc.last_update_success)
            self.assertEqual(self.may.dem_dang_nhap, 2)

    async def test_go_tich_hop_dong_phien(self):
        from custom_components.zte_e2633 import async_unload_entry
        await self.cc.async_refresh()
        self.assertEqual(self.may.dem_dang_nhap, 1)
        self.hass.data["zte_e2633"] = {self.entry.entry_id: self.cc}
        self.hass.config_entries = MagicMock()
        self.hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        self.assertTrue(await async_unload_entry(self.hass, self.entry))
        await self.cc.async_refresh()  # sau khi gỡ, phiên cũ đã bị xoá nên phải đăng nhập mới
        self.assertEqual(self.may.dem_dang_nhap, 2)

    # ── Điểm 3: thuộc tính không vượt giới hạn recorder ──────────────────────────────────────────────────
    async def test_thuoc_tinh_duoc_ghi_vao_recorder_khong_vuot_16kb_voi_150_may(self):
        self.may.clients_json = clients_lon(150)
        await self.cc.async_refresh()
        self.assertEqual(len(self.cc.data["clients"]), 150)
        cam_bien = ZteMayWifiSensor(self.cc, self.entry)
        thuoc_tinh = cam_bien.extra_state_attributes
        self.assertEqual(cam_bien._unrecorded_attributes, frozenset({"clients", "ap"}))
        self.assertEqual(len(thuoc_tinh["clients"]), 150, "thẻ MikroTik vẫn nhận đủ danh sách trong trạng thái")
        # Recorder (db_schema.py) bỏ các thuộc tính trong _unrecorded_attributes rồi mới đo 16384 byte.
        duoc_ghi = {k: v for k, v in thuoc_tinh.items() if k not in cam_bien.__class__._unrecorded_attributes}
        kich_thuoc = len(json_bytes(duoc_ghi))
        self.assertLess(kich_thuoc, GIOI_HAN_RECORDER // 2, f"{kich_thuoc} byte")
        # Đối chứng: nếu không loại `clients` khỏi recorder thì vượt giới hạn — tức test này có đo đúng thứ cần đo.
        self.assertGreater(len(json_bytes(thuoc_tinh)), GIOI_HAN_RECORDER)

    async def test_clients_giu_dung_cac_truong_the_mikrotik_doc(self):
        """Thẻ đọc mac, ip, name, band, rssi, mode từ `clients` (đã grep mikrotik-topo-lan-card.js): mất trường nào là thẻ hỏng."""
        await self.cc.async_refresh()
        may = ZteMayWifiSensor(self.cc, self.entry).extra_state_attributes["clients"][0]
        self.assertEqual(set(may), {"mac", "ip", "name", "band", "rssi", "mode"})
        goc = self.clients_goc["clientsData"]["1"]
        self.assertEqual((may["mac"], may["ip"], may["rssi"], may["band"], may["mode"]),
                         (goc["MacAddr"], goc["IpAddr"], int(goc["Rssi"]), "2.4G", goc["WirelessMode"]))


if __name__ == "__main__":
    unittest.main()
