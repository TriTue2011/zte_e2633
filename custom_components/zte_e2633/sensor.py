"""Cảm biến «Máy WiFi»: trạng thái là số máy đang kết nối; thuộc tính `clients` đúng khuôn card MikroTik đọc."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN

# Chỉ đưa các trường card cần và đủ nhỏ để không vượt giới hạn thuộc tính của Home Assistant.
TRUONG_MAY = ("mac", "ip", "name", "band", "rssi", "mode")


def dong_gon_may(clients: list[dict]) -> list[dict]:
    return [{k: m.get(k) for k in TRUONG_MAY} for m in clients]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ZteMayWifiSensor(coordinator, entry)])


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
