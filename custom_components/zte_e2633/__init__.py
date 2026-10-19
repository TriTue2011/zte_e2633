"""ZTE E2633: đọc danh sách máy WiFi thành cảm biến (card MikroTik `clients_sensor`) và theo dõi từng máy."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ZteE2633, ZteLoiDangNhap, ZteLoiKetNoi
from .const import (
    CHU_KY_MAC_DINH,
    CONF_CHU_KY,
    CONF_HOST,
    CONF_MAT_KHAU,
    CONF_TEN,
    CONF_XAC_MINH_SSL,
    DOMAIN,
    THOI_GIAN_TAM_DUNG,
)

LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR, Platform.DEVICE_TRACKER]


class ZteCoordinator(DataUpdateCoordinator):
    """Giữ một phiên đăng nhập, đọc định kỳ. Sau lỗi đăng nhập thì tạm ngừng, không gõ mật khẩu liên tục."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        # Tuỳ chọn (nút bánh răng) ghi đè dữ liệu lúc thêm: chỉ chu kỳ đọc và kiểm chứng HTTPS đổi được.
        cau_hinh = {**entry.data, **entry.options}
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=cau_hinh.get(CONF_CHU_KY, CHU_KY_MAC_DINH)),
        )
        self.client = ZteE2633(
            cau_hinh[CONF_HOST],
            cau_hinh[CONF_TEN],
            cau_hinh[CONF_MAT_KHAU],
            xac_minh_ssl=cau_hinh.get(CONF_XAC_MINH_SSL, False),
        )
        self._tam_dung_den = 0.0

    async def _async_update_data(self):
        if time.monotonic() < self._tam_dung_den:
            raise UpdateFailed("tạm ngừng đăng nhập sau lỗi trước để tránh khoá tài khoản quản trị của bộ phát")
        try:
            return await self.hass.async_add_executor_job(self.client.doc_thiet_bi)
        except ZteLoiDangNhap as loi:
            self._tam_dung_den = time.monotonic() + THOI_GIAN_TAM_DUNG
            raise ConfigEntryAuthFailed(str(loi)) from loi
        except ZteLoiKetNoi as loi:
            raise UpdateFailed(str(loi)) from loi


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = ZteCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_khi_tuy_chon_doi))
    return True


async def _khi_tuy_chon_doi(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Đổi chu kỳ/kiểm chứng HTTPS trong tuỳ chọn: nạp lại tích hợp để áp dụng."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id, None)
        if coordinator is not None:
            coordinator.client.dang_xuat()  # chỉ quên phiên phía máy khách (xem ZteE2633.dang_xuat)
    return ok
