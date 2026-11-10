"""
Connection configuration. Engine selects the backend (postgresql, mysql, oracle, sqlite).
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Database connection config. Common fields; backend may use a subset."""
    engine: str = "postgresql"
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = ""
    dbname: str = "postgres"
    # File / image field storage
    media_root: str = "media"
    media_url: str = "/media/"
    # Database alias (used for pool lookup in multi-db setups)
    alias: str = "default"

    @classmethod
    def from_env(cls, prefix: str = "DB_") -> "Config":
        return cls(
            engine=os.getenv(f"{prefix}ENGINE", "postgresql"),
            host=os.getenv(f"{prefix}HOST", "localhost"),
            port=int(os.getenv(f"{prefix}PORT", "5432")),
            user=os.getenv(f"{prefix}USER", "postgres"),
            password=os.getenv(f"{prefix}PASSWORD", ""),
            dbname=os.getenv(f"{prefix}NAME", "postgres"),
        )
