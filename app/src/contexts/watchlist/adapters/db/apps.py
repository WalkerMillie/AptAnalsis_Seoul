"""[HAND-WRITTEN] watchlist 영속 어댑터의 Django 앱 설정."""

from django.apps import AppConfig


class WatchlistDbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.watchlist.adapters.db"
    label = "watchlist_db"
