#!/usr/bin/env python3
"""
Error reporting via Discord DM to the bot owner.

Harry runs on a host whose logs scroll away, so unhandled errors used to surface only
when someone in the league noticed a broken command. This DMs the bot owner instead —
no third-party service, nothing leaves Discord.

Repeats are collapsed: the same error DMs once per cooldown window, then reports how
many times it fired when the window closes. A global hourly cap keeps a failing loop
from flooding the DM.
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..security import sanitize_ai_response

logger = logging.getLogger('CFB26Bot.ErrorReporter')

# One DM per identical error per window; further hits are counted, not sent
DEDUPE_WINDOW = timedelta(minutes=15)
# Hard ceiling so a tight failure loop can't fill the owner's DMs
MAX_DMS_PER_HOUR = 12
# Discord's message limit is 2000; leave room for the surrounding text
MAX_TRACEBACK_CHARS = 1200


class ErrorReporter:
    """Collapses repeated errors and DMs the bot owner about them."""

    def __init__(self, bot=None):
        self.bot = bot
        self.enabled = True
        self._seen: Dict[str, Dict] = {}  # fingerprint -> {'first_sent', 'count'}
        self._sent_times: list = []
        self._lock = asyncio.Lock()

    def set_bot(self, bot) -> None:
        self.bot = bot

    @staticmethod
    def fingerprint(error: BaseException, context: str) -> str:
        """Identify 'the same error' by type, message and origin, so repeats collapse."""
        tb = error.__traceback__
        last_frame = ""
        while tb is not None:
            last_frame = f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}"
            tb = tb.tb_next
        return f"{type(error).__name__}|{str(error)[:100]}|{last_frame}|{context}"

    def _under_hourly_cap(self) -> bool:
        cutoff = datetime.now() - timedelta(hours=1)
        self._sent_times = [t for t in self._sent_times if t > cutoff]
        return len(self._sent_times) < MAX_DMS_PER_HOUR

    async def _owner_dm(self):
        from .owner_dm import get_owner_dm
        return await get_owner_dm(self.bot)

    @staticmethod
    def _format(error: BaseException, context: str, repeats: int) -> str:
        tb_text = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        ).strip()
        if len(tb_text) > MAX_TRACEBACK_CHARS:
            tb_text = "…\n" + tb_text[-MAX_TRACEBACK_CHARS:]

        # Tracebacks can quote request URLs and headers — strip anything key-shaped
        tb_text = sanitize_ai_response(tb_text)
        summary = sanitize_ai_response(f"{type(error).__name__}: {error}")[:300]

        lines = [f"⚠️ **{context}**", f"`{summary}`"]
        if repeats > 1:
            lines.append(f"_Happened {repeats} times in the last {int(DEDUPE_WINDOW.total_seconds() // 60)} minutes._")
        lines.append(f"```py\n{tb_text}\n```")
        return "\n".join(lines)[:1990]

    async def report(self, error: BaseException, context: str = "Unhandled error") -> bool:
        """
        DM the bot owner about an error. Returns True if a DM was sent.

        Never raises: reporting a failure must not create another one.
        """
        if not self.enabled or not self.bot:
            return False

        try:
            async with self._lock:
                key = self.fingerprint(error, context)
                now = datetime.now()
                entry = self._seen.get(key)

                if entry and now - entry['first_sent'] < DEDUPE_WINDOW:
                    entry['count'] += 1
                    return False

                repeats = (entry or {}).get('count', 0)
                self._seen[key] = {'first_sent': now, 'count': 1}

                # Drop fingerprints whose window has long passed
                self._seen = {
                    k: v for k, v in self._seen.items()
                    if now - v['first_sent'] < DEDUPE_WINDOW * 4
                }

                if not self._under_hourly_cap():
                    logger.warning("⚠️ Error-report DM cap reached this hour, not sending")
                    return False
                self._sent_times.append(now)

            dm = await self._owner_dm()
            if not dm:
                return False
            await dm.send(self._format(error, context, repeats))
            logger.info(f"📩 DMed the bot owner about: {type(error).__name__} ({context})")
            return True
        except Exception as e:  # never let reporting break the caller
            logger.error(f"❌ Failed to send error report: {e}")
            return False

    async def send_notice(self, title: str, body: str) -> bool:
        """DM the owner a plain notice (budget alerts and the like)."""
        if not self.enabled or not self.bot:
            return False
        try:
            async with self._lock:
                if not self._under_hourly_cap():
                    return False
                self._sent_times.append(datetime.now())
            dm = await self._owner_dm()
            if not dm:
                return False
            await dm.send(f"{title}\n{body}"[:1990])
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send notice: {e}")
            return False


_reporter: Optional[ErrorReporter] = None


def get_error_reporter(bot=None) -> ErrorReporter:
    """Get the shared error reporter, attaching the bot the first time it's available."""
    global _reporter
    if _reporter is None:
        _reporter = ErrorReporter(bot)
    elif bot is not None:
        _reporter.set_bot(bot)
    return _reporter
