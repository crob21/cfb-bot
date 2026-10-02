#!/usr/bin/env python3
"""
Embed builder utilities for CFB League Bot

Provides consistent embed formatting across all cogs.
"""

import discord
from typing import Optional, List, Dict, Any

from ..config import Colors, Footers


class EmbedBuilder:
    """Factory class for creating consistent Discord embeds"""
    
    @staticmethod
    def success(
        title: str,
        description: str = "",
        footer: Optional[str] = None
    ) -> discord.Embed:
        """Create a success (green) embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=Colors.SUCCESS
        )
        if footer:
            embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def error(
        title: str,
        description: str = "",
        footer: Optional[str] = None
    ) -> discord.Embed:
        """Create an error (red) embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=Colors.ERROR
        )
        if footer:
            embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def warning(
        title: str,
        description: str = "",
        footer: Optional[str] = None
    ) -> discord.Embed:
        """Create a warning (orange) embed"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=Colors.WARNING
        )
        if footer:
            embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def info(
        title: str,
        description: str = "",
        footer: Optional[str] = None,
        color: int = Colors.PRIMARY
    ) -> discord.Embed:
        """Create an info (blue) embed"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        if footer:
            embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def player(
        name: str,
        description: str,
        thumbnail_url: Optional[str] = None,
        footer: str = Footers.PLAYER_LOOKUP
    ) -> discord.Embed:
        """Create a player lookup embed"""
        embed = discord.Embed(
            title=f"🏈 {name}",
            description=description,
            color=Colors.PRIMARY
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def recruit(
        name: str,
        description: str,
        stars: int = 0,
        thumbnail_url: Optional[str] = None,
        is_transfer: bool = False
    ) -> discord.Embed:
        """Create a recruiting embed"""
        star_str = "⭐" * stars if stars else ""
        title = f"{star_str} {name}" if star_str else f"⭐ {name}"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=Colors.RECRUITING
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        
        footer = Footers.PORTAL if is_transfer else Footers.RECRUITING
        embed.set_footer(text=footer)
        return embed
    
    @staticmethod
    def hs_stats(
        name: str,
        description: str,
        school: Optional[str] = None
    ) -> discord.Embed:
        """Create a high school stats embed"""
        title = f"🏫 {name}"
        if school:
            title += f" ({school})"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=Colors.HS_STATS
        )
        embed.set_footer(text=Footers.HS_STATS)
        return embed
    
    @staticmethod
    def config(
        title: str,
        description: str = ""
    ) -> discord.Embed:
        """Create a config/admin embed"""
        embed = discord.Embed(
            title=f"⚙️ {title}",
            description=description,
            color=Colors.ADMIN
        )
        embed.set_footer(text=Footers.CONFIG)
        return embed


def paginate_embed(
    items: List[Any],
    page: int,
    per_page: int,
    format_func,
    title: str,
    color: int = Colors.PRIMARY
) -> discord.Embed:
    """
    Create a paginated embed for lists of items.
    
    Args:
        items: List of items to paginate
        page: Current page (1-indexed)
        per_page: Items per page
        format_func: Function to format each item
        title: Embed title
        color: Embed color
        
    Returns:
        Formatted embed for the current page
    """
    total_pages = (len(items) + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_items = items[start_idx:end_idx]
    
    description = "\n".join(format_func(item) for item in page_items)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text=f"Page {page}/{total_pages} • {len(items)} total")
    
    return embed

