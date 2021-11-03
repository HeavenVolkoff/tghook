"""
File: ./external_ip.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: url_to_video_bot

Copyright (C) 2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

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
