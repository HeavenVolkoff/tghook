"""
File: ./tghook/_adhoc_ssl.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from ssl import SSLContext
from typing import Tuple
from datetime import datetime, timezone, timedelta
from tempfile import NamedTemporaryFile
from contextlib import ExitStack

# External
import antenna.security
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Project
from .logger import get_logger

logger = get_logger(__name__)


def generate_adhoc_ssl_pair(organization_name: str, common_name: str) -> Tuple[bytes, bytes]:
    """Generate an adhoc ssl certificate and key

    Modified version of generate_adhoc_ssl_pair from Werkzeug (Copyright 2007 Pallets)
    Original:
        https://github.com/pallets/werkzeug/blob/2dd99eb3cf9c7dd1ece27e36a24242bb02d340ef/src/werkzeug/serving.py#L460-L503
    Licensed under:
        BSD-3-Clause (https://github.com/pallets/werkzeug/blob/bd60d52ba14f32a38caffc674fb17c9090ef70ce/LICENSE.rst)

    Args:
        organization_name: Name of the organization that generated the ssl certificate
        common_name: Common name used to identify the owner of the certificate. (Also used as SubjectAltenativeName)

    Returns:
        Content for the public certificate and private

    """
    pkey = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization_name),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(pkey.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        .add_extension(x509.ExtendedKeyUsage([x509.OID_SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(common_name)]), critical=False)
        .sign(pkey, hashes.SHA256(), backend=default_backend())
    )

    logger.debug("Self signed certificate created for CommonName: %s", common_name)

    return (
        cert.public_bytes(serialization.Encoding.PEM),
        pkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )


def create_server_ssl_context(cert: bytes, key: bytes) -> SSLContext:
    """Given the content of a public certificate and a private key generates a ssl context for use in a HTTP server

    Args:
        cert: Public certificate content
        key: Private key content

    Raises:
        RuntimeError: Failure to create ssl context

    Returns:
        ssl context

    """
    with ExitStack() as stack:
        # We are required to create temporary files for the certificate and key because the underling ssl implementation
        # only loads from files
        cert_temp_file = stack.enter_context(NamedTemporaryFile(mode="w+b"))
        cert_temp_file.write(cert)
        cert_temp_file.flush()
        cert_file = cert_temp_file.name

        key_temp_file = stack.enter_context(NamedTemporaryFile(mode="w+b"))
        key_temp_file.write(key)
        key_temp_file.flush()
        key_file = key_temp_file.name

        return antenna.security.create_server_ssl_context(
            cert_file, key_file, protocols=["http/1.1"]
        )

    raise RuntimeError("Couldn't create ssl context")


__all__ = ("generate_adhoc_ssl_pair", "create_server_ssl_context")
