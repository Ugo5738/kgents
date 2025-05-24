"""
Initialize and provide Supabase client for database operations.
"""

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache()
def _get_supabase_client() -> Client:
    """
    Get a cached Supabase client instance.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(supabase_url, supabase_key)


async def get_supabase_client() -> Client:
    """
    Async function to retrieve the Supabase client instance.
    """
    return _get_supabase_client() 