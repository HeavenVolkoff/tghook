"""
File: ./tghook/logger/__init__.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from os import path, makedirs
from typing import Union, Optional
from logging import INFO, WARNING, Logger, StreamHandler, captureWarnings
from logging.handlers import RotatingFileHandler

# Project
from ._formatter import Formatter

_DEFAULT_LOG_PATH = "./logs"
_MAX_LOG_FILE_SIZE = (
    (1024 * 1024) if __debug__ else (10 * 1024 * 1024)
)  # 1MB for production and 10MB for debug
_MAX_LOG_FILE_COUNT = 10

# Setup root logger basic config
Logger.root.setLevel(INFO if __debug__ else WARNING)
_stderr_stream_handler = StreamHandler()
_stderr_stream_handler.setFormatter(Formatter())
Logger.root.addHandler(_stderr_stream_handler)

# Configure warning to be show using the logging infraestructure
captureWarnings(True)


def set_level(level: Union[str, int]) -> None:
    """Set global logger level.

    Arguments:
        level: Level to be used.

    """
    Logger.root.setLevel(level)


def get_logger(
    name: str,
    *,
    log_path: Optional[str] = _DEFAULT_LOG_PATH,
    file_size_limit: int = _MAX_LOG_FILE_SIZE,
    file_count_limit: int = _MAX_LOG_FILE_COUNT,
) -> Logger:
    """Retrieve a antenna logger.

    Arguments:
        name: Logger name.
        log_path: Path to logger file
        file_size_limit: Limit of logger file size.
        file_count_limit: Limit of existing logger file.

    """
    # Internal

    log = Logger.root.getChild(name)

    if log_path is not None:
        if not path.exists(log_path):
            makedirs(log_path)

        rfh = RotatingFileHandler(
            filename=path.join(log_path, f"{name}.log"),
            encoding="utf8",
            maxBytes=file_size_limit,
            backupCount=file_count_limit,
        )

        # TODO: Replace with a json formatter
        rfh.setFormatter(Formatter(colors=None))

        log.addHandler(rfh)

    # Ensure log is an antenna log
    assert isinstance(log, Logger)

    return log


__all__ = ("get_logger", "set_level")
