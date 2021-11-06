"""
File: ./tghook/telegram/_constants.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from ipaddress import IPv4Network

# According to: https://core.telegram.org/bots/webhooks#an-open-port
_telegram_subnets = (IPv4Network("91.108.4.0/22"), IPv4Network("149.154.160.0/20"))

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_SUBNETS = (
    (
        *_telegram_subnets,
        IPv4Network("10.0.0.0/8"),
        IPv4Network("127.0.0.0/8"),
        IPv4Network("172.16.0.0/12"),
        IPv4Network("192.168.0.0/16"),
    )
    if __debug__
    else _telegram_subnets
)
TELEGRAM_VALID_PORTS = (443, 80, 88, 8443)

__all__ = ("TELEGRAM_API", "TELEGRAM_SUBNETS", "TELEGRAM_VALID_PORTS")
