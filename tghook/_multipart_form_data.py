"""
File: ./tghook/_multipart_form_data.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from typing import Dict, Tuple, Union, Optional, Sequence, NamedTuple
from email.mime import multipart
from email.policy import HTTP
from email.generator import Generator
from email.mime.nonmultipart import MIMENonMultipart


class MIMEMultipart(multipart.MIMEMultipart):
    def _write_headers(self, _: Generator) -> None:
        """Don't add headers to top-level, this is handled by HTTP"""


class MIMEType(NamedTuple):
    main: str
    sub: str
    params: Optional[Dict[str, Union[str, None, Tuple[str, Optional[str], str]]]] = None


MIME_JSON = MIMEType("application", "json", {"charset": "utf8"})
MIME_UTF_TEXT = MIMEType("text", "plain", {"charset": "utf8"})


class FormPart(NamedTuple):
    name: str
    data: Union[str, bytes]
    type: Optional[MIMEType] = None
    filename: Optional[str] = None


def encode_multipart_formdata(parts: Sequence[FormPart]) -> MIMEMultipart:
    """Encode a sequence of form parts as multipart/form-data

    Args:
        parts: Form parts to be encoded

    Returns:
        High level representation of multipart/form-data

    """
    form_data = MIMEMultipart("form-data", policy=HTTP)

    for part in parts:
        mime_type = part.type if part.type else MIME_UTF_TEXT
        data = MIMENonMultipart(
            mime_type.main,
            mime_type.sub,
            policy=HTTP,
            **(mime_type.params if mime_type.params else {}),
        )

        # This header is only for the email spec
        del data["MIME-Version"]

        # Backup Content-Type to restore it later, if there was one from the beginning
        _type = data["Content-Type"] if part.type else None
        # Remove Content-Type before adding Content-Disposition
        del data["Content-Type"]

        # multipart/form-data requires all partes to have a Content-Disposition header, describing the field
        params = {"name": part.name}
        if part.filename:
            params["filename"] = part.filename
        data.add_header("Content-Disposition", f"form-data", **params)

        if _type:
            # Restore Content-Type after Content-Disposition, this is to emulate common browser behavior
            data.add_header("Content-Type", _type)

        data.set_payload(part.data)

        form_data.attach(data)

    return form_data


__all__ = ("MIMEType", "MIME_JSON", "MIME_UTF_TEXT", "FormPart", "encode_multipart_formdata")
