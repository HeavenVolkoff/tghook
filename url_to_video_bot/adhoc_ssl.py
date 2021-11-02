# Internal
from ssl import SSLContext
from typing import Tuple, Optional
from datetime import datetime, timezone, timedelta
from tempfile import NamedTemporaryFile
from contextlib import ExitStack

# External
from cryptography import x509
from antenna.security import create_server_ssl_context
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_adhoc_ssl_pair(
    organization_name: Optional[str] = None, common_name: Optional[str] = None
) -> Tuple[bytes, bytes]:
    """Generate an adhoc ssl certificate and key.
    Modified from: https://github.com/pallets/werkzeug/blob/bd60d52ba14f32a38caffc674fb17c9090ef70ce/src/werkzeug/serving.py#L491
    Licensed under: BSD-3-Clause (https://github.com/pallets/werkzeug/blob/bd60d52ba14f32a38caffc674fb17c9090ef70ce/LICENSE.rst)
    Copyright 2007 Pallets
    """
    pkey = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # pretty damn sure that this is not actually accepted by anyone
    if common_name is None:
        common_name = "*"

    subject = x509.Name(
        [
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME,
                organization_name if organization_name else "Dummy Certificate",
            ),
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

    return (
        cert.public_bytes(serialization.Encoding.PEM),
        pkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ),
    )


def create_ssl_context(
    organization_name: Optional[str] = None, common_name: Optional[str] = None
) -> SSLContext:
    with ExitStack() as stack:
        cert, key = generate_adhoc_ssl_pair(organization_name, common_name)

        cert_temp_file = stack.enter_context(NamedTemporaryFile(mode="w+b"))
        cert_temp_file.write(cert)
        cert_temp_file.flush()
        cert_file = cert_temp_file.name

        key_temp_file = stack.enter_context(NamedTemporaryFile(mode="w+b"))
        key_temp_file.write(key)
        key_temp_file.flush()
        key_file = key_temp_file.name

        return create_server_ssl_context(cert_file, key_file, protocols=["http/1.1"])

    raise RuntimeError("Couldn't create ssl context")


__all__ = ("generate_adhoc_ssl_pair", "create_ssl_context")
