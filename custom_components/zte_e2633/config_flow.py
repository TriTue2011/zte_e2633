"""Thêm và nhập lại mật khẩu bộ phát ZTE E2633. Chỉ đăng nhập thử và đọc một lần, không ghi gì."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .api import ZteE2633, ZteLoiDangNhap, ZteLoiKetNoi
from .const import (
    CHU_KY_LON_NHAT,
    CHU_KY_MAC_DINH,
    CHU_KY_NHO_NHAT,
    CONF_CHU_KY,
    CONF_HOST,
    CONF_MAT_KHAU,
    CONF_TEN,
    CONF_XAC_MINH_SSL,
    DOMAIN,
)

# Địa chỉ được ghép vào URL: chỉ cho IP hoặc tên máy, không cho đường dẫn hay ký tự lạ.
HOST_RE = re.compile(r"^[A-Za-z0-9.-]{1,253}$")
MAT_KHAU_SELECTOR = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))


def _schema(mac_dinh: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_HOST, default=mac_dinh.get(CONF_HOST, "")): str,
        vol.Required(CONF_TEN, default=mac_dinh.get(CONF_TEN, "")): str,
        vol.Required(CONF_MAT_KHAU): MAT_KHAU_SELECTOR,
        vol.Required(CONF_XAC_MINH_SSL, default=mac_dinh.get(CONF_XAC_MINH_SSL, False)): bool,
        vol.Required(CONF_CHU_KY, default=mac_dinh.get(CONF_CHU_KY, CHU_KY_MAC_DINH)): vol.All(
            vol.Coerce(int), vol.Range(min=CHU_KY_NHO_NHAT, max=CHU_KY_LON_NHAT)
        ),
    })


async def _kiem_thu(hass: HomeAssistant, du: dict[str, Any]) -> None:
    """Đăng nhập và đọc thử đúng một lần. Ném ZteLoiDangNhap hoặc ZteLoiKetNoi nếu không được."""
    may = ZteE2633(du[CONF_HOST], du[CONF_TEN], du[CONF_MAT_KHAU], xac_minh_ssl=du[CONF_XAC_MINH_SSL])
    await hass.async_add_executor_job(may.doc_thiet_bi)


class ZteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        loi: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            if not HOST_RE.match(user_input[CONF_HOST]):
                loi["base"] = "host_sai"
            else:
                try:
                    await _kiem_thu(self.hass, user_input)
                except ZteLoiDangNhap:
                    loi["base"] = "dang_nhap"
                except ZteLoiKetNoi:
                    loi["base"] = "ket_noi"
                else:
                    await self.async_set_unique_id(user_input[CONF_HOST])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=f"ZTE E2633 ({user_input[CONF_HOST]})", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema(user_input or {}), errors=loi)

    async def async_step_reauth(self, entry_data: dict[str, Any]):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        entry: ConfigEntry = self._get_reauth_entry()
        loi: dict[str, str] = {}
        if user_input is not None:
            du = {**entry.data, CONF_MAT_KHAU: user_input[CONF_MAT_KHAU]}
            try:
                await _kiem_thu(self.hass, du)
            except ZteLoiDangNhap:
                loi["base"] = "dang_nhap"
            except ZteLoiKetNoi:
                loi["base"] = "ket_noi"
            else:
                return self.async_update_reload_and_abort(entry, data=du, reason="reauth_successful")
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_MAT_KHAU): MAT_KHAU_SELECTOR}),
            errors=loi,
        )
