"""
Migrations: makemigrations (generate from models) and migrate (apply pending).
"""
from .makemigrations import makemigrations, makemigrations_per_app
from .runner import migrate, migrate_all_apps

__all__ = ["makemigrations", "makemigrations_per_app", "migrate", "migrate_all_apps"]
