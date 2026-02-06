#!/usr/bin/env python3
"""
Omada LAN/VLAN Batch Manager (GUI) — IPv4 (v4)

Fixes for create LAN errors you hit:
- Explicitly sets boolean fields that some controllers treat as REQUIRED:
    igmpSnoopEnable, mldSnoopEnable, dhcpL2RelayEnable, portal, accessControlRule, rateLimit
  (prevents: Parameter [igmpSnoopEnable] should not be null)

- gatewaySubnet formatting: controllers differ. This build automatically retries common formats:
    1) <gateway_ip>/<prefixlen>    e.g. 10.10.0.1/24
    2) <network_addr>/<prefixlen> e.g. 10.10.0.0/24
    3) <gateway_ip>/<netmask>     e.g. 10.10.0.1/255.255.255.0
    4) <network_addr>/<netmask>   e.g. 10.10.0.0/255.255.255.0
  (addresses: Parameter [gatewaySubnet] Invalid.)

Notes:
- Uses OpenAPI v2 for LAN networks:
    GET  /openapi/v2/{omadacId}/sites/{siteId}/lan-networks
    POST /openapi/v2/{omadacId}/sites/{siteId}/lan-networks
- Token request tries multiple JSON/form/query variants (same as v3).
"""

from __future__ import annotations

import ipaddress
import json
import queue
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


@dataclass(frozen=True)
class PlannedLan:
    index: int
    name: str
    vlan_id: int
    network: ipaddress.IPv4Network
    gateway: ipaddress.IPv4Address
    dhcp_start: ipaddress.IPv4Address
    dhcp_end: ipaddress.IPv4Address


