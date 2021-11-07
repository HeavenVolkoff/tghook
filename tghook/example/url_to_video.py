"""
File: ./tghook/example/url_to_video.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import re
from typing import Any, Mapping, Pattern, Callable, Optional, Sequence
from logging import INFO, DEBUG, Logger
from urllib.parse import urlsplit

# External
from yt_dlp import YoutubeDL  # type: ignore

# Project
from ..logger import get_logger
from ..telegram.types import Type, User, Update, SendMessage

logger = get_logger(__name__)


def _debug_workaround_yt_dlp(
    msg: object,
    *args: Any,
    _original_debug: Callable[..., None] = logger.debug,
    **kwargs: Any,
) -> None:
    # For compatability with youtube-dl, both debug and info are passed into debug
    # You can distinguish them by the prefix '[debug] '
    if str(msg).startswith("[debug] "):
        if Logger.root.level <= DEBUG:
            return _original_debug(msg, *args, **kwargs)
    else:
        logger.info(msg, *args, **kwargs)


# Workaround yt_dlp logger backward compability shortcomings
setattr(logger, "debug", _debug_workaround_yt_dlp)
if Logger.root.level == INFO:
    logger.setLevel(DEBUG)

_YDL = YoutubeDL(
    {
        "quiet": True,
        "format": "best",
        "logger": logger,
        "simulate": True,
        "cachedir": False,
        "geo_bypass": True,
        "skip_download": True,
    }
)
_URI_REGEX = re.compile(r"\S+://\S+")
_IGNORED_HOSTNAMES = (re.compile(r"([^\s\.]+\.)?youtube(\.[^\s\.]+)+"), "youtu.be")


def _is_ignored(hostname: str) -> bool:
    for ignored in _IGNORED_HOSTNAMES:
        if isinstance(ignored, Pattern):
            if ignored.match(hostname):
                return True
        elif hostname == ignored:
            return True
    return False


def url_to_video(bot: User, update: Update) -> Optional[SendMessage]:
    message = update.message or update.edited_message
    if message is None or message.text is None:
        return None

    # Parse bot command
    if message.text[0] == "/":
        command, _, who = message.text[1:].partition("@")
        if who and who != bot.username:
            return None

        if command == "start":
            return SendMessage(
                text="""Hello, I am a simple bot that extracts direct link to videos from urls.

To get video url just send me a message with a link, and I will answer as soon as possible.

Some hosts are ignore, because telegram already handles them:
 - youtube

 Check my source code at:
    https://github.com/HeavenVolkoff/tghook/blob/main/tghook/example/url_to_video.py
""",
                chat_id=message.chat.id,
                reply_to_message_id=message.message_id,
            )
        else:
            if who == bot.username or message.chat.type == Type.private:
                return SendMessage(
                    text="Unknown command",
                    chat_id=message.chat.id,
                    reply_to_message_id=message.message_id,
                )

    # Parse text messages
    for url in _URI_REGEX.findall(message.text):
        hostname = urlsplit(url).hostname
        if hostname is None or _is_ignored(hostname):
            continue

        try:
            info = _YDL.extract_info(url, download=False)
        except Exception:
            continue

        if not isinstance(info, Mapping):
            continue

        url = info.get("url", None)
        if url is None:
            formats = info.get("formats", None)
            if not isinstance(formats, Sequence):
                continue

            video_format = formats[-1]
            if not isinstance(video_format, Mapping):
                continue

            url = video_format.get("url", None)

        if url is not None:
            return SendMessage(
                text=url, chat_id=message.chat.id, reply_to_message_id=message.message_id
            )

    if message.chat.type == Type.private:
        return SendMessage(
            text="No video URL found",
            chat_id=message.chat.id,
            reply_to_message_id=message.message_id,
        )

    return None


__all__ = ("url_to_video",)
