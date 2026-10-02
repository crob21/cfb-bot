"""
Services module for CFB League Bot

Contains shared utilities used across cogs:
- checks.py: Permission and module checks
- embeds.py: Embed builders
"""

from .checks import (
    check_module_enabled,
    check_module_enabled_deferred,
    is_bot_admin,
    is_server_admin,
)

from .embeds import (
    EmbedBuilder,
    paginate_embed,
)

__all__ = [
    'check_module_enabled',
    'check_module_enabled_deferred',
    'is_bot_admin',
    'is_server_admin',
    'EmbedBuilder',
    'paginate_embed',
]

