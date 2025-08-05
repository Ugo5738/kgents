from functools import lru_cache

from ..config import Settings


@lru_cache()
def get_app_settings() -> Settings:
    """
    Returns the application settings, cached for efficiency.
    """
    return Settings()
