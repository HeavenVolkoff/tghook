"""
File: ./tghook/telegram/_request.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import ssl
from typing import Any, Dict, Optional
from urllib.error import URLError, HTTPError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

# External
import orjson

# Project
from ..logger import get_logger
from ._constants import TELEGRAM_API

logger = get_logger(__name__)

# TODO: Make a generic function that handle any telegram type and converts is to bytes
# TODO: It should handle simple json and multipart/form-data for content with InputFile

# TODO: Deduce request from telegram type
def request_telegram(
    bot_token: str,
    method: str,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
) -> Any:
    """Make a request to the Telegram Bot API

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API
        method: Telegram Bot API methof to be called
        data: Data to be sent with request

    Raises:
        RuntimeError: Failure to communicate with Telegram API

    Returns:
        Response from Telegram API

    """
    if headers is None:
        headers = {}

    if data is None:
        req_method = "GET"
        headers.pop("Content-Length", None)
        logger.debug(
            'Making request to Telegram API - "%s /%s"\nheaders: %s', req_method, method, headers
        )
    else:
        req_method = "POST"
        headers["Content-Length"] = str(len(data))
        logger.debug(
            'Making request to Telegram API - "%s /%s"\nheaders: %s\n%s',
            req_method,
            method,
            headers,
            data,
        )

    try:
        with urlopen(
            Request(
                url=urljoin(TELEGRAM_API, quote(f"bot{bot_token}/{method}")),
                data=data,
                method=req_method,
                headers=headers,
            ),
            context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH),
        ) as req:
            try:
                res = orjson.loads(req.read())
            except orjson.JSONEncodeError as exc:
                raise RuntimeError(f"Failed to parse Telegram response for {method}") from exc

            if not res.get("ok", False):
                raise RuntimeError(
                    f"Telegram answered get_me with an error: {res.get('error_code', 'unknown')}\n{res.get('description', 'unknown')}"
                )

            return res.get("result", None)

    except HTTPError as exc:
        raise RuntimeError(
            f"Telegram Bot API couldn't fulfill the {req_method} request for {method}: {exc.code}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach Telegram Bot API due to: {exc.reason}") from exc


__all__ = ("request_telegram",)
