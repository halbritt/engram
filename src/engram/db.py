from __future__ import annotations

import os

import psycopg


DEFAULT_DATABASE_URL = "postgresql:///engram"


def database_url(env_var: str = "ENGRAM_DATABASE_URL") -> str:
    return os.environ.get(env_var, DEFAULT_DATABASE_URL)


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or database_url())
