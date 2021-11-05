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
    type: MIMEType


def encode_multipart_formdata(parts: Sequence[FormPart]) -> MIMEMultipart:
    """Encode a sequence of form parts as multipart/form-data

    Args:
        parts: Form parts to be encoded

    Returns:
        High level representation of multipart/form-data

    """
    form_data = MIMEMultipart("form-data", policy=HTTP)

    for part in parts:
        data = MIMENonMultipart(
            part.type.main,
            part.type.sub,
            policy=HTTP,
            **(part.type.params if part.type.params else {}),
        )
        del data["MIME-Version"]
        _type = data["Content-Type"]
        data.add_header("Content-Disposition", f'form-data; name="{part.name}"')
        del data["Content-Type"]
        data.add_header("Content-Type", _type)
        data.set_payload(part.data)
        form_data.attach(data)

    return form_data


__all__ = ("MIMEType", "MIME_JSON", "MIME_UTF_TEXT", "FormPart", "encode_multipart_formdata")
