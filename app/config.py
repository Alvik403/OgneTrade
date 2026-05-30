from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Огнетушители"
    secret_key: str = "change-me"
    debug: bool = True
    environment: str = "development"

    database_url: str = "sqlite:///./lids.db"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    ip_hash_salt: str = "ip-salt"
    csrf_secret: str = "csrf-secret"
    admin_path_prefix: str = "/admin"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    cookie_secure: bool = False
    site_url: str = "https://ognetrade.online"
    allowed_hosts: str = "ognetrade.online,ognetrade.ru,www.ognetrade.ru,localhost,127.0.0.1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
