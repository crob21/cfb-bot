"""
Dashboard Routes
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .auth import get_avatar_url, get_guild_icon_url

logger = logging.getLogger('Dashboard.Routes')

router = APIRouter()

# Templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Bot config storage path (shared with bot)
CONFIG_FILE = Path(os.getenv('CONFIG_PATH', '/tmp/harry_server_configs.json'))


def require_auth(request: Request):
    """Dependency to require authentication"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def load_configs() -> dict:
    """Load server configs from file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading configs: {e}")
    return {}


def save_configs(configs: dict):
    """Save server configs to file"""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(configs, f, indent=2)
        logger.info(f"✅ Saved configs for {len(configs)} servers")
    except Exception as e:
        logger.error(f"Error saving configs: {e}")


def get_server_config(guild_id: str) -> dict:
    """Get config for a specific server"""
    configs = load_configs()
    if guild_id not in configs:
        # Default config
        return {
            "modules": {
                "core": True,
                "cfb_data": True,
                "league": False,
            },
            "settings": {
                "timer_channel_id": None,
                "admin_channel_id": None,
                "auto_responses": True,  # Enable automatic jump-in responses (team banter)
                "schedule_announcement": True,  # Week matchups message when timer starts/advances
            },
            "admins": []
        }
    return configs[guild_id]


def save_server_config(guild_id: str, config: dict):
    """Save config for a specific server"""
    configs = load_configs()
    configs[guild_id] = config
    save_configs(configs)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_auth)):
    """Main dashboard page"""
    guilds = request.session.get("guilds", [])
    
    # Add icon URLs
    for guild in guilds:
        guild["icon_url"] = get_guild_icon_url(guild)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "avatar_url": get_avatar_url(user),
        "guilds": guilds,
    })


@router.get("/server/{guild_id}", response_class=HTMLResponse)
async def server_config(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Server configuration page"""
    guilds = request.session.get("guilds", [])
    
    # Find the guild
    guild = next((g for g in guilds if g["id"] == guild_id), None)
    if not guild:
        raise HTTPException(status_code=403, detail="You don't have admin access to this server")
    
    config = get_server_config(guild_id)
    guild["icon_url"] = get_guild_icon_url(guild)
    
    return templates.TemplateResponse("server.html", {
        "request": request,
        "user": user,
        "avatar_url": get_avatar_url(user),
        "guild": guild,
        "config": config,
        "guilds": guilds,
    })


# API Routes

@router.get("/api/server/{guild_id}/config")
async def get_config(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Get server configuration"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return get_server_config(guild_id)


@router.post("/api/server/{guild_id}/modules")
async def update_modules(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Update module settings"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    data = await request.json()
    config = get_server_config(guild_id)
    
    # Update modules (but core is always true)
    if "modules" in data:
        config["modules"]["cfb_data"] = data["modules"].get("cfb_data", True)
        config["modules"]["league"] = data["modules"].get("league", False)
        config["modules"]["core"] = True  # Always on
    
    save_server_config(guild_id, config)
    logger.info(f"✅ Updated modules for guild {guild_id}")
    
    return {"success": True, "config": config}


@router.post("/api/server/{guild_id}/settings")
async def update_settings(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Update server settings"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    data = await request.json()
    config = get_server_config(guild_id)
    
    if "settings" in data:
        config["settings"].update(data["settings"])
    
    save_server_config(guild_id, config)
    logger.info(f"✅ Updated settings for guild {guild_id}")
    
    return {"success": True, "config": config}


@router.get("/api/server/{guild_id}/admins")
async def get_admins(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Get bot admins for server"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = get_server_config(guild_id)
    return {"admins": config.get("admins", [])}


@router.post("/api/server/{guild_id}/admins")
async def add_admin(request: Request, guild_id: str, user: dict = Depends(require_auth)):
    """Add a bot admin"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    data = await request.json()
    user_id = data.get("user_id")
    username = data.get("username", "Unknown")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    config = get_server_config(guild_id)
    if "admins" not in config:
        config["admins"] = []
    
    # Check if already admin
    if any(a["id"] == user_id for a in config["admins"]):
        return {"success": False, "error": "User is already an admin"}
    
    config["admins"].append({"id": user_id, "username": username})
    save_server_config(guild_id, config)
    
    logger.info(f"✅ Added admin {username} ({user_id}) to guild {guild_id}")
    return {"success": True, "admins": config["admins"]}


@router.delete("/api/server/{guild_id}/admins/{user_id}")
async def remove_admin(request: Request, guild_id: str, user_id: str, user: dict = Depends(require_auth)):
    """Remove a bot admin"""
    guilds = request.session.get("guilds", [])
    if not any(g["id"] == guild_id for g in guilds):
        raise HTTPException(status_code=403, detail="Access denied")
    
    config = get_server_config(guild_id)
    if "admins" not in config:
        config["admins"] = []
    
    config["admins"] = [a for a in config["admins"] if a["id"] != user_id]
    save_server_config(guild_id, config)
    
    logger.info(f"✅ Removed admin {user_id} from guild {guild_id}")
    return {"success": True, "admins": config["admins"]}

