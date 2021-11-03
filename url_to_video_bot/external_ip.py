# Internal
import ssl
import json
from ipaddress import IPv4Address
from urllib.error import URLError, HTTPError
from urllib.request import urlopen


def retrieve_external_ip() -> IPv4Address:
    """Retrieve host machine externally facing ip address through ipify API

    Raises:
        RuntimeError: Failure to communicate with ipify API

    Returns:
        Machine's externally facing ip address

    """
    try:
        with urlopen(
            "http://api.ipify.org/?format=json",
            context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH),
        ) as req:
            try:
                res = json.loads(req.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Failed to parse ipify response") from exc

            ip = res.get("ip", None)
            if not isinstance(ip, str):
                raise RuntimeError("ipify returned an invalid response")

            try:
                return IPv4Address(ip)
            except ValueError as exc:
                raise RuntimeError("ipify returned an invalid response") from exc

    except HTTPError as exc:
        raise RuntimeError(f"ipify couldn't fulfill the request: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach ipify due to: {exc.reason}") from exc


__all__ = ("retrieve_external_ip",)
