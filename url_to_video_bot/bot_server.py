# Internal
import signal
from typing import Type, Tuple, Union, Literal, Optional
from ipaddress import IPv4Address
from threading import Thread
from contextlib import ExitStack
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import BaseServer

# Project
from .ip import retrieve_external_ip
from .logger import get_logger
from .telegram import set_webook, delete_webhook
from .adhoc_ssl import generate_adhoc_ssl_pair, create_server_ssl_context

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


def start_server(
    bot_token: str,
    host: str = "0.0.0.0",
    port: int = 443,
    *,
    common_name: Optional[str] = None,
    organization_name: Optional[str] = None,
    external_hostname: Union[str, Tuple[IPv4Address, int], None] = None,
) -> None:
    if external_hostname is None:
        external_hostname = (retrieve_external_ip(), port)

    cert, key = generate_adhoc_ssl_pair(organization_name, common_name)

    ssl_context = create_server_ssl_context(cert, key)
    with ExitStack() as stack:
        server = stack.enter_context(ThreadingHTTPServer((host, port), BotRequestHandler))
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

        server_thread = Thread(target=server.serve_forever)
        server_thread.start()

        signal.signal(signal.SIGINT, lambda _, __: server.shutdown())
        signal.signal(signal.SIGTERM, lambda _, __: server.shutdown())

        stack.push(
            lambda exc_type, exc, __: shutdown_server_on_error(exc if exc else exc_type, server)
        )

        stack.callback(server_thread.join)

        set_webook(external_hostname, bot_token, certificate=cert)

        stack.callback(delete_webhook, bot_token)
