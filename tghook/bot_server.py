"""
File: ./tghook/bot_server.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import json
import signal
from typing import Any, Type, Tuple, Union, Literal, Callable, Optional, overload
from hashlib import md5
from ipaddress import IPv4Address
from threading import Thread
from contextlib import ExitStack
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import BaseServer, BaseRequestHandler

# Project
from .logger import get_logger
from .telegram import TELEGRAM_SUBNETS, get_me, set_webhook, delete_webhook
from ._adhoc_ssl import generate_adhoc_ssl_pair, create_server_ssl_context
from ._external_ip import retrieve_external_ip
from .telegram.types import Update, RequestTypes
from ._multipart_form_data import MIME_JSON

logger = get_logger(__name__)


class BotRequestHandler(BaseHTTPRequestHandler):
    # Bump http version for keep_alive
    protocol_version = "HTTP/1.1"

    def __init__(
        self,
        request: bytes,
        client_address: Tuple[str, int],
        server: BaseServer,
        *,
        bot_impl: Callable[[Update], Optional[RequestTypes]],
        bot_name: Optional[str],
        bot_token: str,
    ) -> None:
        # All custom code must come before super().__init__, due to how request are handled
        greetings = (
            f'You can talk to me <a href="https://t.me/{bot_name}">here</a>' if bot_name else ""
        )
        self._impl = bot_impl
        self._token = bot_token
        self._greetings = (
            f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{bot_name}</title>
</head>
<body>
    <h2>Hello, I am a Telegram Bot.</h2>
    {greetings}
</body>
</html>"""
        ).encode("utf8")
        self._greetings_etag = md5(self._greetings).hexdigest() + "-1"

        super().__init__(request, client_address, server)

    def log_error(self, format: str, *args: Any) -> None:
        logger.error(f"Request from: %s - {format}", self.address_string(), *args)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"Request from: %s - {format}", self.address_string(), *args)

    def do_HEAD(self) -> bool:
        if self.path != "/":
            self.send_error(404)
            return False

        self.send_response(200)
        self.send_header("Etag", str(self._greetings_etag))
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self._greetings)))
        self.end_headers()
        return True

    def do_GET(self) -> None:
        if not self.do_HEAD():
            return

        if not self.wfile.closed:
            self.wfile.write(self._greetings)

    def do_POST(self) -> None:
        if self.path != f"/{self._token}":
            self.send_error(404, explain="Request is probably NOT from Telegram API")
            return

        client_address = IPv4Address(self.client_address[0])
        if not any(client_address in subnet for subnet in TELEGRAM_SUBNETS):
            logger.warn(
                "Bot resquest comes from an address outside the known telegram subnets. %s not in %s",
                client_address,
                TELEGRAM_SUBNETS,
            )

        try:
            update = Update(
                **json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
                )
            )
        except Exception as exc:
            logger.error("Telegram API sent an invalid Update object", exc_info=exc)
            self.send_error(400)
            return

        try:
            res = self._impl(update)
        except Exception as exc:
            logger.error("Bot implementation failed", exc_info=exc)
            self.send_error(500)
            return

        if res is None:
            self.send_response(200)
            self.end_headers()
        else:
            # TODO: Implement multipart/form-data for response types that have InputFile
            try:
                data = res.json().encode("utf-8")
            except Exception as exc:
                logger.error("Failed to serialize bot implementation response", exc_info=exc)
                self.send_error(500)
                return

            self.send_response(200)
            self.send_header("Content-type", f"{MIME_JSON.main}/{MIME_JSON.sub}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()


class HTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        RequestHandlerClass: Callable[..., BaseRequestHandler],
        bind_and_activate: bool = True,
        **request_handler_kwargs: Any,
    ) -> None:
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self._request_handler_kwargs = request_handler_kwargs

    # Pyright is wrong
    def finish_request(  # type: ignore[reportIncompatibleMethodOverride]
        self,
        request: bytes,
        client_address: Union[Tuple[str, int], str],
    ) -> None:
        self.RequestHandlerClass(request, client_address, self, **self._request_handler_kwargs)


