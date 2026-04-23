from core.config import settings


def get_api_key_header_name() -> str:
    return settings.API_KEY_HEADER_NAME
