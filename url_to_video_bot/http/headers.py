"""Modified version of cpython email.message.Message.add_header
Original:
    https://github.com/python/cpython/blob/e3f877c32d7cccb734f45310f26beeec793364ce/Lib/email/message.py#L39-L71
    https://github.com/python/cpython/blob/e3f877c32d7cccb734f45310f26beeec793364ce/Lib/email/message.py#L515-L543

Licensed under:
    Python Software Foundation License Version 2 (https://github.com/python/cpython/blob/e3f877c32d7cccb734f45310f26beeec793364ce/Lib/email/message.py#L39-L71)
"""

# Internal
import re
from email import utils
from typing import Dict, List, Tuple, Union, Optional

SEMISPACE = "; "
PARAM_TYPE = Union[str, None, Tuple[str, Optional[str], str]]

# Regular expression that matches `special' characters in parameters, the
# existence of which force quoting of the parameter value.
tspecials = re.compile(r'[ \(\)<>@,;:\\"/\[\]\?=]')


def _formatparam(param: str, value: PARAM_TYPE = None, quote: bool = True) -> str:
    """Convenience function to format and return a key=value pair.

    This will quote the value if needed or if quote is true.  If value is a
    three tuple (charset, language, value), it will be encoded according
    to RFC2231 rules.  If it contains non-ascii characters it will likewise
    be encoded according to RFC2231 rules, using the utf-8 charset and
    a null language.

    """
    if value is not None and len(value) > 0:
        # A tuple is used for RFC 2231 encoded parameter values where items
        # are (charset, language, value).  charset is a string, not a Charset
        # instance.  RFC 2231 encoded values are never quoted, per RFC.
        if isinstance(value, tuple):
            # Encode as per RFC 2231
            param += "*"
            value = utils.encode_rfc2231(value[2], value[0], value[1])
            return "%s=%s" % (param, value)
        else:
            try:
                value.encode("ascii")
            except UnicodeEncodeError:
                param += "*"
                value = utils.encode_rfc2231(value, "utf-8", "")
                return f"{param}={value}"
        # BAW: Please check this.  I think that if quote is set it should
        # force quoting even if not necessary.
        if quote or tspecials.search(value):
            return f'{param}="{utils.quote(value)}"'
        else:
            return f"{param}={value}"
    else:
        return param


def add_header(
    headers: Dict[str, str],
    name: str,
    value: Optional[str],
    **params: PARAM_TYPE,
) -> None:
    """Extended header setting.

    name is the header field to add.  keyword arguments can be used to set
    additional parameters for the header field, with underscores converted
    to dashes.  Normally the parameter will be added as key="value" unless
    value is None, in which case only the key will be added.  If a
    parameter value contains non-ASCII characters it can be specified as a
    three-tuple of (charset, language, value), in which case it will be
    encoded according to RFC2231 rules.  Otherwise it will be encoded using
    the utf-8 charset and a language of ''.

    Examples:

    msg.add_header('content-disposition', 'attachment', filename='bud.gif')
    msg.add_header('content-disposition', 'attachment',
                   filename=('utf-8', '', Fußballer.ppt'))
    msg.add_header('content-disposition', 'attachment',
                   filename='Fußballer.ppt'))

    """
    parts: List[str] = []
    for k, v in params.items():
        if v is None:
            parts.append(k.replace("_", "-"))
        else:
            parts.append(_formatparam(k.replace("_", "-"), v))
    if value is not None:
        parts.insert(0, value)
    headers[name] = SEMISPACE.join(parts)


__all__ = ("add_header",)
