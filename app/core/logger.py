import asyncio
import json
import sys
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import wraps
from typing import Any

from loguru import logger as loguru_logger

from app.config import Environment, settings


class ConsoleLogger:
    def __init__(self, service_name: str, environment: str = "", include_extra: bool = True) -> None:
        self.service_name = service_name
        self.environment = environment
        self.include_extra = include_extra

    def sink(self, message) -> None:
        record = message.record
        doc = {
            "@timestamp": datetime.now(UTC).isoformat(),
            "service": self.service_name,
            "environment": self.environment,
            "level": record["level"].name,
            "level_value": record["level"].no,
            "logger": record["name"],
            "message": record["message"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "file": record["file"].path,
            "thread": {"name": record["thread"].name, "id": record["thread"].id},
            "process": {"name": record["process"].name, "id": record["process"].id},
            "time": record["time"].isoformat(),
        }

        exc = record.get("exception")
        if exc and (exc.type or exc.value):
            doc["exception"] = {
                "type": exc.type.__name__ if exc.type else None,
                "value": str(exc.value) if exc.value else None,
                "traceback": exc.traceback or None,
            }

        if self.include_extra:
            extra = record.get("extra")
            if extra:
                doc["extra"] = extra

        print(json.dumps(doc, ensure_ascii=False))


class DevConsoleLogger:
    FORMAT = (
        "<dim>[{extra[service]}/{extra[environment]}]</dim> "
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>\n{exception}"
    )
    _DIM = "\033[2m"
    _RESET = "\033[22m"

    @staticmethod
    def _flatten_extra(extra: dict) -> dict[str, Any]:
        skip = {"service", "environment"}
        flattened: dict[str, Any] = {}
        for key, value in extra.items():
            if key in skip:
                continue
            if key == "extra" and isinstance(value, dict):
                flattened.update(value)
            else:
                flattened[key] = value
        return flattened

    @staticmethod
    def _format_extra_value(value: Any) -> str:
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return repr(value)

    def _format_extras(self, extra: dict) -> str:
        flattened = self._flatten_extra(extra)
        if not flattened:
            return ""

        parts = [f"{key}={self._format_extra_value(value)}" for key, value in flattened.items()]
        return f" {self._DIM}| {' '.join(parts)}{self._RESET}"

    def sink(self, message) -> None:
        record = message.record
        extra_suffix = self._format_extras(record.get("extra") or {})
        text = str(message)

        if extra_suffix:
            main_line, _, rest = text.partition("\n")
            sys.stderr.write(f"{main_line.rstrip()}{extra_suffix}\n")
            if rest:
                sys.stderr.write(rest if rest.endswith("\n") else f"{rest}\n")
            return

        sys.stderr.write(text if text.endswith("\n") else f"{text}\n")


@asynccontextmanager
async def async_timer(
    process_name: str, logger_instance=None, log_start: bool = False, extra_data: dict[str, Any] | None = None
):
    _logger = logger_instance or logger
    _extra = extra_data or {}

    start_time = time.perf_counter()

    if log_start:
        _logger.info(f"Starting: {process_name}", **_extra)

    try:
        yield
    except Exception as e:
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        error_message = str(e).replace("{", "{{").replace("}", "}}")

        _logger.error(
            f"{process_name} failed after {execution_time:.3f} sec: {error_message}",
            execution_time=execution_time,
            process_name=process_name,
            error_type=type(e).__name__,
            **_extra,
        )
        raise
    else:
        end_time = time.perf_counter()
        execution_time = end_time - start_time

        _logger.info(
            f"{process_name} completed in {execution_time:.3f} sec",
            execution_time=execution_time,
            process_name=process_name,
            **_extra,
        )


class AsyncTimer:
    def __init__(
        self, process_name: str, logger_instance=None, log_start: bool = False, extra_data: dict[str, Any] | None = None
    ):
        self.process_name = process_name
        self.logger = logger_instance or logger
        self.log_start = log_start
        self.extra_data = extra_data or {}
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.perf_counter()
        if self.log_start:
            self.logger.info(f"Starting: {self.process_name}", **self.extra_data)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        execution_time = end_time - self.start_time

        if exc_type:
            self.logger.error(
                f"{self.process_name} failed after {execution_time:.3f} sec: {str(exc_val)}",
                execution_time=execution_time,
                process_name=self.process_name,
                error_type=exc_type.__name__,
                **self.extra_data,
            )
        else:
            self.logger.info(
                f"{self.process_name} completed in {execution_time:.3f} sec",
                execution_time=execution_time,
                process_name=self.process_name,
                **self.extra_data,
            )


def log_async_execution_time(
    process_name: str | None = None, logger_instance=None, extra_data: dict[str, Any] | None = None
):
    def decorator(func):
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"Function {func.__name__} must be async")

        @wraps(func)
        async def wrapper(*args, **kwargs):
            _process_name = process_name or f"{func.__module__}.{func.__name__}"
            async with async_timer(_process_name, logger_instance, extra_data=extra_data):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def setup_logging(
    service_name: str,
    environment: str,
    level: str = "INFO",
    include_extra: bool = True,
    debug: bool = False,
):
    loguru_logger.remove()

    if debug:
        dev_logger = DevConsoleLogger()
        loguru_logger.add(
            dev_logger.sink,
            format=DevConsoleLogger.FORMAT,
            level="DEBUG",
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )
    else:
        console_logger = ConsoleLogger(
            service_name=service_name,
            environment=environment,
            include_extra=include_extra,
        )
        loguru_logger.add(
            console_logger.sink,
            format="{message}",
            level=level,
            backtrace=True,
            diagnose=True,
            enqueue=True,
        )

    return loguru_logger.bind(service=service_name, environment=environment)


logger = setup_logging(
    service_name=settings.APP_NAME,
    environment="dev" if settings.ENVIRONMENT == Environment.DEVELOPMENT else "prod",
    level="DEBUG" if settings.DEBUG else "INFO",
    include_extra=True,
    debug=settings.DEBUG,
)
