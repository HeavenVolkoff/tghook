# Internal
import ssl
import json
from typing import Dict, List, Tuple, Union, Optional
from pathlib import PurePath
from ipaddress import IPv4Address, AddressValueError
from urllib.error import URLError, HTTPError
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

# Project
from .headers import add_header
from .multipart_form_data import (
    MIME_JSON,
    MIME_UTF_TEXT,
    FormPart,
    MIMEType,
    encode_multipart_formdata,
)

_TELEGRAM_API = "https://api.telegram.org"
_TELEGRM_VALID_PORTS = (443, 80, 88, 8443)


def _parse_webhook(webhook: Union[str, Tuple[str, int], Tuple[IPv4Address, int]]) -> SplitResult:
    if isinstance(webhook, str):
        return urlsplit(webhook, scheme="https")
    else:
        host, port = webhook
        if isinstance(host, IPv4Address):
            host = host.compressed

        return urlsplit(f"{host}:{port}", scheme="https")


def set_webook(
    webhook: Union[str, Tuple[str, int], Tuple[IPv4Address, int]],
    bot_token: str,
    *,
    ip: Optional[IPv4Address] = None,
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
        allowed_updates: Tell Telegram API wheter to delete previous undelivered updates or not.

    Raises:
        ValueError: Incorrect argument value
        RuntimeError: Failure to communicate with Telegram API

    """
    url = _parse_webhook(webhook)
    if url.scheme != "https":
        raise ValueError(f"Webhook URL scheme MUST be https, not: {url.scheme}")
    if url.port and url.port not in _TELEGRM_VALID_PORTS:
        raise ValueError(
            f"Webhook URL port MUST be one of {_TELEGRM_VALID_PORTS}, not: {url.port}"
        )

    if max_connections < 1 or max_connections > 100:
        raise ValueError(f"max_connections must be between 1-100, not: {max_connections}")

    form_data = [
        FormPart(
            name="url",
            data=urlunsplit(url),
            type=MIME_UTF_TEXT,
        ),
        FormPart(
            name="max_connections",
            data=json.dumps(max_connections),
            type=MIME_JSON,
        ),
    ]
    if ip is not None:
        try:
            IPv4Address(url.hostname)
            raise ValueError("ip SHOULD be None when webhook is already an ip addresss")
        except AddressValueError:
            pass

        form_data.append(
            FormPart(
                name="ip_address",
                data=ip.compressed,
                type=MIME_UTF_TEXT,
            )
        )
    if certificate is not None:
        form_data.append(
            FormPart(
                name="certificate",
                data=certificate,
                type=MIMEType("application", "x-pem-file"),
            )
        )
    if allowed_updates is not None:
        form_data.append(
            FormPart(
                name="allowed_updates",
                data=json.dumps(allowed_updates),
                type=MIME_JSON,
            )
        )

    multipart_formdata = encode_multipart_formdata(form_data)

    headers: Dict[str, str] = {}
    add_header(
        headers, "Content-Type", "multipart/form-data", boundary=multipart_formdata.get_boundary()
    )

    try:
        with urlopen(
            Request(
                url=urljoin(_TELEGRAM_API, (PurePath(bot_token) / "setWebhook").as_posix()),
                data=multipart_formdata.as_bytes(),
                method="POST",
                headers=headers,
            ),
            context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH),
        ) as req:
            try:
                res = json.loads(req.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Failed to parse Telegram response") from exc

            if not res.get("ok", False):
                raise RuntimeError(
                    f"Telegram answered with an error: {res.get('error_code', 'unknown')}\n{res.get('description', 'unknown')}"
                )

            if not res.get("result", False):
                raise RuntimeError(
                    f"setWebhook failed. Telegram probably wasn't able to access our server"
                )

    except HTTPError as exc:
        raise RuntimeError(f"Telegram couldn't fulfill the request: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach Telegram due to: {exc.reason}") from exc


def delete_webhook(bot_token: str) -> None:
    """https://core.telegram.org/bots/api#deletewebhook

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API

    Raises:
        RuntimeError: Failure to communicate with Telegram API
    """
    try:
        with urlopen(
            Request(
                url=urljoin(_TELEGRAM_API, (PurePath(bot_token) / "deleteWebhook").as_posix()),
                data="{}".encode(encoding="utf8"),
                method="POST",
                headers={"Content-Type": f"{MIME_JSON.main}/{MIME_JSON.sub}"},
            ),
            context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH),
        ) as req:
            try:
                res = json.loads(req.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Failed to parse Telegram response") from exc

            if not res.get("ok", False):
                raise RuntimeError(
                    f"Telegram answered with an error: {res.get('error_code', 'unknown')}\n{res.get('description', 'unknown')}"
                )

            if not res.get("result", False):
                raise RuntimeError(
                    f"deleteWebhook failed. Maybe there wasn't a webhook registered in the first place?"
                )

    except HTTPError as exc:
        raise RuntimeError(f"ipify couldn't fulfill the request: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach ipify due to: {exc.reason}") from exc


__all__ = ("set_webook", "delete_webhook")
