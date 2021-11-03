# Internal
from typing import Dict, Tuple, Union, Optional, Sequence, NamedTuple
from email.mime import multipart
from email.policy import compat32
from email.generator import Generator
from email.mime.nonmultipart import MIMENonMultipart


class MIMEMultipart(multipart.MIMEMultipart):
    def _write_headers(self, _: Generator) -> None:
        """Don't add headers to top-level, this is handled by HTTP"""


class MIMEType(NamedTuple):
    main: str
    sub: str
    params: Optional[Dict[str, Union[str, None, Tuple[str, Optional[str], str]]]] = None


MIME_JSON = MIMEType("application", "json")
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
    form_data = MIMEMultipart("form-data")

    for part in parts:
        data = MIMENonMultipart(
            part.type.main,
            part.type.sub,
            policy=compat32,
            **(part.type.params if part.type.params else {}),
        )
        del data["MIME-Version"]
        data.add_header("Content-Disposition", f'form-data; name="{part.name}"')
        data.set_payload(part.data)
        form_data.attach(data)

    return form_data


__all__ = ("MIMEType", "MIME_JSON", "MIME_UTF_TEXT", "FormPart", "encode_multipart_formdata")
