"""
File: ./tghook/__init__.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from importlib.metadata import metadata

# Project
from ._bot_server import EXTERNAL_HOST_TYPE, start_server

try:
    _metadata = metadata(__name__)
    __author__: str = _metadata["Author"]
    __version__: str = _metadata["Version"]
    __summary__: str = _metadata["Summary"]
except Exception:  # pragma: no cover
    # Internal
    import traceback
    from warnings import warn

    warn(
        f"Failed to gather package {__name__} metadata, due to:\n{traceback.format_exc()}",
        ImportWarning,
    )

    __author__ = "unknown"
    __version__ = "0.0a0"
    __summary__ = ""

__all__ = ("__author__", "__version__", "__summary__", "start_server", "EXTERNAL_HOST_TYPE")
