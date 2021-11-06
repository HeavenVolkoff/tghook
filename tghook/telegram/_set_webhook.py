"""
File: ./tghook/telegram/_set_webhook.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from typing import List, Tuple, Union, Optional
from ipaddress import IPv4Address, AddressValueError
from urllib.parse import SplitResult, quote, urljoin, urlsplit, urlunsplit

# Project
from ._request import request_telegram
from ._constants import TELEGRAM_VALID_PORTS
from .._multipart_form_data import FormPart, MIMEType, encode_multipart_formdata


def _parse_webhook(webhook: Union[str, Tuple[Union[str, IPv4Address], int]]) -> SplitResult:
    if isinstance(webhook, str):
        return urlsplit(webhook, scheme="https")
    else:
        host, port = webhook
        if isinstance(host, IPv4Address):
            host = host.compressed

        return urlsplit(f"//{host}:{port}", scheme="https")


def set_webhook(
    webhook: Union[str, Tuple[Union[str, IPv4Address], int]],
    bot_token: str,
    *,
    ip_address: Optional[IPv4Address] = None,
    certificate: Optional[bytes] = None,
    max_connections: int = 10,
    allowed_updates: Optional[List[str]] = None,
) -> None:
    """https://core.telegram.org/bots/api#setwebhook

    Args:
        webhook: Webhook url or (host, port) to be used by the Telegram API to send new updates
        bot_token: Telegram bot token, for authentication with the Telegram API
        ip: Tell Telegram API to bypass webhook url resolution and use this ip instead
        certificate: Self-signed public certificate content tobe used by the Telegram API during communication
        max_connections: Tell Telegram API the maximum number of concurrent connections the webhook server can handle
        allowed_updates: Tell Telegram API wether to delete previous undelivered updates or not.

    Raises:
        ValueError: Incorrect argument value
        RuntimeError: Failure to communicate with Telegram API

    """
    url = _parse_webhook(webhook)
    if url.scheme != "https":
        raise ValueError(f"Webhook URL scheme MUST be https, not: {url.scheme}")
    if url.port and url.port not in TELEGRAM_VALID_PORTS:
        raise ValueError(
            f"Webhook URL port MUST be one of {TELEGRAM_VALID_PORTS}, not: {url.port}"
        )

    if max_connections < 1 or max_connections > 100:
        raise ValueError(f"max_connections must be between 1-100, not: {max_connections}")

    form_data = [
        FormPart(name="url", data=urljoin(urlunsplit(url), quote(bot_token))),
        FormPart(name="max_connections", data=str(max_connections)),
    ]
    if ip_address is not None:
        try:
            IPv4Address(url.hostname)
            raise ValueError("ip SHOULD be None when webhook is already an ip address")
        except AddressValueError:
            pass

        form_data.append(FormPart(name="ip_address", data=ip_address.compressed))
    if certificate is not None:
        form_data.append(
            FormPart(
                name="certificate",
                data=certificate,
                type=MIMEType("application", "octet-stream"),
                filename="cert.pem",
            )
        )
    if allowed_updates is not None:
        form_data.append(FormPart(name="allowed_updates", data=str(allowed_updates)))

    multipart_formdata = encode_multipart_formdata(form_data)

    # WARNING: MUST execute multipart_formdata.as_bytes BEFORE multipart_formdata.get_boundary
    #          because the message boundary is generated when getting data. So, if the order is
    #          reversed get_boundary WILL return
    data = multipart_formdata.as_bytes()
    response = request_telegram(
        bot_token,
        "setWebhook",
        {"Content-Type": f"multipart/form-data; boundary={multipart_formdata.get_boundary()}"},
        data,
    )

    if not response:
        raise RuntimeError(
            f"setWebhook failed. Telegram probably wasn't able to access our server"
        )


__all__ = ("set_webhook",)
