"""
File: ./tghook/telegram/__init__.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Project
from ._get_me import get_me
from ._constants import TELEGRAM_API, TELEGRAM_SUBNETS, TELEGRAM_VALID_PORTS
from ._set_webhook import set_webhook
from ._delete_webhook import delete_webhook

__all__ = (
    "get_me",
    "set_webhook",
    "delete_webhook",
    "TELEGRAM_API",
    "TELEGRAM_SUBNETS",
    "TELEGRAM_VALID_PORTS",
)
