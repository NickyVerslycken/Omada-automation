#!/usr/bin/env python3
"""
Probe Omada OpenAPI to discover gateway and interface fields.

Usage examples:
  python omada_gateway_probe.py --base-url https://192.168.6.101 --client-id XXX --client-secret YYY
  python omada_gateway_probe.py --base-url https://192.168.6.101 --client-id XXX --client-secret YYY --site-id 68ca...
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional, Tuple

import requests


class OmadaProbe:
    def __init__(self, base_url: str, verify_ssl: bool = True, timeout: int = 25):
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self.omadac_id: Optional[str] = None
        self.access_token: Optional[str] = None

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
        return resp.json()

    def _auth_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise RuntimeError("Access token missing.")
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
                data = self._req("POST", url, params=params, json_body=jbody, form_body=fbody)
                if data.get("errorCode") != 0:
                    last_err = f"{data.get('errorCode')}: {data.get('msg')}"
                    continue
                result = data.get("result", {})
                token = result.get("accessToken") if isinstance(result, dict) else None
                if not token:
                    last_err = f"Token missing in response for {label}: {data}"
                    continue
                self.access_token = token
                return token
            except Exception as e:
                last_err = str(e)

        raise RuntimeError(f"Token error: {last_err or 'unknown'}")

    def get_sites(self) -> List[Dict[str, Any]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")
        params = {"page": 1, "pageSize": 100}
        candidates = [
            f"{self.base_url}/openapi/v2/{self.omadac_id}/sites",
            f"{self.base_url}/openapi/v1/{self.omadac_id}/sites",
        ]
        last_err: Optional[Exception] = None
        for url in candidates:
            try:
                data = self._req("GET", url, headers=self._auth_headers(), params=params)
                if data.get("errorCode") != 0:
                    raise RuntimeError(f"Sites error {data.get('errorCode')}: {data.get('msg')}")
                result = data.get("result", {})
                return result.get("data", []) if isinstance(result, dict) else []
            except Exception as e:
                last_err = e
        raise RuntimeError(f"All site list candidates failed. Last error: {last_err}")

    def get_devices(self, site_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        if not self.omadac_id:
            raise RuntimeError("omadacId unknown.")
        candidates = [
            ("v1", f"{self.base_url}/openapi/v1/{self.omadac_id}/sites/{site_id}/devices"),
            ("v2", f"{self.base_url}/openapi/v2/{self.omadac_id}/sites/{site_id}/devices"),
        ]
        params_list = [
            {"page": 1, "pageSize": 500, "deviceType": "gateway"},
            {"page": 1, "pageSize": 500},
            {"currentPage": 1, "currentPageSize": 500},
        ]
        last_err: Optional[Exception] = None
        for api_ver, url in candidates:
            for params in params_list:
                try:
                    data = self._req("GET", url, headers=self._auth_headers(), params=params)
                    if data.get("errorCode") != 0:
                        raise RuntimeError(f"Devices error {data.get('errorCode')}: {data.get('msg')}")
                    result = data.get("result", {})
                    items = result.get("data") if isinstance(result, dict) else None
                    if isinstance(items, list):
                        return api_ver, items
                except Exception as e:
                    last_err = e
        raise RuntimeError(f"Devices query failed. Last error: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--site-id", default="")
    ap.add_argument("--verify-ssl", action="store_true")
    args = ap.parse_args()

    probe = OmadaProbe(args.base_url, verify_ssl=bool(args.verify_ssl))
    info = probe.get_controller_info()
    print("Controller info:", json.dumps(info.get("result", {}), indent=2))

    if args.site_id:
        probe.omadac_id = probe.omadac_id or info.get("result", {}).get("omadacId")
    probe.get_access_token_client_credentials(args.client_id, args.client_secret, omadac_id=probe.omadac_id)

    if not args.site_id:
        sites = probe.get_sites()
        print("Sites:")
        for s in sites:
            print(f"- {s.get('name')}  [{s.get('siteId')}]")
        if not sites:
            return
        site_id = sites[0].get("siteId")
    else:
        site_id = args.site_id

    api_ver, devices = probe.get_devices(site_id)
    print(f"Devices API version: {api_ver}")
    print(f"Devices returned: {len(devices)}")

    # Print only gateway-looking devices, include interface-related fields.
    gateways = []
    for d in devices:
        dtype = str(d.get("deviceType") or d.get("type") or d.get("role") or "").lower()
        if dtype and "gateway" not in dtype and "router" not in dtype:
            continue
        gateways.append(d)

    if not gateways:
        print("No gateway devices found in response. Dumping first device for inspection:")
        if devices:
            print(json.dumps(devices[0], indent=2))
        return

    print(f"Gateways returned: {len(gateways)}")
    for g in gateways:
        name = g.get("name") or g.get("customName") or g.get("deviceName") or g.get("displayName")
        print("=" * 60)
        print("Gateway name:", name)
        print("deviceId:", g.get("deviceId") or g.get("id"))
        keys = [
            "interfaceIds",
            "interfaces",
            "ports",
            "lanPorts",
            "wanPorts",
            "lanPort",
            "wanPort",
            "portList",
            "ifList",
        ]
        for k in keys:
            if k in g:
                print(f"{k}: {json.dumps(g.get(k), indent=2)}")
        print("Full gateway object:")
        print(json.dumps(g, indent=2))


if __name__ == "__main__":
    main()
