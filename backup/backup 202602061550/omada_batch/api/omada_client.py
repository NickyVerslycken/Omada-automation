from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from omada_batch.models.lan import PlannedLan


class OmadaOpenApiClient:
    def __init__(
        self,
        base_url: str,
        verify_ssl: bool = True,
        timeout: int = 25,
        logger: Optional[Callable[[str], None]] = None,
        json_logger: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.log = logger or (lambda _m: None)
        self.json_log = json_logger or (lambda _m: None)
        self.session = requests.Session()

        self.omadac_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.access_token_expiry: Optional[datetime] = None

    def _emit_json(self, payload: Dict[str, Any]) -> None:
        try:
            self.json_log(payload)
        except Exception:
            pass

    def _sanitize_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in (headers or {}).items():
            if str(key).lower() == "authorization":
                out[key] = "***redacted***"
            else:
                out[key] = value
        return out

    def _preview_text(self, text: Any, limit: int = 250) -> str:
        out = str(text or "")
        if len(out) <= limit:
            return out
        return f"{out[:limit]}..."

    def _req(self, method: str, url: str, *, headers=None, params=None, json_body=None, form_body=None) -> Dict[str, Any]:
        hdrs = {"Accept": "application/json"}
        if headers:
            hdrs.update(headers)
        safe_headers = self._sanitize_headers(hdrs)

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

        self._emit_json(
            {
                "event": "http_response",
                "request": {
                    "method": method.upper(),
                    "url": url,
                    "params": params,
                    "headers": safe_headers,
                    "json_body": json_body,
                    "form_body": form_body,
                },
                "response": {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                },
            }
        )

        if resp.status_code != 200:
            preview = self._preview_text(resp.text, limit=250)
            self._emit_json(
                {
                    "event": "http_error",
                    "request": {"method": method.upper(), "url": url, "params": params},
                    "response": {"status_code": resp.status_code, "body_text": preview},
                }
            )
            raise RuntimeError(f"HTTP {resp.status_code}: {preview}")
        try:
            data = resp.json()
            self._emit_json(
                {
                    "event": "http_json",
                    "request": {"method": method.upper(), "url": url, "params": params},
                    "response": data,
                }
            )
            return data
        except Exception as e:
            preview = self._preview_text(resp.text, limit=250)
            self._emit_json(
                {
                    "event": "http_non_json",
                    "request": {"method": method.upper(), "url": url, "params": params},
                    "response": {"body_text": preview},
                }
            )
            raise RuntimeError(f"Non-JSON response from {url}: {preview}") from e

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
            ("v3", f"{self.base_url}/openapi/v3/{self.omadac_id}/sites"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites"),
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites"),
        ]
        last_err: Optional[Exception] = None
        for api_ver, url in candidates:
            self.log(f"Trying GET {url.replace(self.base_url,'')} (sites {api_ver}) ...")
            try:
                data = self._req("GET", url, headers=self._auth_headers(), params=params)
                if data.get("errorCode") != 0:
                    raise RuntimeError(f"Sites error {data.get('errorCode')}: {data.get('msg')}")
                result = data.get("result", {})
                items = result.get("data", []) if isinstance(result, dict) else []
                self.log(f"SUCCESS GET {url.replace(self.base_url,'')} (sites {api_ver}) rows={len(items)}")
                return items
            except Exception as e:
                self.log(f"FAILED GET {url.replace(self.base_url,'')} (sites {api_ver}): {e}")
                last_err = e
        raise RuntimeError(f"All site list candidates failed. Last error: {last_err}")

    def get_lan_networks(self, site_id: str, page: int = 1, page_size: int = 200) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")
        params = {"page": page, "pageSize": page_size}
        candidates = [
            ("v3", f"{self.base_url}/openapi/v3/{self.omadac_id}/sites/{site_id}/lan-networks"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/lan-networks"),
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}/lan-networks"),
        ]
        last_err: Optional[Exception] = None
        for api_ver, url in candidates:
            self.log(f"Trying GET {url.replace(self.base_url,'')} (lan-networks {api_ver}) ...")
            try:
                data = self._req("GET", url, headers=self._auth_headers(), params=params)
                if data.get("errorCode") != 0:
                    raise RuntimeError(f"LAN list error {data.get('errorCode')}: {data.get('msg')}")
                result = data.get("result", {})
                if isinstance(result, dict):
                    items = result.get("data")
                    if isinstance(items, list):
                        self.log(
                            f"SUCCESS GET {url.replace(self.base_url,'')} "
                            f"(lan-networks {api_ver}) rows={len(items)}"
                        )
                        return items
                if isinstance(result, list):
                    self.log(
                        f"SUCCESS GET {url.replace(self.base_url,'')} "
                        f"(lan-networks {api_ver}) rows={len(result)}"
                    )
                    return result
                raise RuntimeError("Unexpected LAN list response format.")
            except Exception as e:
                self.log(f"FAILED GET {url.replace(self.base_url,'')} (lan-networks {api_ver}): {e}")
                last_err = e
        raise RuntimeError(f"All LAN list candidates failed. Last error: {last_err}")

    def get_site_devices(self, site_id: str, page: int = 1, page_size: int = 500) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")

        candidates: List[Tuple[str, str]] = [
            ("v3 devices", f"{self.base_url}/openapi/v3/{self.omadac_id}/sites/{site_id}/devices"),
            ("v2 devices", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/devices"),
            ("v1 devices", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}/devices"),
            ("v1 network devices", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}/networks/devices"),
        ]
        params_list = [
            {"page": page, "pageSize": page_size, "deviceType": "1,2"},
            {"page": page, "pageSize": page_size, "filters.deviceType": "1,2"},
            {"page": page, "pageSize": page_size},
            {"currentPage": page, "currentPageSize": page_size},
        ]

        last_err: Optional[Exception] = None
        for label, url in candidates:
            for params in params_list:
                try:
                    self.log(f"Trying GET {url.replace(self.base_url,'')} ({label}) ...")
                    data = self._req("GET", url, headers=self._auth_headers(), params=params)
                    if data.get("errorCode") != 0:
                        raise RuntimeError(f"Device list error {data.get('errorCode')}: {data.get('msg')}")
                    result = data.get("result", {})
                    if isinstance(result, dict):
                        items = result.get("data")
                        if isinstance(items, list):
                            self.log(
                                f"SUCCESS GET {url.replace(self.base_url,'')} ({label}) rows={len(items)}"
                            )
                            return items
                    if isinstance(result, list):
                        self.log(
                            f"SUCCESS GET {url.replace(self.base_url,'')} ({label}) rows={len(result)}"
                        )
                        return result
                    raise RuntimeError("Unexpected device list response format.")
                except Exception as e:
                    self.log(f"FAILED GET {url.replace(self.base_url,'')} ({label}): {e}")
                    last_err = e

        raise RuntimeError(f"Device list failed. Last error: {last_err}")

    def get_site_gateways(self, site_id: str, page: int = 1, page_size: int = 500) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")

        bases = [
            ("v3", f"{self.base_url}/openapi/v3/{self.omadac_id}/sites/{site_id}"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}"),
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}"),
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
                        self.log(
                            f"SUCCESS GET {url.replace(self.base_url,'')} (gateways {api_ver}) rows={len(items)}"
                        )
                        devices = items
                        break
                raise RuntimeError("Unexpected gateway response format.")
            except Exception as e:
                self.log(f"FAILED GET {url.replace(self.base_url,'')} (gateways {api_ver}): {e}")
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
        endpoint_candidates = [
            ("v3", f"{self.base_url}/openapi/v3/{self.omadac_id}/sites/{site_id}/lan-networks"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/lan-networks"),
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}/lan-networks"),
        ]

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
        last_err: Optional[Exception] = None
        for api_ver, url in endpoint_candidates:
            endpoint_failed = False
            gateway_field_enabled = bool(gateway_device)
            interface_field_enabled = bool(interface_ids)
            self.log(f"Trying POST {url.replace(self.base_url,'')} (create lan {api_ver}) ...")
            for gwsub in gwsub_candidates:
                body = dict(base_body)
                body["gatewaySubnet"] = gwsub
                self.log(
                    f"POST {url.replace(self.base_url,'')} (create lan {api_ver}) "
                    f"(name={plan.name}, vlan={plan.vlan_id}, gatewaySubnet={gwsub})"
                )
                try:
                    data = self._req("POST", url, headers=self._auth_headers(), json_body=body)
                except Exception as exc:
                    endpoint_failed = True
                    last_err = exc
                    self.log(f"FAILED POST {url.replace(self.base_url,'')} (create lan {api_ver}): {exc}")
                    break
                last_data = data
                if data.get("errorCode") == 0:
                    self.log(f"SUCCESS POST {url.replace(self.base_url,'')} (create lan {api_ver})")
                    return data
                msg = (data.get("msg") or "").lower()
                if interface_field_enabled and "interface" in msg and ("does not match" in msg or "port information" in msg):
                    interface_field_enabled = False
                    base_body.pop("interfaceIds", None)
                    body2 = dict(base_body)
                    body2["gatewaySubnet"] = gwsub
                    self.log("Retrying without interfaceIds field ...")
                    data2 = self._req("POST", url, headers=self._auth_headers(), json_body=body2)
                    last_data = data2
                    if data2.get("errorCode") == 0:
                        self.log(f"SUCCESS POST {url.replace(self.base_url,'')} (create lan {api_ver})")
                        return data2
                    msg = (data2.get("msg") or "").lower()
                    data = data2
                if gateway_field_enabled and "gateway" in msg and ("invalid" in msg or "not found" in msg or "not exist" in msg):
                    gateway_field_enabled = False
                    base_body.pop("gateway", None)
                    body2 = dict(base_body)
                    body2["gatewaySubnet"] = gwsub
                    self.log("Retrying without gateway selector field ...")
                    data2 = self._req("POST", url, headers=self._auth_headers(), json_body=body2)
                    last_data = data2
                    if data2.get("errorCode") == 0:
                        self.log(f"SUCCESS POST {url.replace(self.base_url,'')} (create lan {api_ver})")
                        return data2
                    msg2 = (data2.get("msg") or "").lower()
                    if "gatewaysubnet" in msg2 and "invalid" in msg2:
                        continue
                    self.log(
                        f"FAILED POST {url.replace(self.base_url,'')} (create lan {api_ver}): "
                        f"{data2.get('errorCode')} {data2.get('msg')}"
                    )
                    return data2
                if "gatewaysubnet" in msg and "invalid" in msg:
                    continue
                self.log(
                    f"FAILED POST {url.replace(self.base_url,'')} (create lan {api_ver}): "
                    f"{data.get('errorCode')} {data.get('msg')}"
                )
                return data
            if not endpoint_failed:
                self.log(f"FAILED POST {url.replace(self.base_url,'')} (create lan {api_ver})")
        if last_data is not None:
            return last_data
        if last_err is not None:
            return {"errorCode": -1, "msg": f"Create LAN failed on all endpoint candidates: {last_err}"}
        return {"errorCode": -1, "msg": "Unknown error creating LAN network"}
