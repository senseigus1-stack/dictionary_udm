#!/bin/sh
set -eu

case "${1:-api}" in
  api)
    if [ "${AUTO_MIGRATE:-false}" = "true" ]; then
      alembic -c /app/backend/alembic.ini upgrade head
    fi
    if [ "${AUTO_IMPORT_DICTIONARY:-false}" = "true" ]; then
      python -m app.cli import-dictionary "${DICTIONARY_PATH:-/app/data/udmurt_dictionary_full.json}"
    fi
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
    ;;
  bot)
    exec python -m bot.main
    ;;
  worker)
    exec arq app.worker.WorkerSettings
    ;;
  migrate)
    exec alembic -c /app/backend/alembic.ini upgrade head
    ;;
  import)
    exec python -m app.cli import-dictionary "${DICTIONARY_PATH:-/app/data/udmurt_dictionary_full.json}"
    ;;
  *)
    exec "$@"
    ;;
esac
