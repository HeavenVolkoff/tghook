# Internal
import signal
from typing import Type, Union, Literal, Optional, overload
from ipaddress import IPv4Address
from threading import Thread
from contextlib import ExitStack
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import BaseServer

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


def shutdown_server_on_error(
    exc: Union[None, BaseException, Type[BaseException]], server: BaseServer
) -> Literal[False]:
    if exc:
        server.shutdown()

    return False


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

    try:
        bot = get_me(bot_token)
    except Exception as exc:
        raise RuntimeError("Failed to authenticate bot with Telegram API") from exc

    # If no external hostname was passed, attempt to retriece host external ip using ipify API
    if external_host is None:
        external_host = retrieve_external_ip()

    if external_port is None:
        external_port = port

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

        # Setup signal handling for graciously finish program
        signal.signal(signal.SIGINT, lambda _, __: server.shutdown())
        signal.signal(signal.SIGTERM, lambda _, __: server.shutdown())

        # Setup context exit handler that shutdown the server if any error hapens for here ownward
        stack.push(
            lambda exc_type, exc, __: shutdown_server_on_error(exc if exc else exc_type, server)  # type: ignore[reportUnknownLambdaType]
        )

        # Setup a context exit callback that simply wait for server to close.
        # This should block the main thread until the server shutdown.
        stack.callback(server_thread.join)

        # Register bot server with telegram API
        set_webhook((external_host, external_port), bot_token, certificate=cert)

        # Setup a context exit callback that unregister this bot server with the telegram API, after it has closed.
        stack.callback(delete_webhook, bot_token)
