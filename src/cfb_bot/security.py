#!/usr/bin/env python3
"""
Security constants for CFB Bot (Harry)

Centralized security settings to prevent issues like:
- Hanging requests
- Memory leaks
- Denial of service
"""

# HTTP Request Timeouts (seconds)
HTTP_TIMEOUT = 30  # Default timeout for all HTTP requests
HTTP_CONNECT_TIMEOUT = 10  # Connection timeout
HTTP_READ_TIMEOUT = 30  # Read timeout

# API Rate Limiting
API_RETRY_ATTEMPTS = 3  # Number of retries for failed API calls
API_RETRY_BACKOFF = 2  # Exponential backoff multiplier (2^attempt seconds)

# Input Validation
MAX_INPUT_LENGTH = 2000  # Maximum characters for user input
MAX_MESSAGE_LENGTH = 4000  # Discord message limit (with buffer)

# Logging Safety
LOG_MESSAGE_TRUNCATE = 100  # Truncate logged messages to this length
REDACT_PATTERNS = [
    r'http[s]?://[^\s]+',  # URLs
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
    r'(?i)(password|token|key|secret)[\s:=]+[\S]+',  # Secrets
]

# Cache Limits
MAX_CACHE_SIZE_MB = 100  # Maximum cache size in MB
CACHE_CLEANUP_INTERVAL = 3600  # Cleanup every hour

# Discord Rate Limits (respect Discord API)
DISCORD_MESSAGE_RATE_LIMIT = 5  # Messages per user per 5 seconds
DISCORD_COMMAND_COOLDOWN = 3  # Seconds between commands

# AI Safety
MAX_AI_CONTEXT_LENGTH = 8000  # Max tokens for AI context
MAX_AI_RESPONSE_LENGTH = 1000  # Max tokens for AI response

# Web Scraping Limits
MAX_SCRAPE_RETRIES = 2  # Max retries for web scraping
SCRAPE_DELAY = 2  # Seconds to wait between scrapes (be nice)
