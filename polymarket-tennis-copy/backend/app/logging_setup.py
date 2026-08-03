"""Structured logging with request/job correlation IDs.

Secrets are scrubbed from every event before rendering so that webhook URLs and
tokens can never reach the log stream or the UI error panel.
"""

from __future__ import annotations

import logging
import re
import sys
from contextvars import ContextVar
from typing import Any

import structlog

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)

# Anything that looks like a credential gets replaced before rendering.
_SECRET_KEY_PATTERN = re.compile(
    r"(token|secret|password|webhook|api_key|apikey|authorization|bearer)",
    re.IGNORECASE,
)
_URL_TOKEN_PATTERN = re.compile(
    r"(https://(?:discord\.com|discordapp\.com)/api/webhooks/)\S+", re.IGNORECASE
)
_TELEGRAM_PATTERN = re.compile(r"(https://api\.telegram\.org/bot)[^/\s]+", re.IGNORECASE)

REDACTED = "***redacted***"


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        value = _URL_TOKEN_PATTERN.sub(r"\1" + REDACTED, value)
        value = _TELEGRAM_PATTERN.sub(r"\1" + REDACTED, value)
        return value
    if isinstance(value, dict):
        return {k: (REDACTED if _SECRET_KEY_PATTERN.search(k) else _scrub_value(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub_value(v) for v in value]
    return value


def _scrub_processor(
    _logger: Any, _name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    for key in list(event_dict.keys()):
        if _SECRET_KEY_PATTERN.search(key):
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _scrub_value(event_dict[key])
    return event_dict


def _correlation_processor(
    _logger: Any, _name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    rid = request_id_var.get()
    jid = job_id_var.get()
    if rid:
        event_dict.setdefault("request_id", rid)
    if jid:
        event_dict.setdefault("job_id", jid)
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Install the structlog pipeline. Idempotent."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )
    # Third-party loggers are noisy at DEBUG; keep them at WARNING.
    for noisy in ("httpx", "httpcore", "apscheduler.executors.default"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _correlation_processor,
            _scrub_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_request_id(request_id: str) -> None:
    """Attach a request id to every log event on this task."""
    request_id_var.set(request_id)


def bind_job_id(job_id: str) -> None:
    """Attach a job id to every log event on this task."""
    job_id_var.set(job_id)
