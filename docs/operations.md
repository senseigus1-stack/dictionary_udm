# Runbook администратора

## SLO и сигналы

Рекомендуемый стартовый SLO: 99,5% успешных API-запросов за месяц, p95 менее 500 мс для чтения и менее 1 с для записи ответа. Ключевые сигналы:

- `up` и `/health/ready`;
- частота HTTP 5xx и p95 latency из `/metrics`;
- число рестартов `api`, `bot`, `worker`;
- свободное место PVC PostgreSQL и backup PVC;
- возраст последнего успешного backup Job;
- ошибки Telegram 401/403/429 в логах worker и bot;
- число просроченных миграционных/import Jobs.

## Установка и обновление

Создайте Secret заранее (значения показаны только как имена ключей):

```bash
kubectl -n zechbur create secret generic zechbur-production \
  --from-literal=APP_SECRET='replace-with-48-random-chars' \
  --from-literal=TELEGRAM_BOT_TOKEN='replace-me' \
  --from-literal=TELEGRAM_BOT_SECRET='replace-with-independent-secret' \
  --from-literal=POSTGRES_PASSWORD='replace-me' \
  --from-literal=DATABASE_URL='postgresql+asyncpg://...' \
  --from-literal=REDIS_URL='redis://...'
```

Запуск:

```bash
helm upgrade --install zechbur deploy/helm -n zechbur --create-namespace \
  --atomic --timeout 20m \
  --set secrets.existingSecret=zechbur-production \
  --set image.tag=rc-2.0 \
  --set ingress.host=udmurt.example.org
```

Сначала создаются обычные ресурсы, затем post-install/post-upgrade Job применяет Alembic и идемпотентно импортирует словарь. Readiness API остаётся красным до появления словарных статей.

Проверка:

```bash
kubectl -n zechbur get pods,jobs
kubectl -n zechbur logs job/zechbur-zechbur-migrate-1
kubectl -n zechbur port-forward svc/zechbur-zechbur 8000:80
curl -fsS http://127.0.0.1:8000/health/ready
```

## Откат

Приложение откатывается `helm rollback`. Миграции написаны с `downgrade`, но автоматический downgrade при откате образа не выполняется: изменения схемы должны быть backward-compatible минимум один релиз.

```bash
helm -n zechbur history zechbur
helm -n zechbur rollback zechbur REVISION --wait --timeout 10m
```

Если релиз меняет схему несовместимо, сначала восстановите совместимую БД из проверенной копии в отдельный инстанс, затем переключите `DATABASE_URL`.

## Резервное копирование

Встроенный CronJob ежедневно создаёт custom-format `pg_dump` и хранит 14 дней на отдельном PVC. Это минимальная страховка, не полноценный disaster recovery. Для production копируйте дампы в versioned object storage или используйте managed PostgreSQL с PITR.

Проверяйте восстановление ежемесячно:

```bash
createdb zechbur_restore_test
pg_restore --clean --if-exists --no-owner --dbname=zechbur_restore_test zechbur-YYYYMMDD.dump
psql zechbur_restore_test -c 'select count(*) from dictionary_entries'
```

Цель по умолчанию: RPO 24 часа, RTO 2 часа. Managed PITR может снизить RPO до минут.

## Инциденты

### Readiness 503

1. Проверьте PostgreSQL и `DATABASE_URL`.
2. Посмотрите migration/import Jobs.
3. Если таблица пуста, повторите импорт одноразовым Job с командой `import`.
4. Не переводите readiness на `/health/live`: это пустит трафик в неготовый сервис.

### Bot не отвечает

1. Убедитесь, что bot Deployment имеет ровно одну реплику.
2. Проверьте `TELEGRAM_BOT_TOKEN`, исходящий TCP/443 и ответы 409 (второй poller).
3. После смены токена перезапустите bot и worker.

### База растёт

Главный растущий объект — `review_logs`. Сначала добавьте партиционирование по месяцу и политику холодного хранения; не удаляйте события без агрегирования retention/accuracy.

## Смена секретов

Смена `APP_SECRET` немедленно инвалидирует все JWT. Планируйте её как пользовательское событие повторного входа. `TELEGRAM_BOT_SECRET` можно менять с согласованным rolling restart API и bot. Пароль PostgreSQL меняйте сначала на сервере, затем в Secret и Deployment.
