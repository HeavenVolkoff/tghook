"""
File: ./tghook/logger/_json_formatter.py
Author: Vítor Vasconcellos (vasconcellos.dev@gmail.com)
Project: tghook

Copyright © 2021-2021 Vítor Vasconcellos
This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
"""

# Internal
from logging import Formatter, LogRecord
from datetime import datetime

# External
import orjson


class JSONFormatter(Formatter):
    def format(self, record: LogRecord) -> str:
        return orjson.dumps(
            {
                "name": record.name,
                "lineno": record.lineno,
                "module": record.module,
                "thread": record.thread,
                "created": datetime.fromtimestamp(record.created),
                "process": record.process,
                "message": record.msg,
                "funcName": record.funcName,
                "pathname": record.pathname,
                "exc_info": (
                    self.formatException(record.exc_info) if record.exc_info else record.exc_text
                ),
                "arguments": record.args,
                "levelname": record.levelname,
                "stack_info": self.formatStack(record.stack_info) if record.stack_info else None,
                "threadName": record.threadName,
                "processName": record.processName,
            },
            default=repr,
            option=orjson.OPT_NON_STR_KEYS,
        ).decode("utf-8")


__all__ = ("JSONFormatter",)
