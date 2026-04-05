"""
Supabase client singleton for backend operations.

Uses service_role key if set, otherwise falls back to anon key
(RLS is relaxed for rules/documents tables).
"""
from __future__ import annotations

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase() -> Client | None:
    """Return the Supabase client, or None if not configured."""
    settings = get_settings()
    if not settings.supabase_url:
        return None
    key = settings.supabase_service_role_key or settings.supabase_anon_key
    if not key:
        return None
    client = create_client(settings.supabase_url, key)
    logger.info("Supabase client ready: %s", settings.supabase_url)
    return client
