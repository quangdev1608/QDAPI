from core.config import settings


def get_database_url() -> str:
    return settings.DATABASE_URL
