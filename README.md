# Lids — сайт лидогенерации по огнетушителям

FastAPI-приложение: публичный лендинг с карточками товаров и формой заявки, админка с Kanban-сделками, аналитикой, редактором виджетов (GridStack) и уведомлениями Email/Telegram.

## Запуск в Docker (рекомендуется)

Требуется [Docker Desktop](https://www.docker.com/products/docker-desktop/) или Docker Engine + Compose.

```bash
docker compose up --build
```

После запуска:
- **Сайт:** http://localhost:8000/
- **Админка:** http://localhost:8000/admin/login
- **Health:** http://localhost:8000/health

Остановка:

```bash
docker compose down
```

Полная очистка с базой данных:

```bash
docker compose down -v
```

### Учётные записи (создаются автоматически при первом запуске)

| Роль | Email | Пароль |
|------|-------|--------|
| Администратор | admin@example.ru | admin12345 |
| Менеджер | manager@example.ru | manager12345 |

## Локальная разработка (без Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.cli seed
uvicorn app.main:app --reload
```

По умолчанию используется SQLite (`lids.db`). Для PostgreSQL укажите `DATABASE_URL` в `.env`.

## Возможности

### Публичный сайт
- Контакты в шапке (редактируются в админке)
- Карточки огнетушителей с трекингом кликов
- Форма заявки с автозаполнением товара
- Трекинг посещений

### Админка
- **Dashboard** — KPI и топ карточек
- **Kanban** — «Новые / В работе / Выполнено», drag-and-drop, комментарии, суммы, назначение менеджера
- **Клиенты** — таблица с фильтрами
- **Аналитика** — графики посещений, кликов, воронка
- **Виджеты** — GridStack редактор главной страницы
- **Пользователи** — создание менеджеров (super_admin)
- **Настройки** — контакты, SMTP, Telegram

## Docker-архитектура

```
docker-compose.yml
├── db (PostgreSQL 16) — healthcheck, volume pgdata
└── app (FastAPI)      — ждёт БД, seed, uvicorn :8000
```

Переменные окружения задаются в `docker-compose.yml`. Для production смените `SECRET_KEY`, `IP_HASH_SALT`, `CSRF_SECRET`.

## Безопасность

- JWT в httpOnly cookies + CSRF-токены
- Rate limit: форма 5/10 мин, логин 5/мин
- CSP и security headers
- IP хешируется перед записью в аналитику
- Пароли — bcrypt

## CLI

```bash
# внутри контейнера
docker compose exec app python -m app.cli create-admin --email you@example.ru --password secret123 --name "Your Name"
docker compose exec app python -m app.cli seed
```

## Переменные окружения

См. [.env.example](.env.example).
