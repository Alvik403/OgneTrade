# Положите сюда сертификат AlphaSSL от Reg.ru

1. В панели Reg.ru скачайте сертификат для **ognetrade.online** в формате **Nginx** (или Apache + ключ).
2. Скопируйте на сервер в эту папку два файла:

| Файл на сервере | Что положить |
|-----------------|--------------|
| `fullchain.pem` | Сертификат + промежуточные (chain), обычно `certificate.crt` + `ca-bundle.crt` склеенные |
| `private.key`   | Приватный ключ, выданный при активации AlphaSSL |

Пример склейки chain на сервере:

```bash
cat certificate.crt ca-bundle.crt > deploy/ssl/fullchain.pem
cp your_private.key deploy/ssl/private.key
chmod 600 deploy/ssl/private.key
```

3. Убедитесь, что DNS доменов указывает на IP сервера:
   - `ognetrade.online` → A-запись
   - `ognetrade.ru` → A-запись (если используете)
   - `www.ognetrade.ru` → A или CNAME

4. Запуск:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Nginx слушает **443** (HTTPS) и перенаправляет **80 → HTTPS**.

**Важно:** не коммитьте `private.key` в git — папка уже в `.gitignore`.
