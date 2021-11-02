# Internal
from typing import Optional
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Project
from .adhoc_ssl import create_ssl_context


class BotRequestHandler(BaseHTTPRequestHandler):
    pass


def start_server(
    host: str = "0.0.0.0",
    port: int = 443,
    *,
    organization_name: Optional[str] = None,
    common_name: Optional[str] = None,
) -> None:
    server = ThreadingHTTPServer((host, port), BotRequestHandler)
    ssl_context = create_ssl_context(organization_name, common_name)

    server.socket = ssl_context.wrap_socket(
        server.socket,
        server_side=True,
        server_hostname=None if common_name == "*" else common_name,
    )

    server.serve_forever()
