# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_RETRIES=8

WORKDIR /build
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY bot ./bot
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
    && /opt/venv/bin/pip install .

FROM python:3.12-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/backend \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app backend ./backend
COPY --chown=app:app bot ./bot
COPY --chown=app:app web ./web
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app udmurt_dictionary_full.json ./data/udmurt_dictionary_full.json
RUN chmod +x /app/scripts/entrypoint.sh

USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["api"]
