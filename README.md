# Ӟечбур

Красивый, но не игрушечный MVP для ежедневного изучения удмуртского языка. Внутри — 44 637 словарных статей, интервальные повторения, 10 интерактивных уроков грамматики по очерку В. И. Алатырева, Telegram-бот и production-ready развёртывание в Kubernetes.

![Статус](https://img.shields.io/badge/release-2.0.0--rc.1-245c4d)
![Python](https://img.shields.io/badge/python-3.12-efad4d)
![FastAPI](https://img.shields.io/badge/API-FastAPI-173f35)

## Что уже работает

- веб-приложение без тяжёлой фронтенд-сборки: адаптивный маршрут, карточки, уроки и полный словарь;
- FastAPI API с JWT, гостевым режимом и проверкой подписи Telegram Web App;
- импорт исходного `udmurt_dictionary_full.json` с извлечением части речи, помет, краткого значения и примеров;
- интервальные повторения: «снова» через 7 минут, затем растущие интервалы с поправкой на лёгкость;
- приоритет просроченных карточек, затем базовая учебная лексика, затем остальной словарь;
- грамматическая траектория от пяти специальных букв до порядка слов и сложного предложения;
- Telegram-бот: `/learn`, `/grammar`, `/stats`, Web App и ежедневные напоминания;
- PostgreSQL, Redis/ARQ, Alembic, Prometheus-метрики и структурированные JSON-логи;
- Docker Compose и Helm: probes, HPA, PDB, CronJob резервных копий, миграционные Jobs и опциональный NetworkPolicy.

## Быстрый запуск

Нужны Docker Engine 24+ и Docker Compose v2.

```bash
cp .env.example .env
docker compose up --build
```

Первый запуск создаст схему и импортирует словарь. Интерфейс будет на `http://localhost:8000`, Swagger — на `http://localhost:8000/api/docs`, метрики — на `http://localhost:8000/metrics`.

Telegram локально включается отдельным профилем после заполнения `TELEGRAM_BOT_TOKEN`:

```bash
docker compose --profile telegram up --build
```

## Учебная логика

Словарная статья не сводится к паре «слово — перевод». При импорте сохраняются:

| Поле | Как используется |
|---|---|
| `word` | лицевая сторона карточки и полнотекстовый поиск |
| `definition` | полная статья без потери оттенков |
| `part_of_speech` | похожие отвлекающие ответы и фильтры |
| `labels` | пометы `диал.`, `бот.`, `разг.` и другие |
| `gloss` | короткий проверяемый ответ |
| `examples` | контекст после раскрытия карточки |
| `detail_url` | связь с исходной онлайн-статьёй |

Новый пользователь получает короткую базовую лексику. Затем планировщик всегда ставит сначала просроченные карточки. Ошибка возвращает слово через 7 минут; уверенный ответ увеличивает интервал до 1, 3, 4 и более дней. Это намеренно прозрачная SRS-модель: её коэффициенты находятся в `backend/app/services/srs.py` и легко калибруются по реальным данным.

Грамматика разбита на 10 ступеней по §§ 5–76 «Краткого грамматического очерка удмуртского языка» В. И. Алатырева (Ижевск, 1983): алфавит, множественное число, основные и пространственные падежи, притяжательность, числа и местоимения, глагол, отрицание, наклонения, нефинитные формы и синтаксис. Теория пересказана кратко; после каждого урока идут три проверяемых задания.

## Разработка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
make test
make lint
```

Полезные команды:

```bash
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend python -m app.cli import-dictionary udmurt_dictionary_full.json
PYTHONPATH=backend python -m app.cli stats
```

Структура проекта:

```text
backend/app/       API, модели, импорт, SRS и грамматический контент
backend/alembic/   версионируемая схема PostgreSQL
bot/               Telegram-бот на aiogram 3
web/               адаптивный HTML/CSS/JS клиент
deploy/helm/       Helm-чарт для production
docs/              архитектура и инструкция администратора
tests/             unit-тесты предметной логики
```

## Production

Соберите образ и передайте Helm-чарту тег, домен и Kubernetes Secret:

```bash
helm upgrade --install zechbur deploy/helm \
  --namespace zechbur --create-namespace \
  --set image.repository=ghcr.io/senseigus1-stack/dictionary_udm \
  --set image.tag=rc-2.0 \
  --set ingress.host=udmurt.example.org \
  --set bot.enabled=true \
  --set secrets.existingSecret=zechbur-production
```

Для серьёзной нагрузки рекомендуется управляемый PostgreSQL с PITR и управляемый Redis: установите `database.internal=false`, `redis.internal=false`, а `DATABASE_URL` и `REDIS_URL` положите в существующий Secret. Полный runbook — в [docs/operations.md](docs/operations.md), архитектурные решения — в [docs/architecture.md](docs/architecture.md).

## Данные и источники

Исходный словарь получен существующим PHP-парсером из `dict.fu-lab.ru`; исходные `detail_url` сохранены. Грамматический курс основан на предоставленном пользователем PDF В. И. Алатырева. PDF в репозиторий не копируется.

Перед публичным коммерческим запуском отдельно проверьте права на распространение словарной базы, грамматических примеров и название продукта: в исходном репозитории явная лицензия на данные не обнаружена.
