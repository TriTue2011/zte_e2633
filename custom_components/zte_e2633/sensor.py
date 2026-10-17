"""Cảm biến «Máy WiFi»: trạng thái là số máy đang kết nối; thuộc tính `clients` đúng khuôn card MikroTik đọc."""
from __future__ import annotations

import re

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.helpers import entity_registry as er
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .parser import dem_theo_bang

# Chỉ đưa các trường card cần và đủ nhỏ để không vượt giới hạn thuộc tính của Home Assistant.
TRUONG_MAY = ("mac", "ip", "name", "band", "rssi", "mode", "rx_bps", "tx_bps", "rx_mbps", "tx_mbps")


def dong_gon_may(clients: list[dict]) -> list[dict]:
    return [{k: m.get(k) for k in TRUONG_MAY} for m in clients]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ZteMayWifiSensor(coordinator, entry),
        ZteMayTheoBangSensor(coordinator, entry, "2.4G"),
        ZteMayTheoBangSensor(coordinator, entry, "5G"),
        ZteBoPhatSensor(coordinator, entry),
    ])
    _them_cam_bien_tung_may(hass, entry, coordinator, async_add_entities)


class ZteMayWifiSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Máy WiFi"
    _attr_icon = "mdi:wifi"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_may_wifi"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ZTE E2633 {entry.data[CONF_HOST]}",
            manufacturer="ZTE",
            model="E2633",
        )

    @property
    def native_value(self) -> int | None:
        du = self.coordinator.data
        return len(du["clients"]) if du else None

    @property
    def extra_state_attributes(self) -> dict:
        du = self.coordinator.data or {"clients": [], "ap": {}}
        return {
            "clients": dong_gon_may(du["clients"]),
            "ap": du["ap"],
        }


class ZteMayTheoBangSensor(CoordinatorEntity, SensorEntity):
    """Số máy đang kết nối ở một băng tần (2.4G hoặc 5G)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:wifi"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry: ConfigEntry, bang: str) -> None:
        super().__init__(coordinator)
        self._bang = bang
        self._attr_name = f"Máy WiFi {bang}"
        self._attr_unique_id = f"{entry.entry_id}_may_{bang.lower().replace('.', '_')}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self) -> int | None:
        du = self.coordinator.data
        return dem_theo_bang(du["clients"], self._bang) if du else None


class ZteBoPhatSensor(CoordinatorEntity, SensorEntity):
    """Thông tin bộ phát: trạng thái là phiên bản phần mềm; thuộc tính là mọi trường bộ phát trả về."""

    _attr_has_entity_name = True
    _attr_name = "Bộ phát"
    _attr_icon = "mdi:router-wireless"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_bo_phat"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def native_value(self) -> str | None:
        ap = (self.coordinator.data or {}).get("ap") or {}
        return ap.get("firmware") or ap.get("name") or None

    @property
    def extra_state_attributes(self) -> dict:
        ap = (self.coordinator.data or {}).get("ap") or {}
        ra = {k: v for k, v in ap.items() if k != "goc" and v not in (None, "")}
        ra.update(ap.get("goc") or {})
        return ra


# ── Cảm biến theo TỪNG MÁY: nằm trong chính thiết bị của máy đó (cùng thiết bị với thực thể theo dõi) ──────────────

#: loại → (tên hiển thị, khoá trong dữ liệu máy, đơn vị, lớp thiết bị, nhóm thực thể, biểu tượng)
LOAI_CAM_BIEN_MAY = {
    "rssi": ("Cường độ tín hiệu", "rssi", "dBm", SensorDeviceClass.SIGNAL_STRENGTH, None, None),
    "band": ("Băng tần", "band", None, None, None, "mdi:wifi-marker"),
    "mode": ("Chế độ WiFi", "mode", None, None, None, "mdi:wifi-cog"),
    "ip": ("Địa chỉ IP", "ip", None, None, EntityCategory.DIAGNOSTIC, "mdi:ip-network"),
    "rx_mbps": ("Tốc độ nhận", "rx_mbps", "Mbit/s", None, None, "mdi:download-network"),
    "tx_mbps": ("Tốc độ gửi", "tx_mbps", "Mbit/s", None, None, "mdi:upload-network"),
    "assoc_s": ("Thời gian kết nối", "assoc_s", UnitOfTime.SECONDS, SensorDeviceClass.DURATION, None, None),
}
_UNIQUE_MAY_RE = re.compile(r"^(?P<mac>[0-9a-f]{2}(?::[0-9a-f]{2}){5})_(?P<loai>[a-z_0-9]+)$")


def _them_cam_bien_tung_may(hass, entry, coordinator, async_add_entities) -> None:
    """Mỗi máy WiFi một bộ cảm biến. Máy mới vào WiFi tự được thêm; máy đã từng thấy dựng lại sau khi khởi động."""
    da_them: set[tuple[str, str]] = set()
    tien_to = f"{entry.entry_id}_"

    def _dung(mac: str, loai: str) -> ZteMayCamBien | None:
        if loai in LOAI_CAM_BIEN_MAY and (mac, loai) not in da_them:
            da_them.add((mac, loai))
            return ZteMayCamBien(coordinator, entry, mac, loai)
        return None

    cu = []
    for muc in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if muc.domain == "sensor" and muc.unique_id.startswith(tien_to):
            kq = _UNIQUE_MAY_RE.match(muc.unique_id.removeprefix(tien_to))
            if kq and (cb := _dung(kq["mac"], kq["loai"])):
                cu.append(cb)
    if cu:
        async_add_entities(cu)

    @callback
    def _them_moi() -> None:
        moi = []
        for may in (coordinator.data or {}).get("clients", []):
            for loai in LOAI_CAM_BIEN_MAY:
                if (cb := _dung(may["mac"], loai)):
                    moi.append(cb)
        if moi:
            async_add_entities(moi)

    _them_moi()
    entry.async_on_unload(coordinator.async_add_listener(_them_moi))


class ZteMayCamBien(CoordinatorEntity, SensorEntity):
    """Một thông tin của một máy WiFi. Máy vắng thì «không có sẵn»."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry: ConfigEntry, mac: str, loai: str) -> None:
        super().__init__(coordinator)
        ten, self._khoa, don_vi, lop, nhom, bieu_tuong = LOAI_CAM_BIEN_MAY[loai]
        self._mac = mac
        self._entry_id = entry.entry_id
        self._attr_name = ten
        self._attr_unique_id = f"{entry.entry_id}_{mac}_{loai}"
        self._attr_native_unit_of_measurement = don_vi
        self._attr_device_class = lop
        self._attr_entity_category = nhom
        self._attr_icon = bieu_tuong
        if don_vi is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._ten_cuoi = (self._may or {}).get("name") or mac

    @property
    def _may(self) -> dict | None:
        for may in (self.coordinator.data or {}).get("clients", []):
            if may["mac"] == self._mac:
                return may
        return None

    @property
    def device_info(self) -> DeviceInfo:
        # Cùng «kết nối MAC» với thực thể theo dõi → cùng MỘT thiết bị trong Home Assistant.
        return DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            name=self._ten_cuoi,
            via_device=(DOMAIN, self._entry_id),
        )

    @property
    def available(self) -> bool:
        return super().available and self._may is not None

    @property
    def native_value(self):
        may = self._may
        if not may:
            return None
        gia_tri = may.get(self._khoa)
        return gia_tri if gia_tri not in ("",) else None
