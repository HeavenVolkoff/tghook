"""Modified version of LogFormatter from Tornado (Copyright 2009 Facebook)
Original:
    https://github.com/tornadoweb/tornado/blob/1db5b45918da8303d2c6958ee03dbbd5dc2709e9/tornado/log.py#L81-L208
Licensed under:
    Apache-2.0 License (https://github.com/tornadoweb/tornado/blob/1db5b45918da8303d2c6958ee03dbbd5dc2709e9/LICENSE)
"""

# Internal
import os
import sys
from pprint import PrettyPrinter
from typing import Any, Dict, Tuple, AnyStr, Literal, Callable, Optional, Sequence
from logging import INFO, DEBUG, ERROR, WARNING, CRITICAL, Formatter, LogRecord


def _stderr_supports_color(
    colors: Optional[Dict[int, int]]
) -> Optional[Tuple[Dict[int, str], str]]:
    # Colors can be forced with an env variable
    if colors is None or "NO_COLOR" in os.environ:
        return None

    if os.name == "nt":
        try:
            # Attempt to enable ANSI colors on windows
            # Internal
            from ctypes import windll  # type: ignore

            k = windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
        except Exception:
            return None

    # Detect color support of stderr with curses (Linux/macOS)
    if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
        try:
            # Internal
            import curses

            curses.setupterm()
            if curses.tigetnum("colors") > 0:
                fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or b""

                # Convert the terminal control characters from bytes to unicode strings for easier use with the logging
                # module.
                return {
                    levelno: str(curses.tparm(fg_color, code), "ascii")
                    for levelno, code in colors.items()
                }, str(curses.tigetstr("sgr0"), "ascii")
        except Exception:
            # If curses is not present (currently we'll only get here on windows),
            # assume hard-coded ANSI color codes.
            return {levelno: ("\033[2;3%dm" % code) for levelno, code in colors.items()}, "\033[0m"

    return None


def _safe_unicode(message: Optional[AnyStr]) -> str:
    if isinstance(message, bytes):
        try:
            return message.decode("utf-8")
        except UnicodeDecodeError:
            return repr(message)
    return message or ""


_DEVNULL = open(os.devnull, "w")
_DEFAULT_DISPATCH: Tuple[Callable[..., Any], ...] = (
    dict.__repr__,
    list.__repr__,
    tuple.__repr__,
    set.__repr__,
    frozenset.__repr__,
)


class ConsoleFormatter(Formatter):
    """
    Log formatter used in Tornado. Key features of this formatter are:
    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.
    """

    DEFAULT_FORMAT = (
        "%(color)s"
        + (
            "[%(name)s]-[%(levelname)s]-[%(asctime)s]\n"
            "From %(module)s.%(funcName)s at %(filename)s:%(lineno)d"
        )
        + "%(end_color)s"
        "\n%(message)s"
    )
    DEFAULT_COLORS = {
        DEBUG: 4,  # Blue
        INFO: 2,  # Green
        WARNING: 3,  # Yellow
        ERROR: 1,  # Red
        CRITICAL: 5,  # Magenta
    }
    DEFAULT_DATE_FORMAT = "%Y/%m/%d %H:%M:%S"

    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DEFAULT_DATE_FORMAT,
        style: Literal["%", "{", "$"] = "%",
        validate: bool = True,
        colors: Optional[Dict[int, int]] = DEFAULT_COLORS,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate)

        # Initialize pprinter instance
        self._pprinter = PrettyPrinter(width=80, stream=_DEVNULL, compact=True)
        self._pprinter_supported: Sequence[Any] = _DEFAULT_DISPATCH
        pprint_dispatch = getattr(
            self._pprinter, "_dispatch", None
        )  # _dispatch is cpython specifc
        if isinstance(pprint_dispatch, dict) and len(pprint_dispatch) > 0:
            self._pprinter_supported = tuple(pprint_dispatch.values())

        # Check for color support and initialize utility structures
        supports_color = _stderr_supports_color(colors)
        if supports_color is None:
            self._colors = None
            self._normal = ""
        else:
            self._colors, self._normal = supports_color

    def format(self, record: LogRecord) -> str:
        try:
            message = str(record.msg)
            if isinstance(record.args, tuple):
                message = message % tuple(
                    (
                        self._pprinter.pformat(arg)
                        if type(arg).__repr__ in self._pprinter_supported
                        else arg
                    )
                    for arg in record.args
                )
            elif record.args is not None:
                message = message % {
                    name: (
                        self._pprinter.pformat(arg)
                        if type(arg).__repr__ in self._pprinter_supported
                        else arg
                    )
                    for name, arg in record.args.items()
                }
            record.message = _safe_unicode(message)
        except Exception as exc:
            record.message = "Bad message"
            record.exc_info = (type(exc), exc, exc.__traceback__)

        record.asctime = self.formatTime(record, self.datefmt)

        color_info: Dict[str, str] = {}
        if self._colors and record.levelno in self._colors:
            color_info["color"] = self._colors[record.levelno]
            color_info["end_color"] = self._normal
        else:
            color_info["color"] = ""
            color_info["end_color"] = ""

        formatted = (self._fmt if self._fmt else type(self).DEFAULT_FORMAT) % {
            **record.__dict__,
            **color_info,
        }

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            # exc_text contains multiple lines.
            # We need to _safe_unicode each line separately so that non-utf8 bytes don't cause all the newlines to turn
            # into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(_safe_unicode(ln) for ln in record.exc_text.split("\n"))
            formatted = "\n".join(lines)

        return formatted.replace("\n", "\n    ")


__all__ = ("ConsoleFormatter",)
