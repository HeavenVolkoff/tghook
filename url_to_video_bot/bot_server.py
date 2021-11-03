"""
File: ./bot_server.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: url_to_video_bot

Copyright (C) 2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import signal
from typing import Any, Type, Union, Literal, Optional, overload
from ipaddress import IPv4Address
from threading import Thread
from contextlib import ExitStack
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Project
from .logger import get_logger
from .telegram import get_me, set_webhook, delete_webhook
from .adhoc_ssl import generate_adhoc_ssl_pair, create_server_ssl_context
from .external_ip import retrieve_external_ip

# Telegram subnets are:
#  - 91.108.4.0/22
#  - 149.154.160.0/20
# According to: https://core.telegram.org/bots/webhooks#an-open-port

logger = get_logger(__name__)


class BotRequestHandler(BaseHTTPRequestHandler):
    pass


@overload
def start_server(
    bot_token: str,
    host: str = "0.0.0.0",
    port: int = 443,
    *,
    external_host: str,
    external_port: Optional[int] = None,
    alternative_name: None = None,
) -> None:
    ...


@overload
def start_server(
    bot_token: str,
    host: str = "0.0.0.0",
    port: int = 443,
    *,
    external_host: Optional[IPv4Address] = None,
    external_port: Optional[int] = None,
    alternative_name: Optional[str] = None,
) -> None:
    ...


def start_server(
    bot_token: str,
    host: str = "0.0.0.0",
    port: int = 443,
    *,
    external_host: Union[str, IPv4Address, None] = None,
    external_port: Optional[int] = None,
    alternative_name: Optional[str] = None,
) -> None:
    """Bot server entrypoint

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API
        host: Host used for binding this server socket
        port: Port used for binding this server socket
        organization_name: Name of the organization that generated the ssl certificate
        external_hostname: [description]. Defaults to None.
    """

    logger.info("Starting Telegram bot server...")

    try:
        bot = get_me(bot_token)
    except Exception as exc:
        raise RuntimeError("Failed to authenticate bot with Telegram API") from exc

    logger.info("Sucesscefully connectect to Telegram API")

    logger.info(f"Hello, I am {bot.first_name}, id: {bot.id}")

    if not bot.is_bot:
        logger.warn(f"It seems that I have gained sentience")

    # If no external hostname was passed, attempt to retriece host external ip using ipify API
    if external_host is None:
        external_host = retrieve_external_ip()

    if external_port is None:
        external_port = port

    logger.info(f"Bot server will be exposed at {external_host}:{external_port}")

    # SSL/TLS self-signed certificate
    if alternative_name is not None:
        if isinstance(external_host, str):
            raise ValueError("Alternative Name can only be used when External Host is an IP")

        cert, key = generate_adhoc_ssl_pair(
            f"Telegram Bot: {bot.first_name}", alternative_name, ip_address=external_host
        )
    elif isinstance(external_host, str):
        cert, key = generate_adhoc_ssl_pair(f"Telegram Bot: {bot.first_name}", external_host)
    else:
        cert, key = generate_adhoc_ssl_pair(
            f"Telegram Bot: {bot.first_name}", ip_address=external_host
        )

    # SSL/TLS context for HTTPS
    ssl_context = create_server_ssl_context(cert, key)

    with ExitStack() as stack:
        server = stack.enter_context(ThreadingHTTPServer((host, port), BotRequestHandler))
        # Enable SSL/TLS in server for HTTPS support
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

        # Open server in a new thread
        server_thread = Thread(target=server.serve_forever)
        server_thread.start()

        logger.info(f"Bot server started")

        # Setup signal handling for graciously finish program
        signal.signal(signal.SIGINT, lambda _, __: server.shutdown())
        signal.signal(signal.SIGTERM, lambda _, __: server.shutdown())

        @stack.push
        def shutdown_server_on_error(  # type: ignore[reportUnusedFunction]
            exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], _: Any
        ) -> Literal[False]:
            """Context exit handler that shutdown the server if any error hapens for here ownward"""
            if exc is None and exc_type is not None:
                exc = exc_type()

            if exc:
                logger.error(f"An error occured, shuthing down bot server...", exc_info=exc)
                server.shutdown()

            return False

        @stack.callback
        def join_with_server_thread() -> None:  # type: ignore[reportUnusedFunction]
            """Context exit callback that simply wait for server to close.
            This should block the main thread until the server shutdown.
            """
            server_thread.join()
            logger.warn("Bot server shutted down")

        # Register bot server with telegram API
        set_webhook((external_host, external_port), bot_token, certificate=cert)

        logger.info(f"Telegram API webhook was sucesscefully configures")

        @stack.callback
        def unregister_webhook() -> None:  # type: ignore[reportUnusedFunction]
            """Context exit callback that unregister this bot server with the telegram API, after it has closed"""
            try:
                delete_webhook(bot_token)
            except Exception as exc:
                logger.error("Failed to unregister webhook", exc_info=exc)
            else:
                logger.error("Successfully unregistertered webhook")
