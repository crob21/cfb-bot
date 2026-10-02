"""
Discord OAuth2 Authentication
"""

import os
import logging
from typing import Optional
import httpx

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse

logger = logging.getLogger('Dashboard.Auth')

auth_router = APIRouter()

# Discord OAuth2 settings
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:8080/auth/callback')

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# Scopes we need
SCOPES = ["identify", "guilds"]


def get_oauth_url(state: str) -> str:
    """Generate Discord OAuth2 authorization URL"""
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{DISCORD_AUTH_URL}?{query}"


async def exchange_code(code: str) -> Optional[dict]:
    """Exchange authorization code for access token"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                DISCORD_TOKEN_URL,
                data={
                    "client_id": DISCORD_CLIENT_ID,
                    "client_secret": DISCORD_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": DISCORD_REDIRECT_URI,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error exchanging code: {e}")
            return None


async def get_user_info(access_token: str) -> Optional[dict]:
    """Get user info from Discord API"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None


async def get_user_guilds(access_token: str) -> list:
    """Get guilds the user is in"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DISCORD_API_BASE}/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting guilds: {e}")
            return []


@auth_router.get("/login")
async def login(request: Request):
    """Redirect to Discord OAuth"""
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Discord OAuth not configured. Set DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET."
        )
    
    # Generate state for CSRF protection
    import secrets
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    return RedirectResponse(url=get_oauth_url(state))


@auth_router.get("/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle Discord OAuth callback"""
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(url="/?error=oauth_denied")
    
    if not code:
        return RedirectResponse(url="/?error=no_code")
    
    # Verify state
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        logger.warning("OAuth state mismatch")
        return RedirectResponse(url="/?error=invalid_state")
    
    # Exchange code for token
    token_data = await exchange_code(code)
    if not token_data:
        return RedirectResponse(url="/?error=token_exchange_failed")
    
    access_token = token_data.get("access_token")
    
    user_info = await get_user_info(access_token)
    if not user_info:
        return RedirectResponse(url="/?error=user_info_failed")
    
    guilds = await get_user_guilds(access_token)
    
    # Filter to guilds where user has manage_guild permission (admin)
    admin_guilds = []
    for guild in guilds:
        permissions = int(guild.get("permissions", 0))
        # Check for ADMINISTRATOR (0x8) or MANAGE_GUILD (0x20)
        if permissions & 0x8 or permissions & 0x20:
            admin_guilds.append({
                "id": guild["id"],
                "name": guild["name"],
                "icon": guild.get("icon"),
            })
    
    # Store in session
    request.session["user"] = {
        "id": user_info["id"],
        "username": user_info["username"],
        "discriminator": user_info.get("discriminator", "0"),
        "avatar": user_info.get("avatar"),
        "global_name": user_info.get("global_name"),
    }
    request.session["access_token"] = access_token
    request.session["guilds"] = admin_guilds
    
    logger.info(f"User {user_info['username']} logged in with {len(admin_guilds)} admin guilds")
    
    return RedirectResponse(url="/dashboard")


@auth_router.get("/logout")
async def logout(request: Request):
    """Log out and clear session"""
    request.session.clear()
    return RedirectResponse(url="/")


def get_avatar_url(user: dict) -> str:
    """Get user's avatar URL"""
    if user.get("avatar"):
        return f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
    # Default avatar
    discriminator = int(user.get("discriminator", "0"))
    return f"https://cdn.discordapp.com/embed/avatars/{discriminator % 5}.png"


def get_guild_icon_url(guild: dict) -> Optional[str]:
    """Get guild's icon URL"""
    if guild.get("icon"):
        return f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png"
    return None