class OmadaOpenApiClient:
    def __init__(
        self,
        base_url: str,
        verify_ssl: bool = True,
        timeout: int = 25,
        logger: Optional[Callable[[str], None]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.log = logger or (lambda _m: None)
        self.session = requests.Session()

        self.omadac_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.access_token_expiry: Optional[datetime] = None

    def _req(self, method: str, url: str, *, headers=None, params=None, json_body=None, form_body=None) -> Dict[str, Any]:
        hdrs = {"Accept": "application/json"}
        if headers:
            hdrs.update(headers)

        if form_body is not None:
            resp = self.session.request(
                method=method.upper(),
                url=url,
                headers=hdrs,
                params=params,
                data=form_body,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        else:
            if json_body is not None:
                hdrs.setdefault("Content-Type", "application/json")
            resp = self.session.request(
                method=method.upper(),
                url=url,
                headers=hdrs,
                params=params,
                json=json_body,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:800]}")
        try:
            return resp.json()
        except Exception as e:
            raise RuntimeError(f"Non-JSON response from {url}: {resp.text[:200]}") from e

    def _auth_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Access token missing. Connect again.")
        return {"Authorization": f"AccessToken={self.access_token}"}

    def get_controller_info(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/info"
        data = self._req("GET", url)
        res = data.get("result", {}) if isinstance(data, dict) else {}
        if isinstance(res, dict) and "omadacId" in res:
            self.omadac_id = res["omadacId"]
        return data

    def get_access_token_client_credentials(self, client_id: str, client_secret: str, omadac_id: Optional[str] = None) -> str:
        omadac_id = omadac_id or self.omadac_id
        url = f"{self.base_url}/openapi/authorize/token"
        base_params = {"grant_type": "client_credentials"}

        candidates: List[Tuple[str, Dict[str, str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]] = []

        candidates += [
            ("json:client_id", {}, {"client_id": client_id, "client_secret": client_secret}, None),
            ("json:clientId", {}, {"clientId": client_id, "clientSecret": client_secret}, None),
            ("json:clientKey", {}, {"clientKey": client_id, "clientSecret": client_secret}, None),
        ]
        if omadac_id:
            candidates += [
                ("json:client_id+omadacId", {}, {"client_id": client_id, "client_secret": client_secret, "omadacId": omadac_id}, None),
                ("json:client_id+omadac_id", {}, {"client_id": client_id, "client_secret": client_secret, "omadac_id": omadac_id}, None),
                ("json:clientKey+omadac_id", {}, {"clientKey": client_id, "clientSecret": client_secret, "omadac_id": omadac_id}, None),
                ("json:clientId+omadacId", {}, {"clientId": client_id, "clientSecret": client_secret, "omadacId": omadac_id}, None),
            ]

        candidates += [
            ("form:client_id", {}, None, {"client_id": client_id, "client_secret": client_secret}),
            ("form:clientKey", {}, None, {"clientKey": client_id, "clientSecret": client_secret}),
            ("query:client_id", {"client_id": client_id, "client_secret": client_secret}, None, None),
            ("query:clientKey", {"clientKey": client_id, "clientSecret": client_secret}, None, None),
        ]
        if omadac_id:
            candidates += [
                ("form:client_id+omadac_id", {}, None, {"client_id": client_id, "client_secret": client_secret, "omadac_id": omadac_id}),
                ("query:client_id+omadac_id", {"client_id": client_id, "client_secret": client_secret, "omadac_id": omadac_id}, None, None),
            ]

        last_err: Optional[str] = None
        for label, extra_params, jbody, fbody in candidates:
            try:
                params = dict(base_params)
                params.update(extra_params)
                self.log(f"Requesting access token ({label}) ...")
                data = self._req("POST", url, params=params, json_body=jbody, form_body=fbody)
                if data.get("errorCode") != 0:
                    last_err = f"{data.get('errorCode')}: {data.get('msg')}"
                    continue
                result = data.get("result", {})
                token = result.get("accessToken") if isinstance(result, dict) else None
                expires = result.get("expiresIn", 3600) if isinstance(result, dict) else 3600
                if not token:
                    last_err = f"Token missing in response for {label}: {data}"
                    continue
                self.access_token = token
                self.access_token_expiry = datetime.utcnow() + timedelta(seconds=int(expires))
                self.log(f"Token OK via {label}.")
                return token
            except Exception as e:
                last_err = str(e)

        raise RuntimeError(f"Token error: {last_err or 'unknown'}")

    def get_sites(self, page: int = 1, page_size: int = 100) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown. Use /api/info or fill it manually.")
        params = {"page": page, "pageSize": page_size}
        candidates = [
            f"{self.base_url}/openapi/v2/{self.omadac_id}/sites",
            f"{self.base_url}/openapi/v1/{self.omadac_id}/sites",
        ]
        last_err: Optional[Exception] = None
        for url in candidates:
            self.log(f"Trying GET {url.replace(self.base_url,'')} ...")
            try:
                data = self._req("GET", url, headers=self._auth_headers(), params=params)
                if data.get("errorCode") != 0:
                    raise RuntimeError(f"Sites error {data.get('errorCode')}: {data.get('msg')}")
                result = data.get("result", {})
                return result.get("data", []) if isinstance(result, dict) else []
            except Exception as e:
                last_err = e
        raise RuntimeError(f"All site list candidates failed. Last error: {last_err}")

    def get_lan_networks(self, site_id: str, page: int = 1, page_size: int = 200) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")
        params = {"page": page, "pageSize": page_size}
        url = f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/lan-networks"
        self.log(f"Trying GET {url.replace(self.base_url,'')} ...")
        data = self._req("GET", url, headers=self._auth_headers(), params=params)
        if data.get("errorCode") != 0:
            raise RuntimeError(f"LAN list error {data.get('errorCode')}: {data.get('msg')}")
        result = data.get("result", {})
        return result.get("data", []) if isinstance(result, dict) else []

    def get_site_gateways(self, site_id: str, page: int = 1, page_size: int = 500) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")

        bases = [
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}"),
        ]
        candidates: List[Tuple[str, str, Dict[str, Any]]] = []
        for api_ver, base in bases:
            candidates += [
                (api_ver, f"{base}/devices", {"page": page, "pageSize": page_size, "deviceType": "gateway"}),
                (api_ver, f"{base}/devices", {"page": page, "pageSize": page_size}),
                (api_ver, f"{base}/devices", {"currentPage": page, "currentPageSize": page_size}),
            ]

        last_err: Optional[Exception] = None
        devices: List[Dict[str, Any]] = []
        for api_ver, url, params in candidates:
            try:
                self.log(f"Trying GET {url.replace(self.base_url,'')} (gateways {api_ver}) ...")
                data = self._req("GET", url, headers=self._auth_headers(), params=params)
                if data.get("errorCode") != 0:
                    raise RuntimeError(f"Gateway list error {data.get('errorCode')}: {data.get('msg')}")
                result = data.get("result", {})
                if isinstance(result, dict):
                    items = result.get("data")
                    if isinstance(items, list):
                        devices = items
                        break
                raise RuntimeError("Unexpected gateway response format.")
            except Exception as e:
                last_err = e

        if not devices and last_err:
            raise RuntimeError(f"Gateway list failed. Last error: {last_err}")

        explicit_gateways: List[Dict[str, Any]] = []
        unknown_gateways: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for dev in devices:
            dtype = str(dev.get("deviceType") or dev.get("type") or dev.get("role") or "").lower()
            name = str(
                dev.get("name")
                or dev.get("customName")
                or dev.get("deviceName")
                or dev.get("displayName")
                or ""
            ).strip()
            if not name:
                continue
            dev_id = str(dev.get("deviceId") or dev.get("device_id") or dev.get("id") or "").strip()
            mac = str(dev.get("mac") or dev.get("macAddress") or "").strip()
            value = dev_id or mac or name

            if value in seen:
                continue
            seen.add(value)

            if mac:
                label = f"{name}  [{mac}]"
            elif dtype:
                label = f"{name}  ({dtype})"
            else:
                label = name

            iface_ids: List[str] = []
            iface_list: List[Dict[str, str]] = []
            raw_iface_ids = dev.get("interfaceIds")
            if isinstance(raw_iface_ids, list):
                iface_ids = [str(x) for x in raw_iface_ids if x]
            else:
                raw_ifaces = dev.get("interfaces")
                if isinstance(raw_ifaces, list):
                    for it in raw_ifaces:
                        if isinstance(it, dict):
                            iid = it.get("id") or it.get("interfaceId")
                            if iid:
                                iface_ids.append(str(iid))
                            iname = (
                                it.get("name")
                                or it.get("ifName")
                                or it.get("displayName")
                                or it.get("ifname")
                                or it.get("port")
                                or ""
                            )
                            if iid:
                                iface_list.append({"id": str(iid), "name": str(iname) if iname else str(iid)})

            entry = {
                "name": name,
                "label": label,
                "value": value,
                "device_id": dev_id or None,
                "interface_ids": iface_ids,
                "interfaces": iface_list,
            }
            if "gateway" in dtype or "router" in dtype:
                explicit_gateways.append(entry)
            elif any(x in dtype for x in ("ap", "switch")):
                continue
            else:
                unknown_gateways.append(entry)

        return explicit_gateways or unknown_gateways

    def create_lan_network(
        self,
        site_id: str,
        plan: PlannedLan,
        gateway_device: Optional[str] = None,
        interface_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")
        url = f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/lan-networks"

        gw_ip = str(plan.gateway)
        net_addr = str(plan.network.network_address)
        mask = str(plan.network.netmask)
        prefix = plan.network.prefixlen

        gwsub_candidates = [
            f"{gw_ip}/{prefix}",
            f"{gw_ip}/{mask}",
            f"{net_addr}/{prefix}",
            f"{net_addr}/{mask}",
        ]

        base_body: Dict[str, Any] = {
            "name": plan.name,
            "purpose": 1,
            "vlanType": 0,
            "vlan": plan.vlan_id,
            "application": 0,
            "dhcpSettingsVO": {
                "enable": True,
                "ipRangePool": [{"ipaddrStart": str(plan.dhcp_start), "ipaddrEnd": str(plan.dhcp_end)}],
                "dhcpns": "auto",
                "leasetime": 1440,
                "gateway": gw_ip,
            },
            "igmpSnoopEnable": True,
            "mldSnoopEnable": False,
            "dhcpL2RelayEnable": False,
            "portal": False,
            "accessControlRule": False,
            "rateLimit": False,
        }
        if gateway_device:
            base_body["gateway"] = str(gateway_device).strip()
        if interface_ids:
            base_body["interfaceIds"] = list(interface_ids)

        last_data: Optional[Dict[str, Any]] = None
        gateway_field_enabled = bool(gateway_device)
        for gwsub in gwsub_candidates:
            body = dict(base_body)
            body["gatewaySubnet"] = gwsub
            self.log(f"POST {url.replace(self.base_url,'')}  (name={plan.name}, vlan={plan.vlan_id}, gatewaySubnet={gwsub})")
            data = self._req("POST", url, headers=self._auth_headers(), json_body=body)
            last_data = data
            if data.get("errorCode") == 0:
                return data
            msg = (data.get("msg") or "").lower()
            if gateway_field_enabled and "gateway" in msg and ("invalid" in msg or "not found" in msg or "not exist" in msg):
                gateway_field_enabled = False
                base_body.pop("gateway", None)
                body2 = dict(base_body)
                body2["gatewaySubnet"] = gwsub
                self.log("Retrying without gateway selector field ...")
                data2 = self._req("POST", url, headers=self._auth_headers(), json_body=body2)
                last_data = data2
                if data2.get("errorCode") == 0:
                    return data2
                msg2 = (data2.get("msg") or "").lower()
                if "gatewaysubnet" in msg2 and "invalid" in msg2:
                    continue
                return data2
            if "gatewaysubnet" in msg and "invalid" in msg:
                continue
            return data
        return last_data or {"errorCode": -1, "msg": "Unknown error creating LAN network"}


def generate_plan(
    name_prefix: str,
    start_ip: str,
    prefix_len: int,
    count: int,
    start_vlan: int,
    dhcp_start_offset: int,
    dhcp_end_offset: int,
) -> Tuple[List[PlannedLan], List[str]]:
    warnings: List[str] = []

    if count <= 0:
        raise ValueError("Number of networks must be > 0")
    if not (1 <= prefix_len <= 30):
        raise ValueError("Prefix length must be between 1 and 30")
    if start_vlan < 1 or start_vlan > 4090:
        raise ValueError("Start VLAN must be 1..4090")
    if start_vlan + count - 1 > 4090:
        raise ValueError("VLAN range exceeds 4090 (controller API limit)")

    ip = ipaddress.IPv4Address(start_ip)
    net0 = ipaddress.IPv4Network((ip, prefix_len), strict=False)
    if ip != net0.network_address:
        warnings.append(f"Start IP {ip} is not a network boundary for /{prefix_len}. Using {net0.network_address} as the first subnet.")

    block_size = net0.num_addresses
    plans: List[PlannedLan] = []

    for i in range(count):
        net_addr_int = int(net0.network_address) + i * block_size
        n = ipaddress.IPv4Network((ipaddress.IPv4Address(net_addr_int), prefix_len), strict=True)

        gw = ipaddress.IPv4Address(int(n.network_address) + 1)
        first_usable = ipaddress.IPv4Address(int(n.network_address) + 2)
        last_usable = ipaddress.IPv4Address(int(n.broadcast_address) - 1)

        ds = ipaddress.IPv4Address(int(n.network_address) + dhcp_start_offset)
        de = ipaddress.IPv4Address(int(n.broadcast_address) - dhcp_end_offset)

        if ds < first_usable:
            ds = first_usable
        if de > last_usable:
            de = last_usable
        if ds >= de:
            warnings.append(f"DHCP range invalid for {n.with_prefixlen}; adjusted to {first_usable}-{last_usable}")
            ds, de = first_usable, last_usable

        vlan = start_vlan + i
        name = f"{name_prefix}-{vlan}"

        plans.append(
            PlannedLan(
                index=i + 1,
                name=name,
                vlan_id=vlan,
                network=n,
                gateway=gw,
                dhcp_start=ds,
                dhcp_end=de,
            )
        )

    return plans, warnings


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Omada LAN/VLAN Batch Manager (IPv4) — v4")
        self.geometry("1100x720")

        self.client: Optional[OmadaOpenApiClient] = None
        self.sites: List[Dict[str, Any]] = []
        self.gateways: List[Dict[str, str]] = []
        self.selected_site_id: Optional[str] = None
        self.selected_gateway_name: Optional[str] = None
        self.selected_gateway_value: Optional[str] = None
        self.selected_gateway_device_id: Optional[str] = None
        self.selected_gateway_interface_ids: List[str] = []
        self.selected_gateway_interfaces: List[Dict[str, str]] = []
        self.plan: List[PlannedLan] = []
        self.plan_interface_ids: Dict[int, List[str]] = {}

        self._q: "queue.Queue[Tuple[str, Any]]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None

        self._build_ui()
        self.after(150, self._poll_queue)

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)

        self.tab_conn = ttk.Frame(nb)
        self.tab_current = ttk.Frame(nb)
        self.tab_batch = ttk.Frame(nb)
        self.tab_logs = ttk.Frame(nb)

        nb.add(self.tab_conn, text="Connection")
        nb.add(self.tab_current, text="Current LAN Networks")
        nb.add(self.tab_batch, text="Batch Create")
        nb.add(self.tab_logs, text="Logs")

        self._build_connection_tab()
        self._build_current_tab()
        self._build_batch_tab()
        self._build_logs_tab()

    def _build_connection_tab(self):
        frame = ttk.Frame(self.tab_conn, padding=10)
        frame.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frame, text="Controller base URL (example: https://omada:8043)").grid(row=row, column=0, sticky="w")
        self.var_url = tk.StringVar(value="https://")
        ttk.Entry(frame, textvariable=self.var_url, width=55).grid(row=row, column=1, sticky="w")
        self.var_verify_ssl = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Verify SSL certificate", variable=self.var_verify_ssl).grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frame, text="OpenAPI Client ID").grid(row=row, column=0, sticky="w")
        self.var_client_id = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_client_id, width=55).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frame, text="OpenAPI Client Secret").grid(row=row, column=0, sticky="w")
        self.var_client_secret = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_client_secret, width=55, show="•").grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frame, text="(Optional) Omada ID (omadacId) - auto-detected via /api/info").grid(row=row, column=0, sticky="w")
        self.var_omada_id = tk.StringVar()
        ttk.Entry(frame, textvariable=self.var_omada_id, width=55).grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=3, sticky="ew", pady=10)
        row += 1

        self.btn_connect = ttk.Button(frame, text="Connect", command=self.on_connect)
        self.btn_connect.grid(row=row, column=0, sticky="w")

        self.lbl_conn_state = ttk.Label(frame, text="Not connected")
        self.lbl_conn_state.grid(row=row, column=1, sticky="w")

        self.btn_disconnect = ttk.Button(frame, text="Disconnect", command=self.on_disconnect, state="disabled")
        self.btn_disconnect.grid(row=row, column=2, sticky="w")
        row += 1

        ttk.Label(frame, text="Site").grid(row=row, column=0, sticky="w", pady=(10, 0))
        self.var_site = tk.StringVar()
        self.cmb_sites = ttk.Combobox(frame, textvariable=self.var_site, width=52, state="readonly")
        self.cmb_sites.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.cmb_sites.bind("<<ComboboxSelected>>", self.on_site_selected)

        self.btn_refresh_sites = ttk.Button(frame, text="Refresh sites", command=self.on_refresh_sites, state="disabled")
        self.btn_refresh_sites.grid(row=row, column=2, sticky="w", pady=(10, 0))
        row += 1

        ttk.Label(frame, text="Gateway").grid(row=row, column=0, sticky="w", pady=(10, 0))
        self.var_gateway = tk.StringVar()
        self.cmb_gateways = ttk.Combobox(frame, textvariable=self.var_gateway, width=52, state="disabled")
        self.cmb_gateways.grid(row=row, column=1, sticky="w", pady=(10, 0))
        self.cmb_gateways.bind("<<ComboboxSelected>>", self.on_gateway_selected)

        self.btn_refresh_gateways = ttk.Button(frame, text="Refresh gateways", command=self.on_refresh_gateways, state="disabled")
        self.btn_refresh_gateways.grid(row=row, column=2, sticky="w", pady=(10, 0))

        for c in range(3):
            frame.grid_columnconfigure(c, weight=1 if c == 1 else 0)

    def _build_current_tab(self):
        frame = ttk.Frame(self.tab_current, padding=10)
        frame.pack(fill="both", expand=True)

        top = ttk.Frame(frame)
        top.pack(fill="x")

        self.btn_fetch_networks = ttk.Button(top, text="Refresh LAN networks", command=self.on_fetch_networks, state="disabled")
        self.btn_fetch_networks.pack(side="left")

        self.btn_export_networks = ttk.Button(top, text="Export JSON…", command=self.on_export_networks, state="disabled")
        self.btn_export_networks.pack(side="left", padx=(8, 0))

        self.lbl_networks_state = ttk.Label(top, text="")
        self.lbl_networks_state.pack(side="left", padx=(10, 0))

        cols = ("name", "vlan", "gatewaySubnet", "dhcp_start", "dhcp_end", "id")
        self.tree_networks = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (220, 70, 170, 120, 120, 260)):
            self.tree_networks.heading(c, text=c)
            self.tree_networks.column(c, width=w, anchor="w")
        self.tree_networks.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(frame, text="Raw JSON (selected row)").pack(anchor="w", pady=(10, 0))
        self.txt_network_raw = tk.Text(frame, height=8)
        self.txt_network_raw.pack(fill="x", expand=False)
        self.tree_networks.bind("<<TreeviewSelect>>", self._on_network_selected)

        self._networks_cache: List[Dict[str, Any]] = []

    def _build_batch_tab(self):
        frame = ttk.Frame(self.tab_batch, padding=10)
        frame.pack(fill="both", expand=True)

        form = ttk.LabelFrame(frame, text="Batch parameters", padding=10)
        form.pack(fill="x")

        r = 0
        ttk.Label(form, text="Name prefix").grid(row=r, column=0, sticky="w")
        self.var_name_prefix = tk.StringVar(value="LAN")
        ttk.Entry(form, textvariable=self.var_name_prefix, width=18).grid(row=r, column=1, sticky="w")

        ttk.Label(form, text="Start subnet IP").grid(row=r, column=2, sticky="w", padx=(15, 0))
        self.var_start_ip = tk.StringVar(value="10.0.0.0")
        ttk.Entry(form, textvariable=self.var_start_ip, width=18).grid(row=r, column=3, sticky="w")
        r += 1

        ttk.Label(form, text="Prefix length (CIDR)").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_prefix = tk.IntVar(value=24)
        ttk.Spinbox(form, from_=8, to=30, textvariable=self.var_prefix, width=6).grid(row=r, column=1, sticky="w", pady=(6, 0))

        ttk.Label(form, text="Number of LANs/VLANs").grid(row=r, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
        self.var_count = tk.IntVar(value=20)
        ttk.Spinbox(form, from_=1, to=200, textvariable=self.var_count, width=8).grid(row=r, column=3, sticky="w", pady=(6, 0))
        r += 1

        ttk.Label(form, text="Start VLAN").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_start_vlan = tk.IntVar(value=100)
        ttk.Spinbox(form, from_=1, to=4090, textvariable=self.var_start_vlan, width=8).grid(row=r, column=1, sticky="w", pady=(6, 0))

        ttk.Label(form, text="DHCP start offset").grid(row=r, column=2, sticky="w", padx=(15, 0), pady=(6, 0))
        self.var_dhcp_start_off = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=2, to=200, textvariable=self.var_dhcp_start_off, width=8).grid(row=r, column=3, sticky="w", pady=(6, 0))
        r += 1

        ttk.Label(form, text="DHCP end offset (from broadcast)").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.var_dhcp_end_off = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=2, to=200, textvariable=self.var_dhcp_end_off, width=8).grid(row=r, column=1, sticky="w", pady=(6, 0))
        r += 1

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(10, 0))

        self.btn_preview = ttk.Button(btns, text="Generate preview", command=self.on_generate_preview, state="disabled")
        self.btn_preview.pack(side="left")

        self.btn_push = ttk.Button(btns, text="Push to controller", command=self.on_push_plan, state="disabled")
        self.btn_push.pack(side="left", padx=(8, 0))

        self.btn_export_plan = ttk.Button(btns, text="Export preview JSON…", command=self.on_export_plan, state="disabled")
        self.btn_export_plan.pack(side="left", padx=(8, 0))

        self.prog = ttk.Progressbar(btns, mode="determinate")
        self.prog.pack(side="right", fill="x", expand=True, padx=(10, 0))

        self.lbl_batch_state = ttk.Label(frame, text="")
        self.lbl_batch_state.pack(anchor="w", pady=(6, 0))

        cols = ("#", "name", "vlan", "subnet", "gateway", "dhcp_start", "dhcp_end")
        self.tree_plan = ttk.Treeview(frame, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (40, 200, 70, 150, 120, 120, 120)):
            self.tree_plan.heading(c, text=c)
            self.tree_plan.column(c, width=w, anchor="w")
        self.tree_plan.pack(fill="both", expand=True, pady=(10, 0))

        for c in range(4):
            form.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0)

    def _build_logs_tab(self):
        frame = ttk.Frame(self.tab_logs, padding=10)
        frame.pack(fill="both", expand=True)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Button(top, text="Clear log", command=self.on_clear_log).pack(side="left")
        self.txt_logs = tk.Text(frame)
        self.txt_logs.pack(fill="both", expand=True)
        self._log("Ready.")

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.insert("end", f"[{ts}] {msg}\n")
        self.txt_logs.see("end")

    def on_clear_log(self):
        self.txt_logs.delete("1.0", "end")
        self._log("Log cleared.")

    def _poll_queue(self):
        try:
            while True:
                typ, payload = self._q.get_nowait()
                if typ == "log":
                    self._log(str(payload))
                elif typ == "connected":
                    self._on_connected(payload)
                elif typ == "sites":
                    self._on_sites(payload)
                elif typ == "networks":
                    self._on_networks(payload)
                elif typ == "gateways":
                    self._on_gateways(payload)
                elif typ == "progress":
                    done, total, text = payload
                    self.prog["maximum"] = max(total, 1)
                    self.prog["value"] = done
                    self.lbl_batch_state.config(text=text)
                elif typ == "error":
                    messagebox.showerror("Error", str(payload))
                elif typ == "info":
                    messagebox.showinfo("Info", str(payload))
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _run_bg(self, fn, *, disable_buttons: List[ttk.Button]):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        for b in disable_buttons:
            b.config(state="disabled")

        def wrap():
            try:
                fn()
            except Exception as e:
                self._q.put(("error", str(e)))
                self._q.put(("log", f"ERROR: {e}"))
            finally:
                self._q.put(("log", "Operation finished."))
                self._q.put(("connected", "refresh_buttons"))

        self._worker = threading.Thread(target=wrap, daemon=True)
        self._worker.start()

    def on_connect(self):
        url = self.var_url.get().strip()
        cid = self.var_client_id.get().strip()
        csec = self.var_client_secret.get().strip()
        omada_id = self.var_omada_id.get().strip() or None
        verify = bool(self.var_verify_ssl.get())

        if not url or url == "https://":
            messagebox.showwarning("Missing", "Please enter the controller base URL.")
            return
        if not cid or not csec:
            messagebox.showwarning("Missing", "Please enter Client ID and Client Secret.")
            return

        def work():
            self._q.put(("log", f"Connecting to {url} (verify_ssl={verify}) ..."))
            client = OmadaOpenApiClient(url, verify_ssl=verify, logger=lambda m: self._q.put(("log", m)))

            info = client.get_controller_info()
            ver = info.get("result", {}).get("controllerVer") if isinstance(info, dict) else None
            self._q.put(("log", f"/api/info OK; controllerVer={ver}"))

            if omada_id:
                client.omadac_id = omada_id
            elif client.omadac_id:
                self._q.put(("log", f"Detected omadacId={client.omadac_id}"))

            client.get_access_token_client_credentials(cid, csec, omadac_id=client.omadac_id)
            self._q.put(("log", f"Access token OK (expires ~{client.access_token_expiry} UTC)."))

            sites = client.get_sites(page=1, page_size=100)
            self._q.put(("sites", sites))

            self.client = client
            self._q.put(("connected", "connected"))

        self._run_bg(work, disable_buttons=[self.btn_connect])

    def _on_connected(self, status):
        if status == "connected":
            self.lbl_conn_state.config(text="Connected")
            self.btn_refresh_sites.config(state="normal")
            self.btn_fetch_networks.config(state="normal")
            self.btn_export_networks.config(state="normal")
            self.btn_preview.config(state="normal")
            self.btn_refresh_gateways.config(state="normal")
            self.btn_connect.config(state="normal")
            self.btn_disconnect.config(state="normal")
            if self.client and self.client.omadac_id:
                self.var_omada_id.set(self.client.omadac_id)
            self._update_push_state()
        elif status == "refresh_buttons":
            self.btn_connect.config(state="normal")
            if self.client:
                self.btn_refresh_sites.config(state="normal")
                self.btn_fetch_networks.config(state="normal")
                self.btn_export_networks.config(state="normal")
                self.btn_preview.config(state="normal")
                self.btn_refresh_gateways.config(state="normal")
                self.btn_disconnect.config(state="normal")
                self._update_push_state()
            else:
                self.btn_disconnect.config(state="disabled")
                self._update_push_state()

    def on_disconnect(self):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("Busy", "An operation is already running.")
            return

        if self.client:
            try:
                self.client.session.close()
            except Exception:
                pass

        self.client = None
        self.sites = []
        self.selected_site_id = None
        self.gateways = []
        self.selected_gateway_name = None
        self.selected_gateway_value = None
        self.selected_gateway_device_id = None
        self.selected_gateway_interface_ids = []
        self.selected_gateway_interfaces = []
        self.plan_interface_ids = {}

        self.cmb_sites["values"] = []
        self.var_site.set("")
        self._on_gateways([])

        self._networks_cache = []
        for i in self.tree_networks.get_children():
            self.tree_networks.delete(i)
        self.txt_network_raw.delete("1.0", "end")
        self.lbl_networks_state.config(text="")

        self.lbl_conn_state.config(text="Not connected")
        self.btn_refresh_sites.config(state="disabled")
        self.btn_refresh_gateways.config(state="disabled")
        self.btn_fetch_networks.config(state="disabled")
        self.btn_export_networks.config(state="disabled")
        self.btn_preview.config(state="disabled")
        self.btn_disconnect.config(state="disabled")
        self.btn_connect.config(state="normal")
        self._update_push_state()
        self._q.put(("log", "Disconnected."))

    def on_refresh_sites(self):
        if not self.client:
            return

        def work():
            self._q.put(("log", "Refreshing sites..."))
            sites = self.client.get_sites(page=1, page_size=100)
            self._q.put(("sites", sites))

        self._run_bg(work, disable_buttons=[self.btn_refresh_sites])

    def _on_sites(self, sites):
        self.sites = sites or []
        if not self.sites:
            self.cmb_sites["values"] = []
            self.var_site.set("")
            self.selected_site_id = None
            self._on_gateways([])
            self._q.put(("log", "No sites returned."))
            return

        values = [f"{s.get('name','(no name)')}  [{s.get('siteId')}]" for s in self.sites]
        self.cmb_sites["values"] = values
        self.cmb_sites.current(0)
        self.on_site_selected()

    def on_site_selected(self, _evt=None):
        idx = self.cmb_sites.current()
        if idx < 0 or idx >= len(self.sites):
            self.selected_site_id = None
            return
        self.selected_site_id = self.sites[idx].get("siteId")
        self._q.put(("log", f"Selected siteId={self.selected_site_id}"))
        self._on_gateways([])
        self.after(400, lambda: self.on_refresh_gateways(silent_if_busy=True))

    def on_refresh_gateways(self, silent_if_busy: bool = False):
        if not self.client or not self.selected_site_id:
            if not silent_if_busy:
                messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        if self._worker and self._worker.is_alive():
            if not silent_if_busy:
                messagebox.showwarning("Busy", "An operation is already running.")
            return

        def work():
            assert self.client
            assert self.selected_site_id
            self._q.put(("log", f"Fetching gateways for siteId={self.selected_site_id} ..."))
            gateways = self.client.get_site_gateways(self.selected_site_id, page=1, page_size=500)
            self._q.put(("gateways", gateways))

        self._run_bg(work, disable_buttons=[self.btn_refresh_gateways])

    def _on_gateways(self, gateways):
        self.gateways = gateways or []
        self.selected_gateway_name = None
        self.selected_gateway_value = None
        self.selected_gateway_device_id = None
        self.selected_gateway_interface_ids = []
        self.selected_gateway_interfaces = []

        if not self.gateways:
            self.cmb_gateways["values"] = []
            self.var_gateway.set("")
            self.cmb_gateways.config(state="disabled")
            self._q.put(("log", "No gateways loaded for selected site."))
            self._update_push_state()
            return

        values = [g.get("label", g.get("name", "")) for g in self.gateways]
        self.cmb_gateways["values"] = values
        self.cmb_gateways.config(state="readonly")
        self.cmb_gateways.current(0)
        self.on_gateway_selected()
        self._q.put(("log", f"Loaded {len(self.gateways)} gateways for selected site."))

    def on_gateway_selected(self, _evt=None):
        idx = self.cmb_gateways.current()
        if idx < 0 or idx >= len(self.gateways):
            self.selected_gateway_name = None
            self.selected_gateway_value = None
            self.selected_gateway_device_id = None
            self.selected_gateway_interface_ids = []
            self._update_push_state()
            return
        self.selected_gateway_name = self.gateways[idx].get("name")
        self.selected_gateway_value = self.gateways[idx].get("value")
        self.selected_gateway_device_id = self.gateways[idx].get("device_id") or None
        self.selected_gateway_interface_ids = self.gateways[idx].get("interface_ids") or []
        self.selected_gateway_interfaces = self.gateways[idx].get("interfaces") or []
        self._q.put(("log", f"Selected gateway={self.selected_gateway_name}"))
        self._update_push_state()

    def on_fetch_networks(self):
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return

        def work():
            self._q.put(("log", "Fetching LAN networks..."))
            nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
            self._q.put(("networks", nets))

        self._run_bg(work, disable_buttons=[self.btn_fetch_networks])

    def _on_networks(self, nets):
        self._networks_cache = nets or []
        for i in self.tree_networks.get_children():
            self.tree_networks.delete(i)

        for n in self._networks_cache:
            name = n.get("name", "")
            vlan = n.get("vlan", "")
            gateway_subnet = n.get("gatewaySubnet", "")
            dhcp = n.get("dhcpSettingsVO") or {}
            pool = (dhcp.get("ipRangePool") or [])
            ds = pool[0].get("ipaddrStart") if pool else ""
            de = pool[0].get("ipaddrEnd") if pool else ""
            nid = n.get("id", "")
            self.tree_networks.insert("", "end", values=(name, vlan, gateway_subnet, ds, de, nid))

        self.lbl_networks_state.config(text=f"{len(self._networks_cache)} networks loaded.")
        self._q.put(("log", f"Loaded {len(self._networks_cache)} LAN networks."))

    def _on_network_selected(self, _evt=None):
        sel = self.tree_networks.selection()
        if not sel:
            return
        idx = self.tree_networks.index(sel[0])
        if idx < 0 or idx >= len(self._networks_cache):
            return
        raw = self._networks_cache[idx]
        self.txt_network_raw.delete("1.0", "end")
        self.txt_network_raw.insert("end", json.dumps(raw, indent=2))

    def on_export_networks(self):
        if not self._networks_cache:
            messagebox.showinfo("Nothing", "No networks loaded.")
            return
        path = filedialog.asksaveasfilename(
            title="Export LAN networks JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._networks_cache, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_generate_preview(self):
        try:
            plans, warnings = generate_plan(
                name_prefix=self.var_name_prefix.get().strip() or "LAN",
                start_ip=self.var_start_ip.get().strip(),
                prefix_len=int(self.var_prefix.get()),
                count=int(self.var_count.get()),
                start_vlan=int(self.var_start_vlan.get()),
                dhcp_start_offset=int(self.var_dhcp_start_off.get()),
                dhcp_end_offset=int(self.var_dhcp_end_off.get()),
            )
        except Exception as e:
            messagebox.showerror("Invalid input", str(e))
            return

        self.plan = plans
        for i in self.tree_plan.get_children():
            self.tree_plan.delete(i)

        for p in self.plan:
            self.tree_plan.insert(
                "",
                "end",
                values=(p.index, p.name, p.vlan_id, p.network.with_prefixlen, str(p.gateway), str(p.dhcp_start), str(p.dhcp_end)),
            )

        if warnings:
            messagebox.showwarning("Plan warnings", "\n".join(warnings))
            for w in warnings:
                self._log(f"WARNING: {w}")

        self._log(f"Preview generated: {len(self.plan)} networks.")
        self._update_push_state()
        self.btn_export_plan.config(state="normal" if self.plan else "disabled")

    def on_export_plan(self):
        if not self.plan:
            messagebox.showinfo("Nothing", "No preview generated.")
            return
        path = filedialog.asksaveasfilename(
            title="Export preview JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        obj = [{
            "index": p.index,
            "name": p.name,
            "vlan": p.vlan_id,
            "gatewaySubnet_candidates": [
                f"{p.gateway}/{p.network.prefixlen}",
                f"{p.network.network_address}/{p.network.prefixlen}",
                f"{p.gateway}/{p.network.netmask}",
                f"{p.network.network_address}/{p.network.netmask}",
            ],
            "dhcpStart": str(p.dhcp_start),
            "dhcpEnd": str(p.dhcp_end),
        } for p in self.plan]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")

    def on_push_plan(self):
        if not self.client or not self.selected_site_id:
            messagebox.showwarning("Missing", "Connect and select a site first.")
            return
        if not self.selected_gateway_name:
            messagebox.showwarning("Missing", "Select a gateway for this site first (Refresh gateways).")
            return
        if not self.plan:
            messagebox.showwarning("Missing", "Generate a preview first.")
            return
        iface_catalog = self.selected_gateway_interfaces
        if not iface_catalog and self.selected_gateway_interface_ids:
            iface_catalog = [{"id": i, "name": i} for i in self.selected_gateway_interface_ids]
        if not iface_catalog:
            iface_catalog = self._get_interface_catalog_from_networks()
        if not iface_catalog:
            messagebox.showwarning("Missing", "No LAN interfaces found for this site.")
            return
        mapping = self._prompt_interface_selection(iface_catalog)
        if mapping is None:
            return
        self.plan_interface_ids = mapping

        if not messagebox.askyesno("Confirm push", f"This will create {len(self.plan)} LAN networks.\n\nContinue?"):
            return

        def work():
            assert self.client
            site_id = self.selected_site_id
            assert site_id
            gateway_name = self.selected_gateway_name
            assert gateway_name
            gateway_device = self.selected_gateway_device_id or self.selected_gateway_value or gateway_name
            interface_ids = None

            total_steps = len(self.plan)
            done = 0

            for p in self.plan:
                self._q.put(("progress", (done, total_steps, f"Creating {p.name} (VLAN {p.vlan_id})...")))
                iface_ids = self.plan_interface_ids.get(p.index)
                if not iface_ids:
                    raise RuntimeError(f"Interface selection missing for {p.name}.")
                resp = self.client.create_lan_network(site_id, p, gateway_device=gateway_device, interface_ids=iface_ids)
                if resp.get("errorCode") != 0:
                    raise RuntimeError(f"Create LAN failed for {p.name}: {resp.get('errorCode')} {resp.get('msg')}")
                self._q.put(("log", f"LAN created: {p.name} VLAN {p.vlan_id} {p.network.with_prefixlen}"))
                done += 1

            self._q.put(("progress", (total_steps, total_steps, "Done.")))
            self._q.put(("info", "Batch creation completed."))

        self._run_bg(work, disable_buttons=[self.btn_push])

    def _update_push_state(self):
        enabled = bool(self.client and self.selected_site_id and self.selected_gateway_name and len(self.plan) > 0)
        self.btn_push.config(state="normal" if enabled else "disabled")

    def _prompt_interface_selection(self, interfaces: List[Dict[str, str]]) -> Optional[Dict[int, List[str]]]:
        if not interfaces:
            messagebox.showwarning("Missing", "No LAN interfaces are available.")
            return None

        win = tk.Toplevel(self)
        win.title("Select LAN interfaces for networks")
        win.transient(self)
        win.grab_set()

        info = ttk.Label(win, text="Choose LAN interfaces per network. Top row applies to all networks.")
        info.pack(anchor="w", padx=10, pady=(10, 6))

        container = ttk.Frame(win)
        container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        header = ttk.Frame(inner)
        header.grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Network").grid(row=0, column=0, sticky="w", padx=(0, 10))

        apply_all_vars: List[tk.BooleanVar] = []
        for c, iface in enumerate(interfaces, start=1):
            ttk.Label(header, text=iface.get("name") or iface.get("id", "")).grid(row=0, column=c, padx=6, sticky="w")

        row_vars: Dict[int, List[tk.BooleanVar]] = {}

        apply_row = ttk.Frame(inner)
        apply_row.grid(row=1, column=0, sticky="w", pady=(4, 8))
        ttk.Label(apply_row, text="Apply to all").grid(row=0, column=0, sticky="w", padx=(0, 10))

        def apply_all_changed(col: int):
            val = apply_all_vars[col].get()
            for vars_ in row_vars.values():
                vars_[col].set(val)

        for c, _iface in enumerate(interfaces):
            v = tk.BooleanVar(value=True)
            apply_all_vars.append(v)
            ttk.Checkbutton(apply_row, variable=v, command=lambda col=c: apply_all_changed(col)).grid(row=0, column=c + 1, padx=6)

        for r, p in enumerate(self.plan, start=2):
            row = ttk.Frame(inner)
            row.grid(row=r, column=0, sticky="w", pady=2)
            ttk.Label(row, text=f"{p.name} (VLAN {p.vlan_id})").grid(row=0, column=0, sticky="w", padx=(0, 10))
            vars_for_row: List[tk.BooleanVar] = []
            for c, _iface in enumerate(interfaces):
                v = tk.BooleanVar(value=True)
                vars_for_row.append(v)
                ttk.Checkbutton(row, variable=v).grid(row=0, column=c + 1, padx=6)
            row_vars[p.index] = vars_for_row

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        result: Dict[str, Any] = {"ok": False, "mapping": None}

        def on_ok():
            mapping: Dict[int, List[str]] = {}
            for p in self.plan:
                vars_ = row_vars.get(p.index, [])
                ids: List[str] = []
                for var, iface in zip(vars_, interfaces):
                    if var.get():
                        iid = iface.get("id")
                        if iid:
                            ids.append(str(iid))
                if not ids:
                    messagebox.showwarning("Missing", f"Select at least one interface for {p.name}.")
                    return
                mapping[p.index] = ids
            result["ok"] = True
            result["mapping"] = mapping
            win.destroy()

        def on_cancel():
            win.destroy()

        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(6, 0))
        ttk.Button(btns, text="OK", command=on_ok).pack(side="right")

        win.wait_window()
        if result["ok"]:
            return result["mapping"]
        return None

    def _get_interface_catalog_from_networks(self) -> List[Dict[str, str]]:
        iface_ids: List[str] = []

        for n in self._networks_cache:
            ids = n.get("interfaceIds")
            if isinstance(ids, list):
                for i in ids:
                    if i:
                        iface_ids.append(str(i))

        if not iface_ids and self.client and self.selected_site_id:
            try:
                nets = self.client.get_lan_networks(self.selected_site_id, page=1, page_size=500)
                for n in nets:
                    ids = n.get("interfaceIds")
                    if isinstance(ids, list):
                        for i in ids:
                            if i:
                                iface_ids.append(str(i))
            except Exception as e:
                self._q.put(("log", f"WARNING: Could not fetch interfaceIds from networks: {e}"))

        seen: set[str] = set()
        catalog: List[Dict[str, str]] = []
        for i in iface_ids:
            if i in seen:
                continue
            seen.add(i)
            catalog.append({"id": i, "name": i})

        return catalog

    def on_export_networks(self):
        if not self._networks_cache:
            messagebox.showinfo("Nothing", "No networks loaded.")
            return
        path = filedialog.asksaveasfilename(
            title="Export LAN networks JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._networks_cache, f, indent=2)
        messagebox.showinfo("Exported", f"Saved to {path}")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
