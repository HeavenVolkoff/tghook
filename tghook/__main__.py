"""
File: ./tghook/__main__.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
import sys
from typing import List, Union, Literal, NoReturn, Optional
from logging import INFO, WARN, DEBUG
from argparse import ArgumentError
from ipaddress import IPv4Address, AddressValueError

# External
from tap import Tap

from tghook import EXTERNAL_HOST_TYPE, __summary__, __version__, start_server
from tghook.logger import set_level
from tghook.example import IMPLEMENTATIONS


def _to_ip_or_host(url: Optional[str]) -> Union[str, None, IPv4Address]:
    if url is None:
        return url
    try:
        return IPv4Address(url)
    except AddressValueError:
        return url


class ArgumentParser(Tap):
    bot_key: str  # Telegram API bot key
    implementation: Literal["url_to_video"]  # Which example bot implementation to use
    host: str = "0.0.0.0"  # Address which the bot server will bind
    port: int = 8443  # Port which the bot server will bind
    verbose: int = 0  # Verbosity level, Maximum is -vv
    external_host: Union[str, None, IPv4Address] = None
    """External name or IPv4 that will be resolved to the host where the bot server is running"""
    external_port: Optional[Literal[80, 88, 443, 8443]] = None
    """External port where the bot server is exposed"""
    alternative_name: Optional[str] = None
    """Alternative name to be used as server hostname, when external_host is an IPv4 address."""

    def configure(self) -> None:
        self.add_argument("bot_key")
        self.add_argument("-i", "--implementation")
        self.add_argument("--verbose", "-v", action="count")
        self.add_argument("--external_host", type=_to_ip_or_host)
        self.add_argument("--version", action="version", version=f"%(prog)s {__version__}")


def main(raw_args: List[str] = sys.argv[1:]) -> NoReturn:
    arg_parser = ArgumentParser(underscores_to_dashes=True, description=__summary__)

    try:
        args = arg_parser.parse_args(raw_args)
    except ArgumentError as exc:
        print(exc.message, file=sys.stderr)
        arg_parser.print_usage()
        sys.exit(1)

    set_level(DEBUG if args.verbose >= 2 else (INFO if args.verbose == 1 else WARN))

    implementation = IMPLEMENTATIONS.get(args.implementation, None)
    if implementation is None:
        print("Invalid implementation", file=sys.stderr)
        arg_parser.print_usage()
        sys.exit(1)

    if args.alternative_name is not None:
        if isinstance(args.external_host, str):
            raise ValueError("Alternative Name can only be used when External Host is an IP")
        external_host: EXTERNAL_HOST_TYPE = (args.alternative_name, args.external_host)
    else:
        external_host = args.external_host

    try:
        start_server(
            implementation,
            args.bot_key,
            host=args.host,
            port=args.port,
            external_host=external_host,
            external_port=args.external_port,
        )
    except Exception:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
