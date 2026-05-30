# Деплой OgneTrade (ognetrade.online)

## Требования

- VPS с Docker и Docker Compose
- Домен **ognetrade.online** (и опционально **ognetrade.ru**) на Reg.ru
- AlphaSSL сертификат от Reg.ru

## 1. DNS

В Reg.ru создайте A-записи на IP сервера:

| Имя | Тип | Значение |
|-----|-----|----------|
| `@` (ognetrade.online) | A | IP сервера |
| `@` (ognetrade.ru) | A | IP сервера |
| `www` | A или CNAME | IP / ognetrade.ru |

## 2. SSL (AlphaSSL)

Следуйте инструкции в [deploy/ssl/README.md](deploy/ssl/README.md).

## 3. Переменные окружения

```bash
cp .env.production.example .env
nano .env
```

Обязательно задайте:

- `POSTGRES_PASSWORD`
- `SECRET_KEY` (64+ случайных символов)
- `IP_HASH_SALT`
- `CSRF_SECRET`

## 4. Запуск

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Проверка:

```bash
curl -I https://ognetrade.online/health
docker compose -f docker-compose.prod.yml exec app python test_smoke.py
```

## 5. Админка

- URL: `https://ognetrade.online/admin/login`
- Демо после seed: `admin@example.ru` / `admin12345` — **смените пароль в продакшене**

```bash
docker compose -f docker-compose.prod.yml exec app python -m app.cli create-admin \
  --email admin@ognetrade.ru --password 'YOUR_STRONG_PASSWORD' --name Admin
```

## 6. Обновление

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Архитектура

```
Internet → Nginx :443 (AlphaSSL) → FastAPI :8000 → PostgreSQL
```

- PostgreSQL **не** проброшен наружу
- `COOKIE_SECURE=true`, `ENVIRONMENT=production`
- HTTP автоматически редиректится на HTTPS

## Локальная разработка

```bash
docker compose up --build
```

Сайт: http://localhost:8000
