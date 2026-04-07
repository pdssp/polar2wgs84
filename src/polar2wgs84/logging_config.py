# Polar to WGS84 Converter - Global geometry processing utilities for GeoJSON-safe WGS84 polygons.
# Copyright (C) 2026 - CNES (Jean-Christophe Malapert for PDSSP)
"""
Logging configuration — loguru
================================
Centralises all logging setup for the ODE STAC Proxy.

Two log streams are produced:

operational
    Human-readable logs for diagnosing runtime problems.
    Includes request tracing, ODE errors, cache events and slow-query alerts.
    Structured as JSON when writing to a file so that tools such as
    ``jq``, Loki, or Elastic can ingest them without a parser.

statistics (``stats``)
    Machine-readable JSON lines written to a dedicated sink.
    Every record carries a ``log_type`` field set to ``"stat"`` so that
    it can be filtered trivially.  The goal is to answer questions like:
    - Which collections are queried most often?
    - What is the p95 response latency?
    - What is the cache hit ratio?
    - How many ODE errors per hour?

Usage
-----
Import the module-level helpers at the top of any module::

    from .logging_config import get_logger, log_stat

    logger = get_logger(__name__)
    logger.info("server started on port={port}", port=8000)

    log_stat("search", collection="mars-mro-hirise-rdrv11",
             duration_ms=142, cache_hit=True, n_items=10)

The ``log_stat`` call emits a single JSON-line record to the stats sink
(and also to the operational sink at DEBUG level).

Configuration
-------------
Call :func:`setup_logging` once at startup (from ``__init__.py`` / CLI)::

    from .logging_config import setup_logging
    setup_logging(
        log_level="INFO",
        log_file="logs/proxy.log",
        stats_file="logs/stats.jsonl",
        rotation="50 MB",
        retention="30 days",
    )
"""
import json
import sys
from datetime import datetime
from datetime import UTC
from pathlib import Path

from loguru import logger

# ---------------------------------------------------------------------------
# Module-level sentinel — avoid double-initialisation in unit tests
# ---------------------------------------------------------------------------
_configured = False


def setup_logging(
    log_level: str = "INFO",
    log_file: str | None = None,
    stats_file: str | None = None,
    rotation: str = "50 MB",
    retention: str = "30 days",
    json_console: bool = False,
) -> None:
    """
    Configure loguru sinks for operational and statistical logging.

    Should be called **once** at application startup before any other module
    emits log records.  Calling it a second time is a no-op (guarded by a
    module-level flag so that test imports do not reset handlers).

    Parameters
    ----------
    log_level:
        Minimum severity for the operational log (console + file).
        One of ``"TRACE"``, ``"DEBUG"``, ``"INFO"``, ``"WARNING"``,
        ``"ERROR"``, ``"CRITICAL"``.
    log_file:
        Path to the rotating operational log file.
        ``None`` → file sink is disabled (console only).
    stats_file:
        Path to the append-only statistics JSONL file.
        ``None`` → stats are emitted to the console at DEBUG level only.
    rotation:
        Loguru rotation trigger for ``log_file`` (e.g. ``"50 MB"``,
        ``"1 day"``).
    retention:
        Loguru retention policy for ``log_file`` (e.g. ``"30 days"``).
    json_console:
        When ``True``, the console sink emits JSON instead of coloured text.
        Useful when running inside a container / log aggregator.
    """
    global _configured
    if _configured:
        return
    _configured = True

    # Remove the default loguru handler added at import time
    logger.remove()

    # ------------------------------------------------------------------
    # Console sink — operational logs
    # ------------------------------------------------------------------
    if json_console:
        logger.add(
            sys.stdout,
            level=log_level,
            format=_json_formatter,
            colorize=False,
            filter=_not_stat,
        )
    else:
        logger.add(
            sys.stdout,
            level=log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[module]}</cyan> | "
                "{message}"
            ),
            colorize=True,
            filter=_not_stat,
        )

    # ------------------------------------------------------------------
    # File sink — operational logs (JSON, rotating)
    # ------------------------------------------------------------------
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=log_level,
            format=_json_formatter,
            rotation=rotation,
            retention=retention,
            compression="gz",
            encoding="utf-8",
            filter=_not_stat,
        )

    # ------------------------------------------------------------------
    # Stats sink — machine-readable JSONL, append-only
    # ------------------------------------------------------------------
    if stats_file:
        Path(stats_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            stats_file,
            level="DEBUG",
            format="{message}",  # message IS the full JSON line
            rotation=rotation,
            retention=retention,
            compression="gz",
            encoding="utf-8",
            filter=_only_stat,
        )

    logger.info(
        "Logging initialised | level={level} | log_file={log_file} | stats_file={stats_file}",
        level=log_level,
        log_file=log_file or "none",
        stats_file=stats_file or "none",
        module="logging_config",
    )


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_logger(name: str):
    """
    Return a loguru logger bound with the caller's module name.

    The ``module`` extra is injected into every record emitted through the
    returned logger so that the console format can display it.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module.

    Returns
    -------
    loguru.Logger
        A context-bound loguru logger.

    Example
    -------
    ::

        from .logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("collection loaded | id={id} n={n}", id="mars-mro-hirise", n=42)
    """
    return logger.bind(module=name)


