#!/usr/bin/env python3
"""
Permission and module check helpers for CFB League Bot

These functions are used by cogs to verify that:
1. The required module is enabled for the server
2. The channel is whitelisted (if whitelist exists)
3. The user has required permissions
"""

import logging
import discord
from typing import Optional

# Import will be done at module load time to avoid circular imports
# from ..utils.server_config import server_config, FeatureModule

logger = logging.getLogger('CFBBot.Checks')


async def check_module_enabled(
    interaction: discord.Interaction,
    module: 'FeatureModule',
    server_config: 'ServerConfig'
) -> bool:
    """
    Check if a module is enabled for this server and channel.
    
    Sends an ephemeral message if disabled.
    Use this for commands that respond immediately.
    
    Args:
        interaction: The Discord interaction
        module: The FeatureModule to check
        server_config: The server config manager instance
        
    Returns:
        True if module is enabled and channel is allowed, False otherwise
    """
    guild_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id if interaction.channel else 0
    
    # Check if module is enabled
    if not server_config.is_module_enabled(guild_id, module):
        module_name = module.value.replace('_', ' ').title()
        await interaction.response.send_message(
            f"❌ The **{module_name}** module is disabled on this server.\n"
            f"Ask an admin to enable it with `/admin config`",
            ephemeral=True
        )
        return False
    
    # Check if channel is whitelisted (if whitelist exists)
    enabled_channels = server_config.get_enabled_channels(guild_id)
    if enabled_channels and channel_id not in enabled_channels:
        await interaction.response.send_message(
            f"❌ Commands are not enabled in this channel.\n"
            f"Ask an admin to whitelist this channel with `/admin channels`",
            ephemeral=True
        )
        return False
    
    return True


async def check_module_enabled_deferred(
    interaction: discord.Interaction,
    module: 'FeatureModule',
    server_config: 'ServerConfig'
) -> bool:
    """
    Check if a module is enabled for this server and channel.
    
    Sends a followup message if disabled.
    Use this for commands that have already deferred their response.
    
    Args:
        interaction: The Discord interaction (already deferred)
        module: The FeatureModule to check
        server_config: The server config manager instance
        
    Returns:
        True if module is enabled and channel is allowed, False otherwise
    """
    guild_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id if interaction.channel else 0
    
    # Check if module is enabled
    if not server_config.is_module_enabled(guild_id, module):
        module_name = module.value.replace('_', ' ').title()
        await interaction.followup.send(
            f"❌ The **{module_name}** module is disabled on this server.\n"
            f"Ask an admin to enable it with `/admin config`",
            ephemeral=True
        )
        return False
    
    # Check if channel is whitelisted (if whitelist exists)
    enabled_channels = server_config.get_enabled_channels(guild_id)
    if enabled_channels and channel_id not in enabled_channels:
        await interaction.followup.send(
            f"❌ Commands are not enabled in this channel.\n"
            f"Ask an admin to whitelist this channel with `/admin channels`",
            ephemeral=True
        )
        return False
    
    return True


def is_bot_admin(
    user: discord.User,
    guild_id: int,
    server_config: 'ServerConfig'
) -> bool:
    """
    Check if a user is a bot admin for the server.
    
    Args:
        user: The Discord user to check
        guild_id: The guild ID
        server_config: The server config manager instance
        
    Returns:
        True if user is a bot admin
    """
    admins = server_config.get_bot_admins(guild_id)
    return user.id in admins


def is_server_admin(member: discord.Member) -> bool:
    """
    Check if a member has Discord server admin permissions.
    
    Args:
        member: The Discord member to check
        
    Returns:
        True if member has administrator permission
    """
    return member.guild_permissions.administrator

