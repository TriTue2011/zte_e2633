"""Theo dõi từng máy WiFi: mỗi địa chỉ MAC là một thiết bị với một thực thể «có mặt / vắng»."""
from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import ScannerEntity, SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    da_them: set[str] = set()
    tien_to = f"{entry.entry_id}_"

    # Máy đã từng thấy (còn trong sổ thực thể) nhưng lúc này vắng: dựng lại để hiện «không ở nhà», không để mất.
    cu: list[ZteMayTracker] = []
    for muc in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if muc.domain == "device_tracker" and muc.unique_id.startswith(tien_to):
            mac = muc.unique_id.removeprefix(tien_to)
            if mac not in da_them:
                da_them.add(mac)
                cu.append(ZteMayTracker(coordinator, entry, mac))
    if cu:
        async_add_entities(cu)

    @callback
    def _them_may_moi() -> None:
        moi: list[ZteMayTracker] = []
        for may in (coordinator.data or {}).get("clients", []):
            mac = may["mac"]
            if mac not in da_them:
                da_them.add(mac)
                moi.append(ZteMayTracker(coordinator, entry, mac))
        if moi:
            async_add_entities(moi)

    _them_may_moi()
    entry.async_on_unload(coordinator.async_add_listener(_them_may_moi))


class ZteMayTracker(CoordinatorEntity, ScannerEntity):
    """Một máy WiFi. Có trong danh sách của bộ phát = đang kết nối; vắng = không ở nhà."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, entry: ConfigEntry, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{mac}"
        self._ten_cuoi = (self._may or {}).get("name") or mac

    @property
    def _may(self) -> dict[str, Any] | None:
        for may in (self.coordinator.data or {}).get("clients", []):
            if may["mac"] == self._mac:
                return may
        return None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, self._mac)},
            name=self._ten_cuoi,
            via_device=(DOMAIN, self._entry_id),
        )

    @property
    def source_type(self) -> SourceType:
        return SourceType.ROUTER

    @property
    def is_connected(self) -> bool:
        return self._may is not None

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def ip_address(self) -> str | None:
        may = self._may
        return (may.get("ip") or None) if may else None

    @property
    def hostname(self) -> str | None:
        may = self._may
        return (may.get("name") or None) if may else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Mọi thông tin bộ phát trả về cho máy này: trường chuẩn hoá + mọi trường gốc còn lại (tên gốc)."""
        may = self._may
        if not may:
            return {}
        ra = {k: v for k, v in may.items() if k not in ("mac", "ip", "name", "goc") and v not in (None, "")}
        ra.update(may.get("goc") or {})
        return ra
