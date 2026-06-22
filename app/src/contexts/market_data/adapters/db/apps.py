"""[HAND-WRITTEN] market_data 영속 어댑터의 Django 앱 설정."""

from django.apps import AppConfig


class MarketDataDbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.market_data.adapters.db"
    label = "market_data_db"
