"""
File: ./tghook/telegram/_delete_webhook.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Project
from ._request import request_telegram


def delete_webhook(bot_token: str) -> None:
    """https://core.telegram.org/bots/api#deletewebhook

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API

    Raises:
        RuntimeError: Failure to communicate with Telegram API
    """
    result = request_telegram(bot_token, "deleteWebhook")
    if not result:
        raise RuntimeError(
            f"deleteWebhook failed. Maybe there wasn't a webhook registered in the first place?"
        )


__all__ = ("delete_webhook",)
