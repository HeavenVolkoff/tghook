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
import os
import re
import sys
import shlex
from typing import Union, Literal, NoReturn, Optional, Sequence
from logging import INFO, WARN, DEBUG
from argparse import ArgumentError
from ipaddress import IPv4Address, IPv6Address, AddressValueError

# External
from tap import Tap

from tghook import EXTERNAL_HOST_TYPE, __summary__, __version__, start_server
from tghook.logger import set_level
from tghook.example import IMPLEMENTATIONS

DOMAIN_REGEX = re.compile(
    # Courtesy of https://github.com/kvesteri/validators/blob/ad231676892d144250673d264ba459b2e860478e/validators/domain.py#L6-L9
    # MIT Licensed, Copyright (c) 2013-2014 Konsta Vesterinen
    r"^(?:[a-zA-Z0-9]"  # First character of the domain
    r"(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)"  # Sub domain + hostname
    r"+[A-Za-z0-9][A-Za-z0-9-_]{0,61}"  # First 61 characters of the gTLD
    r"[A-Za-z]$"  # Last character of the gTLD
)


def _to_ip_or_host(
    hostname: Union[str, None, IPv4Address, IPv6Address]
) -> Union[str, None, IPv4Address, IPv6Address]:
    """Parse argument into IPv4Address or leave it as is for hostnames

    Args:
        hostname: Hostname to be parsed

    Returns:
        IP or Hostname

    """
    if hostname is None or isinstance(hostname, (IPv4Address, IPv6Address)):
        return hostname

    try:
        return IPv4Address(hostname)
    except AddressValueError:
        try:
            return IPv6Address(hostname)
        except AddressValueError:
            pass

    if not DOMAIN_REGEX.match(hostname.encode("idna").decode("ascii")):
        raise ValueError(f"Hostname should be a valid domain name")

    return hostname


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
        # Load arguments from environment variables
        environ_config = []
        for variable in self.class_variables:
            envvar = f"TGHOOK_{variable.upper()}"
            if envvar in os.environ and os.environ[envvar]:
                if self._underscores_to_dashes:
                    variable = variable.replace("_", "-")
                environ_config.append(f"--{variable}={shlex.quote(os.environ[envvar])}")
        if len(environ_config) > 0:
            self.args_from_configs.insert(0, " ".join(environ_config))

        # More advanced argparse configurations
        self.add_argument("bot_key")
        self.add_argument("-i", "--implementation")
        self.add_argument("--verbose", "-v", action="count")
        self.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    def process_args(self) -> None:
        external_host = _to_ip_or_host(self.external_host)

        if isinstance(external_host, IPv6Address) or (
            isinstance(_to_ip_or_host(self.host), IPv6Address) and external_host is None
        ):
            raise ValueError(
                "Host can't be an IPv6Address, because Telegram doesn't support IPv6 webhooks"
            )

        self.external_host = external_host


def main(raw_args: Sequence[str] = sys.argv[1:]) -> NoReturn:
    arg_parser = ArgumentParser(underscores_to_dashes=True, description=__summary__)

    # Workaround TAP using simple split instead of shlex.split in args_from_configs
    raw_args = [
        *(
            arg
            for args_from_config in arg_parser.args_from_configs
            for arg in shlex.split(args_from_config)
        ),
        *raw_args,
    ]
    arg_parser.args_from_configs = []

    try:
        args = arg_parser.parse_args(raw_args)
    except ArgumentError as exc:
        print(exc.message, file=sys.stderr)
        arg_parser.print_usage()
        sys.exit(1)

    # Set logger lever according to user choise, default is WARN
    set_level(DEBUG if args.verbose >= 2 else (INFO if args.verbose == 1 else WARN))

    # Get example bot implementation according to user choise
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
    except BrokenPipeError:
        # https://docs.python.org/3/library/signal.html#note-on-sigpipe
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(r"\nERROR: {err}")
    except Exception:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
