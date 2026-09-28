"""The log: what ModStaller does, live and in a file.

Built on ``logging`` so that warnings from pymobiledevice3 & co. end up here
too. Every entry belongs to an *area* (install, JIT, device, account, ...),
which the interface filters by.

* :class:`Logbook` keeps the latest entries in memory and passes each new
  one on to listeners - that is how it reaches the interface live.
* :func:`setup` attaches the logbook and a rotating file to the root
  logger. CLI and interface write to the same file, so an unattended
  refresh stays traceable too.

Passwords, tokens and anisette headers never belong here. The code does not
log them, and libraries only get through from WARNING up - their DEBUG noise
might otherwise contain headers.
"""

from __future__ import annotations

import itertools
import logging
import logging.handlers
import re
import textwrap
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Callable

#: Between INFO (20) and WARNING (30): something succeeded.
SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")

INSTALL, REFRESH, JIT, APPS, DEVICE, ACCOUNT, SYSTEM = (
    "install", "refresh", "jit", "apps", "device", "account", "system")

#: Which logger maps to which area when the entry doesn't say.
_SOURCE_BY_LOGGER = (
    ("pymobiledevice3", DEVICE),
    ("modstaller.device", DEVICE),
    ("anisette", ACCOUNT),
    ("modstaller.apple", ACCOUNT),
)

_LEVELS = {logging.DEBUG: "debug", logging.INFO: "info", SUCCESS: "success",
           logging.WARNING: "warn", logging.ERROR: "error",
           logging.CRITICAL: "error"}

#: This many entries stay in memory for "history".
KEEP = 1000

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(source)s] %(message)s"


@dataclass(frozen=True)
class Entry:
    id: int
    ts: float
    level: str          # debug | info | success | warn | error
    source: str
    message: str
    job: object = None  # ID of the request it belongs to

    def as_dict(self) -> dict:
        return asdict(self)


def _source_of(record: logging.LogRecord) -> str:
    source = getattr(record, "source", None)
    if source:
        return source
    name = record.name or ""
    for prefix, src in _SOURCE_BY_LOGGER:
        if name == prefix or name.startswith(prefix + "."):
            return src
    return SYSTEM


class _FileFormatter(logging.Formatter):
    """One line per entry in the file - continuation lines are indented
    under the message, so the file stays greppable by date."""

    def format(self, record: logging.LogRecord) -> str:
        head = super().format(record)
        first, _, rest = head.partition("\n")
        if not rest:
            return head
        pad = " " * (len(first) - len(record.getMessage().partition("\n")[0]))
        return first + "".join(f"\n{pad}{line}" for line in rest.split("\n"))


class _SourceFilter(logging.Filter):
    """Makes sure every record has ``source`` (for the file format)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.source = _source_of(record)
        return True


class Logbook(logging.Handler):
    def __init__(self, keep: int = KEEP) -> None:
        super().__init__(level=logging.DEBUG)
        self._entries: deque[Entry] = deque(maxlen=keep)
        self._listeners: list[Callable[[Entry], None]] = []
        self._ids = itertools.count(1)
        self._guard = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        entry = Entry(
            id=next(self._ids), ts=record.created,
            level=_LEVELS.get(record.levelno, "info"),
            source=_source_of(record), message=message,
            job=getattr(record, "job", None))
        with self._guard:
            self._entries.append(entry)
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(entry)
            except Exception:
                pass  # a broken listener must not stop the log

    def history(self, limit: int | None = None) -> list[Entry]:
        with self._guard:
            entries = list(self._entries)
        return entries[-limit:] if limit else entries

    def subscribe(self, listener: Callable[[Entry], None]) -> Callable[[], None]:
        with self._guard:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._guard:
                if listener in self._listeners:
                    self._listeners.remove(listener)
        return unsubscribe


#: This process's logbook.
BOOK = Logbook()

_log = logging.getLogger("modstaller.events")


#: "=== Renewing X ===" - a heading for the terminal, noise in the log.
_BANNER = re.compile(r"^=+\s*(.*?)\s*=+$")


def tidy(message: str) -> str:
    """Terminal output made fit for the log.

    The pipeline writes for a terminal: blank lines as separators, indented
    detail lines, ``===`` banners. In the log every step is one entry, so
    that goes: blank lines out, the block dedented as a whole (a table
    keeps its columns), banners reduced to their text.
    """
    lines = [line.rstrip() for line in str(message).splitlines()]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return ""
    text = textwrap.dedent("\n".join(lines))
    first, _, rest = text.partition("\n")
    banner = _BANNER.match(first.strip())
    if banner:
        first = banner.group(1)
    return f"{first}\n{rest}" if rest else first


def log(source: str, message: str, level: int = logging.INFO,
        job: object = None) -> None:
    """An event for the log. A step that spans several lines (a table, a
    heading with details) stays one entry."""
    text = tidy(message)
    if text:
        _log.log(level, text, extra={"source": source, "job": job})


def mask_apple_id(apple_id: str) -> str:
    """``santino@example.de`` -> ``sa***@example.de`` - recognizable, not readable."""
    name, at, domain = apple_id.partition("@")
    return f"{name[:2]}***{at}{domain}" if at else f"{apple_id[:2]}***"


_configured = False


def setup(*, file=None, book: Logbook | None = BOOK,
          echo: bool = False) -> None:
    """Attaches the logbook and (optionally) a file to the root logger. Idempotent.

    ``echo`` also prints warnings and errors to stderr - for the CLI, which
    would otherwise lose them to the file once a handler exists.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Our own messages from INFO, third-party libraries only from WARNING.
    logging.getLogger("modstaller").setLevel(logging.INFO)
    for noisy in ("pymobiledevice3", "anisette", "urllib3", "asyncio",
                  "requests", "unicorn"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    if book is not None:
        root.addHandler(book)
    if file is not None:
        try:
            file.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                file, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        except OSError:
            handler = None  # not writable: the live log still works
        if handler is not None:
            handler.addFilter(_SourceFilter())
            handler.setFormatter(_FileFormatter(LOG_FORMAT))
            root.addHandler(handler)
    if echo:
        stderr = logging.StreamHandler()
        stderr.setLevel(logging.WARNING)
        stderr.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        root.addHandler(stderr)


def elapsed(started: float) -> str:
    s = time.monotonic() - started
    return f"{s:.1f} s" if s < 60 else f"{int(s // 60)} min {int(s % 60)} s"
