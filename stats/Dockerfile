# ---------- Stage 1: Build ----------
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-compile -r requirements.txt && \
    /opt/venv/bin/pip uninstall -y pip setuptools

# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim

# Sicherheitsupdates des Basis-Images einspielen (siehe notely-Dockerfile).
# Cache-Anker: Datum anheben, um die apt-Schicht bewusst neu zu bauen —
# ein gecachtes "apt-get upgrade" schützt nur so frisch, wie sein Layer alt ist.
ARG APT_REFRESH=2026-08-26
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
