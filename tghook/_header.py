# Internal
import re
from typing import List, Union
from ipaddress import IPv4Address, IPv6Address


def parse_identifier(identifier: str) -> Union[str, IPv4Address, IPv6Address]:
    """https://www.rfc-editor.org/rfc/rfc7239#section-6"""

    if not identifier:
        raise ValueError("Identifier must contain a value")

    if identifier == "unknown" or re.match(r"_[A-Za-z0-9_\.\-]+", identifier):
        return identifier

    if identifier.startswith("["):
        host, separator, _ = identifier.rpartition("]:")
        if separator == "]:":
            return IPv6Address(host[1:])
        elif identifier.endswith("]"):
            return IPv6Address(identifier[1:-1])
        else:
            raise ValueError("Invalid IPv6")

    return IPv4Address(identifier.partition(":")[0])


def parse_header_forwarded_for(header: str) -> List[Union[str, IPv4Address, IPv6Address]]:
    """Parse forwarded element for

    Args:
        header: Value for the Forwarded Header

    Links:
        https://www.rfc-editor.org/rfc/rfc7239#section-4

    Raises:
        ValueError: Invalid for= component value

    Returns:
        List of ips defined in forwarded element for

    """
    return [
        parse_identifier(element[2])
        for component in re.split(r"[;,]", header)
        if (element := str(component).strip().partition("="))[0] == "for"
    ]


__all__ = ("parse_header_forwarded_for",)
