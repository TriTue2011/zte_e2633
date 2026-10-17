"""Đổi JSON trang quản trị ZTE E2633 (GetALLClients, GetALLAP) thành dữ liệu thiết bị. Không gọi mạng.

Khuôn đã đo từ trang của thiết bị: mỗi máy có MacAddr, IpAddr, HostName, Rssi (dBm), AccessType («1» = 2.4 GHz,
«2» = 5 GHz), WirelessMode, AssocTime (giây), TxRateBps, RxRateBps.
"""
from __future__ import annotations

import re
from typing import Any

BAND = {"1": "2.4G", "2": "5G"}
MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")


def _so_nguyen(v: Any, mac_dinh: int | None = None) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return mac_dinh


def _muc(du_lieu: Any) -> list[dict]:
    """Các mục «1», «2», … của một khối, theo thứ tự số. Bỏ khoá khác (ví dụ MGET_INST_NUM) và mục không phải đối tượng."""
    if not isinstance(du_lieu, dict):
        return []
    ra = [(int(k), v) for k, v in du_lieu.items() if str(k).isdigit() and isinstance(v, dict)]
    return [v for _, v in sorted(ra, key=lambda kv: kv[0])]


def phan_tich_thiet_bi(du_lieu: Any) -> list[dict]:
    """JSON GetALLClients → danh sách {mac, ip, name, band, rssi, mode, assoc_s, rx_bps, tx_bps}. Mục có MAC sai khuôn bị bỏ."""
    goc = du_lieu.get("clientsData") if isinstance(du_lieu, dict) else None
    ra: list[dict] = []
    for m in _muc(goc):
        mac = str(m.get("MacAddr", "")).strip().lower()
        if not MAC_RE.match(mac):
            continue
        ra.append({
            "mac": mac,
            "ip": str(m.get("IpAddr", ""))[:45],
            "name": str(m.get("HostName", ""))[:64],
            "band": BAND.get(str(m.get("AccessType", "")).strip(), ""),
            "rssi": _so_nguyen(m.get("Rssi")),
            "mode": str(m.get("WirelessMode", ""))[:16],
            "assoc_s": _so_nguyen(m.get("AssocTime")),
            "rx_bps": _so_nguyen(m.get("RxRateBps"), 0),
            "tx_bps": _so_nguyen(m.get("TxRateBps"), 0),
        })
    return ra


def phan_tich_ap(du_lieu: Any) -> dict:
    """JSON GetALLAP → thông tin bộ phát (mục đầu tiên), hoặc {} nếu không có."""
    goc = du_lieu.get("apData") if isinstance(du_lieu, dict) else None
    ds = _muc(goc)
    if not ds:
        return {}
    a = ds[0]
    mac = str(a.get("MacAddr", "")).strip().lower()
    return {
        "mac": mac if MAC_RE.match(mac) else "",
        "ip": str(a.get("IpAddr", ""))[:45],
        "name": str(a.get("DeviceName", ""))[:64],
        "firmware": str(a.get("SoftwareVer", ""))[:32],
    }