@overload
def start_server(
    bot_impl: Callable[[Update], Optional[RequestTypes]],
    bot_token: str,
    *,
    host: str = "0.0.0.0",
    port: int = 443,
    external_host: str,
    external_port: Optional[int] = None,
    alternative_name: None = None,
) -> None:
    ...


@overload
def start_server(
    bot_impl: Callable[[Update], Optional[RequestTypes]],
    bot_token: str,
    *,
    host: str = "0.0.0.0",
    port: int = 443,
    external_host: Optional[IPv4Address] = None,
    external_port: Optional[int] = None,
    alternative_name: Optional[str] = None,
) -> None:
    ...


def start_server(
    bot_impl: Callable[[Update], Optional[RequestTypes]],
    bot_token: str,
    *,
    host: str = "0.0.0.0",
    port: int = 443,
    external_host: Union[str, IPv4Address, None] = None,
    external_port: Optional[int] = None,
    alternative_name: Optional[str] = None,
) -> None:
    """Bot server entrypoint

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API
        host: Host used for binding this server socket
        port: Port used for binding this server socket
        external_host: External hostname that will be resolved to the host where the bot server is running
        external_port: External port where the bot server is exposed
        alternative_name: Alternative name to be used as server hostname, when external_host is an IPv4 address.

    """
    logger.info("Starting Telegram bot server...")

    try:
        bot = get_me(bot_token)
    except Exception as exc:
        raise RuntimeError("Failed to authenticate bot with Telegram API") from exc

    logger.info("Successfully connectect to Telegram API")

    logger.info(f"Hello, I am %s (id: %d)", bot.first_name, bot.id)

    if not bot.is_bot:
        logger.warn(f"It seems that I have gained sentience")

    # If no external hostname was passed, attempt to retrieve host external ip using ipify API
    if external_host is None:
        external_host = retrieve_external_ip()

    if external_port is None:
        external_port = port

    logger.info(f"Bot server will be exposed at %s:%d", external_host, external_port)

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
        server = stack.enter_context(
            HTTPServer(
                (host, port),
                BotRequestHandler,
                bot_name=bot.username,
                bot_token=bot_token,
                bot_impl=bot_impl,
            )
        )
        # Enable SSL/TLS in server for HTTPS support
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

        # Open server in a new thread
        server_thread = Thread(target=server.serve_forever)
        server_thread.start()

        logger.info(f"Bot server started")

        # Setup signal handling for graciously finish program
        signal.signal(signal.SIGINT, lambda _, __: server.shutdown())
        signal.signal(signal.SIGTERM, lambda _, __: server.shutdown())

        @stack.push  # Pyright does not recognize annotating a function as usage
        def shutdown_server_on_error(  # type: ignore[reportUnusedFunction]
            exc_type: Optional[Type[BaseException]], exc: Optional[BaseException], _: Any
        ) -> Literal[False]:
            """Context exit handler that shutdown the server if any error hapens for here onward"""
            if exc is None and exc_type is not None:
                exc = exc_type()

            if exc:
                logger.error(f"An error occurred, shuthing down bot server...", exc_info=exc)
                server.shutdown()

            return False

        logger.info(f"Configuring Telegram API webhook...")

        # Register bot server with telegram API
        if alternative_name:
            if isinstance(external_host, str):
                raise ValueError("Alternative Name can only be used when External Host is an IP")
            set_webhook(
                (alternative_name, external_port),
                bot_token,
                ip_address=external_host,
                certificate=cert,
            )
        else:
            set_webhook((external_host, external_port), bot_token, certificate=cert)

        logger.info(f"Telegram API webhook was successfully registered")

        @stack.callback  # Pyright does not recognize annotating a function as usage
        def unregister_webhook() -> None:  # type: ignore[reportUnusedFunction]
            """Context exit callback that unregister this bot server with the telegram API, after it has closed"""
            try:
                delete_webhook(bot_token)
            except Exception as exc:
                logger.error("Failed to unregister webhook", exc_info=exc)
            else:
                logger.warn("Telegram API webhook was successfully unregistered")

        # Wait for server to close.
        # This should block the main thread until server shutdown is called.
        server_thread.join()

        logger.warn("Bot server shutted down")


__all__ = ("start_server",)
