# Internal
import ssl
import json
from pathlib import PurePath
from urllib.error import URLError, HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

# Project
from . import _constants
from ..http.multipart_form_data import MIME_JSON


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
                url=urljoin(
                    _constants.TELEGRAM_API, (PurePath(bot_token) / "deleteWebhook").as_posix()
                ),
                data="{}".encode(encoding="utf8"),
                method="POST",
                headers={"Content-Type": f"{MIME_JSON.main}/{MIME_JSON.sub}"},
            ),
            context=ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH),
        ) as req:
            try:
                res = json.loads(req.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Failed to parse Telegram response for deleteWebhook") from exc

            if not res.get("ok", False):
                raise RuntimeError(
                    f"Telegram answered deleteWebhook with an error: {res.get('error_code', 'unknown')}\n{res.get('description', 'unknown')}"
                )

            if not res.get("result", False):
                raise RuntimeError(
                    f"deleteWebhook failed. Maybe there wasn't a webhook registered in the first place?"
                )

    except HTTPError as exc:
        raise RuntimeError(f"ipify couldn't fulfill the request: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to reach ipify due to: {exc.reason}") from exc


__all__ = ("delete_webhook",)