def log_stat(event: str, **fields) -> None:
    """
    Emit a structured statistics record.

    The record is written to the stats sink as a single JSON line.
    It is also emitted to the operational console at ``DEBUG`` level
    (filtered out by default unless ``log_level=DEBUG`` is set).

    Parameters
    ----------
    event:
        Short identifier for the measured event, e.g. ``"search"``,
        ``"cache_hit"``, ``"ode_error"``, ``"startup"``.
    **fields:
        Arbitrary key/value pairs to include in the JSON record.
        Common fields:

        - ``collection`` — STAC collection ID
        - ``duration_ms`` — elapsed time in milliseconds (``float``)
        - ``cache_hit`` — whether the response came from cache (``bool``)
        - ``n_items`` — number of items returned
        - ``status_code`` — HTTP status code
        - ``error`` — error message or exception class name

    Example
    -------
    ::

        log_stat("search",
                 collection="mars-mro-hirise-rdrv11",
                 bbox="-138.5,-5.5,-137.5,-4.5",
                 duration_ms=142.3,
                 cache_hit=False,
                 n_items=10)
    """
    record = {
        "log_type": "stat",
        "event": event,
        "ts": datetime.now(UTC).isoformat(),
        **fields,
    }
    json_line = json.dumps(record, default=str)
    # Route to the stats sink via the "stat" extra flag
    logger.bind(stat=True, module="stats").debug(json_line)


# ---------------------------------------------------------------------------
# Loguru filter helpers
# ---------------------------------------------------------------------------


def _not_stat(record: dict) -> bool:
    """Keep only non-stat records (operational sink filter)."""
    return not record["extra"].get("stat", False)


def _only_stat(record: dict) -> bool:
    """Keep only stat records (statistics sink filter)."""
    return record["extra"].get("stat", False)


# ---------------------------------------------------------------------------
# JSON formatter for file / JSON-console sinks
# ---------------------------------------------------------------------------


def _json_formatter(record: dict) -> str:
    """
    Serialise a loguru record as a single JSON line.

    The output is a compact JSON object followed by a newline, suitable
    for ingestion by Loki, Elastic, or any JSONL-aware tool.
    """
    payload = {
        "ts": record["time"].isoformat(),
        "level": record["level"].name,
        "module": record["extra"].get("module", record["name"]),
        "msg": record["message"],
    }
    # Include any extra fields the caller injected via logger.bind(…)
    for k, v in record["extra"].items():
        if k not in ("module", "stat"):
            payload[k] = v
    if record["exception"]:
        payload["exc"] = str(record["exception"])
    # Loguru applies str.format_map() on the string returned by a callable
    # formatter, so any { } in the JSON output would be misinterpreted as
    # format tokens.  Doubling them escapes them safely.
    serialised = json.dumps(payload, default=str)
    return serialised.replace("{", "{{").replace("}", "}}") + "\n"
