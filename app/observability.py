"""JSON-Logging und Prometheus-Metriken."""

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter(
    "http_requests_total",
    "Anzahl HTTP-Anfragen",
    ["method", "path", "status"],
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "Dauer der HTTP-Anfragen in Sekunden",
    ["method", "path"],
)

logger = logging.getLogger("notely.access")


class JsonFormatter(logging.Formatter):
    """Schreibt jede Logzeile als ein JSON-Objekt."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # uvicorns eigener Zugriffslog wird abgeschaltet: unsere Middleware loggt jede
    # Anfrage bereits, und zwar als JSON. Sonst stünden zwei Formate nebeneinander.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False


async def observe_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    # Route-Vorlage statt echtem Pfad: "/notes/{note_id}", nicht "/notes/<uuid>".
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")

    REQUESTS.labels(request.method, path, str(response.status_code)).inc()
    LATENCY.labels(request.method, path).observe(duration)

    logger.info(
        "request",
        extra={
            "fields": {
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        },
    )
    return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)