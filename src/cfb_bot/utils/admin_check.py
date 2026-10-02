#!/usr/bin/env python3
"""
Admin Management for CFB League Bot
Handles admin permission checks
"""

import os
import logging
from typing import Set
import discord

logger = logging.getLogger('CFBBot.Admin')

class AdminManager:
    """Manages bot admin permissions"""

    def __init__(self):
        self.admin_ids: Set[int] = set()
        self._load_admins()

    def _load_admins(self):
        """Load admin IDs from environment variable or config"""
        # Load from environment variable (comma-separated list of user IDs)
        admin_env = os.getenv('BOT_ADMIN_IDS', '')

        if admin_env:
            try:
                admin_list = [int(uid.strip()) for uid in admin_env.split(',') if uid.strip()]
                self.admin_ids.update(admin_list)
                logger.info(f"Loaded {len(admin_list)} admin(s) from BOT_ADMIN_IDS")
            except ValueError as e:
                logger.error(f"Error parsing BOT_ADMIN_IDS: {e}")

        # Hardcoded fallback admins (you can add your user ID here!)
        # To find your user ID: Enable Developer Mode in Discord → Right-click your name → Copy User ID
        HARDCODED_ADMINS = [
            357591392358236161,  # Craig - Main Admin
            # Add more admins below as needed
        ]

        if HARDCODED_ADMINS:
            self.admin_ids.update(HARDCODED_ADMINS)
            logger.info(f"Loaded {len(HARDCODED_ADMINS)} hardcoded admin(s)")

        if not self.admin_ids:
            logger.warning("No bot admins configured! Admin commands will require Discord Administrator permission.")

    def add_admin(self, user_id: int) -> bool:
        """Add a user as bot admin"""
        if user_id in self.admin_ids:
            return False
        self.admin_ids.add(user_id)
        logger.info(f"Added admin: {user_id}")
        return True

    def remove_admin(self, user_id: int) -> bool:
        """Remove a user as bot admin"""
        if user_id not in self.admin_ids:
            return False
        self.admin_ids.remove(user_id)
        logger.info(f"Removed admin: {user_id}")
        return True

    def is_admin(self, user: discord.User, interaction: discord.Interaction = None) -> bool:
        """
        Check if a user is a bot admin

        Args:
            user: The Discord user to check
            interaction: Optional interaction to also check Discord permissions

        Returns:
            True if user is admin, False otherwise
        """
        # Check if user is in bot admin list
        if user.id in self.admin_ids:
            return True

        # Fallback: Check Discord Administrator permission if interaction provided
        if interaction and hasattr(interaction.user, 'guild_permissions'):
            if interaction.user.guild_permissions.administrator:
                return True

        return False

    def get_admin_list(self) -> list:
        """Get list of admin user IDs"""
        return list(self.admin_ids)

    def get_admin_count(self) -> int:
        """Get number of configured admins"""
        return len(self.admin_ids)
