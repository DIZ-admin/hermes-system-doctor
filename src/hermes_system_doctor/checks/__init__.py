from .config import config_check
from .cron import cron_check
from .discovery import discover_home
from .profiles import profile_inventory_check

# Backward-compatible alias for the initial scaffold import name.
profile_config_check = config_check

__all__ = [
    "config_check",
    "cron_check",
    "discover_home",
    "profile_config_check",
    "profile_inventory_check",
]
