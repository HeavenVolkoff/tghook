"""
File: ./tghook/_bot_server.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import signal
from ssl import SSLContext
from sys import exc_info
from socket import socket
from typing import Any, Type, Tuple, Union, Literal, Callable, Optional
from hashlib import md5
from ipaddress import IPv4Address
from threading import Thread
from contextlib import ExitStack
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import BaseServer, BaseRequestHandler
from urllib.parse import unquote

# External
import orjson

# Project
from .logger import get_logger
from ._header import parse_header_forwarded_for
from .telegram import TELEGRAM_SUBNETS, get_me, set_webhook, delete_webhook
from ._adhoc_ssl import generate_adhoc_ssl_pair, create_server_ssl_context
from ._external_ip import retrieve_external_ip
from .telegram.types import User, Update, RequestTypes
from ._multipart_form_data import MIME_JSON

logger = get_logger(__name__)

EXTERNAL_HOST_TYPE = Union[str, None, IPv4Address, Tuple[str, Optional[IPv4Address]]]


class BotRequestHandler(BaseHTTPRequestHandler):
    # Bump http version for keep_alive
    # https://docs.python.org/3/library/http.server.html#http.server.BaseHTTPRequestHandler.protocol_version
    protocol_version = "HTTP/1.1"

    def __init__(
        self,
        request: bytes,
        client_address: Tuple[str, int],
        server: BaseServer,
        *,
        bot: User,
        bot_impl: Callable[[User, Update], Optional[RequestTypes]],
        bot_token: str,
    ) -> None:
        # All custom code must come before super().__init__, due to how request are handled
        greetings = (
            f'You can talk to me <a href="https://t.me/{bot.username}">here</a>'
            if bot.username
            else ""
        )
        self._bot = bot
        self._impl = bot_impl
        self._token = bot_token
        self._update_id = 0
        self._greetings = (
            f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{bot.first_name}</title>
</head>
<body>
    <h2>Hello, I am a Telegram Bot.</h2>
    {greetings}
</body>
</html>"""
        ).encode("utf8")
        self._greetings_etag = md5(self._greetings).hexdigest() + "-1"

        super().__init__(request, client_address, server)

    @property
    def proper_path(self) -> str:
        return unquote(self.path)

    def log_error(self, format: str, *args: Any) -> None:
        logger.error(f"Request from: %s - {format}", self.address_string(), *args)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"Request from: %s - {format}", self.address_string(), *args)

    def do_HEAD(self) -> bool:
        if self.proper_path != "/":
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
        if self.proper_path != f"/{self._token}":
            self.send_error(404, explain="Request is probably NOT from Telegram API")
            return

        try:
            client_address = parse_header_forwarded_for(self.headers.get("Forwarded", ''))[0]
            if not isinstance(client_address, IPv4Address):
                raise ValueError('Telegram client must be a IPv4Address')
        except ValueError:
            try:
                client_address = IPv4Address(self.client_address[0])
            except ValueError:
                # https://core.telegram.org/bots/webhooks#the-short-version
                # https://datatracker.ietf.org/doc/html/rfc7540#section-9.1.2
                self.send_error(421, explain="Telegram API only communicates with IPv4")
                return

        if not any(client_address in subnet for subnet in TELEGRAM_SUBNETS):
            # TODO: Add logic for limiting clients that are outside telegram subnets and that send invalid data
            logger.warn(
                "Bot resquest comes from an address outside the known telegram subnets. %s not in %s",
                client_address,
                TELEGRAM_SUBNETS,
            )

        # TODO: Validate Content-Type and Content-Encoding before reading body, answer with 415 if invalid
        try:
            update_raw = orjson.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            update = Update.parse_obj(update_raw)
        except Exception as exc:
            logger.error("Telegram API sent an invalid Update object", exc_info=exc)
            self.send_error(400)
            return

        # Ignore already processed updates
        if update.update_id <= self._update_id:
            self.send_response(202)
            self.end_headers()
            return

        logger.debug("Telegram API sent an Update: %s", update_raw)
        del update_raw

        try:
            res = self._impl(self._bot, update)
        except Exception as exc:
            logger.error("Bot implementation failed", exc_info=exc)
            self.send_error(500)
            return

        if res is None:  # TODO: Validate Accept and Accept-Encoding headers before sending data
            self.send_response(200)
            self.end_headers()
        else:
            # TODO: Implement multipart/form-data for response types that have InputFile
            try:
                data_dict = res.dict(skip_defaults=True)
                method = type(res).__name__

                logger.debug("Answering request with %s: %s", method, data_dict)

                data = orjson.dumps({**data_dict, "method": method[0].lower() + method[1:]})
            except Exception as exc:
                logger.error("Failed to serialize bot implementation response", exc_info=exc)
                self.send_error(500)
                return

            self.send_response(200)
            self.send_header("Content-Type", f"{MIME_JSON.main}/{MIME_JSON.sub}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()

            self.wfile.write(data)

        # Update tracking id
        self._update_id = update.update_id


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

    def finish_request(
        self,
        request: Union[socket, Tuple[bytes, socket]],
        client_address: Union[Tuple[str, int], str],
    ) -> None:
        self.RequestHandlerClass(request, client_address, self, **self._request_handler_kwargs)

    def handle_error(
        self,
        request: Union[socket, Tuple[bytes, socket]],
        client_address: Union[Tuple[str, int], str],
    ) -> None:
        logger.error(
            "Error occurred during processing of request from %s",
            client_address,
            exc_info=exc_info(),
        )


def start_server(
    bot_impl: Callable[[User, Update], Optional[RequestTypes]],
    bot_token: str,
    *,
    ssl: Union[bool, SSLContext] = True,
    host: str = "0.0.0.0",
    port: int = 443,
    external_host: EXTERNAL_HOST_TYPE = None,
    external_port: Optional[int] = None,
) -> None:
    """Bot server entrypoint

    Args:
        bot_token: Telegram bot token, for authentication with the Telegram API
        host: Host used for binding this server socket
        port: Port used for binding this server socket
        external_host: External hostname that will be resolved to the host where the bot server is running
        external_port: External port where the bot server is exposed

    """
    cert: Optional[bytes] = None

    logger.info("Starting Telegram bot server...")

    try:  # Retrieve bot information from Telegram API
        bot = get_me(bot_token)
    except Exception as exc:
        raise RuntimeError("Failed to authenticate bot with Telegram API") from exc

    logger.info("Hello, I am %s (id: %d)", bot.first_name, bot.id)

    if not bot.is_bot:  # Hun?!
        logger.warn(f"It seems that I have gained sentience")

    # Retrieve alternative_name argument
    alternative_name = None
    if isinstance(external_host, tuple):
        alternative_name, external_host = external_host

    # If no external hostname was passed, attempt to retrieve host external ip using ipify API
    if external_host is None:
        external_host = retrieve_external_ip()

    if external_port is None:
        external_port = port

    with ExitStack() as stack:
        server = stack.enter_context(
            HTTPServer(
                (host, port),
                BotRequestHandler,
                bot=bot,
                bot_impl=bot_impl,
                bot_token=bot_token,
            )
        )

        if ssl:  # Wrap TCP socket with SSL/TLS to enable HTTPS support in the server
            if not isinstance(ssl, SSLContext):
                # SSL/TLS self-signed certificate
                if isinstance(external_host, IPv4Address):
                    if alternative_name is None:
                        alternative_name = f"{bot.first_name.lower()}.bot"

                    cert, key = generate_adhoc_ssl_pair(
                        f"Telegram Bot: {bot.first_name}", alternative_name
                    )
                else:
                    if alternative_name is not None:
                        raise ValueError(
                            "Alternative Name can only be used when External Host is an IP"
                        )

                    cert, key = generate_adhoc_ssl_pair(
                        f"Telegram Bot: {bot.first_name}", external_host
                    )

                ssl = create_server_ssl_context(cert, key)
            server.socket = ssl.wrap_socket(server.socket, server_side=True)
        elif not isinstance(external_host, str):
            logger.warn(
                "Telegram REQUIRES webhooks to have SSL enabled. "
                "Only run with SSL disable if behind a reverse proxy with SSL termination"
            )

        # Open server in a new thread
        server_thread = Thread(target=server.serve_forever)
        server_thread.start()

        logger.info("Bot server started. Address: %s:%d", external_host, external_port)

        # Setup signal handling for gracious shutdown
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
            if isinstance(external_host, IPv4Address):
                raise ValueError(
                    "External Host is an IP. This requires an alternative host name, for correct certificate validation"
                )
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


__all__ = ("start_server", "EXTERNAL_HOST_TYPE")
