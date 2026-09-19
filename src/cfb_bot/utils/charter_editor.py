#!/usr/bin/env python3
"""
Charter Editor Module for CFB 26 League Bot
Handles editing and updating the league charter with interactive AI updates
Supports Discord-based persistence for charter content across deployments
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger('CFB26Bot.CharterEditor')

# Discord message limit is 2000 chars, so we chunk the charter
DISCORD_CHUNK_SIZE = 1900  # Leave room for markers


class CharterEditor:
    """Handles editing and updating the league charter"""

    def __init__(self, ai_assistant=None, bot=None):
        self.ai_assistant = ai_assistant
        self.bot = bot  # Discord bot for persistence
        self.charter_file = "data/charter_content.txt"
        self.backup_dir = "data/charter_backups"
        self._discord_charter_loaded = False  # Track if we've loaded from Discord

        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)

    async def _get_bot_owner_dm(self):
        """Get the bot owner's DM channel for storage"""
        if not self.bot:
            return None
        try:
            app_info = await self.bot.application_info()
            if app_info.owner:
                dm_channel = app_info.owner.dm_channel
                if not dm_channel:
                    dm_channel = await app_info.owner.create_dm()
                return dm_channel
        except Exception as e:
            logger.error(f"❌ Could not get bot owner DM: {e}")
        return None

    async def save_to_discord(self, content: str) -> bool:
        """Save charter content to Discord DM for persistence across deployments"""
        if not self.bot:
            logger.warning("⚠️ No bot reference, cannot save charter to Discord")
            return False

        try:
            dm_channel = await self._get_bot_owner_dm()
            if not dm_channel:
                logger.warning("⚠️ Could not get DM channel for charter storage")
                return False

            # Delete old charter messages first
            try:
                async for message in dm_channel.history(limit=50):
                    if (message.author == self.bot.user and
                        message.content.startswith("📜CHARTER_CHUNK_")):
                        await message.delete()
            except Exception:
                pass  # Ignore delete failures

            # Split content into chunks (Discord 2000 char limit)
            chunks = []
            remaining = content
            chunk_num = 0
            while remaining:
                chunk = remaining[:DISCORD_CHUNK_SIZE]
                remaining = remaining[DISCORD_CHUNK_SIZE:]
                chunks.append(chunk)
                chunk_num += 1

            # Send chunks with markers
            total_chunks = len(chunks)
            for i, chunk in enumerate(chunks):
                marker = f"📜CHARTER_CHUNK_{i+1}of{total_chunks}📜\n"
                await dm_channel.send(marker + chunk)

            logger.info(f"💾 Charter saved to Discord ({total_chunks} chunks, {len(content)} chars)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save charter to Discord: {e}")
            return False

    async def load_from_discord(self) -> Optional[str]:
        """Load charter content from Discord DM"""
        if not self.bot:
            return None

        try:
            dm_channel = await self._get_bot_owner_dm()
            if not dm_channel:
                return None

            # Find all charter chunks
            chunks = {}
            total_chunks = 0

            async for message in dm_channel.history(limit=50):
                if (message.author == self.bot.user and
                    message.content.startswith("📜CHARTER_CHUNK_")):
                    # Parse chunk marker: 📜CHARTER_CHUNK_1of5📜
                    first_line = message.content.split('\n')[0]
                    try:
                        # Extract "1of5" from marker
                        marker_content = first_line.replace("📜CHARTER_CHUNK_", "").replace("📜", "")
                        chunk_num, total = marker_content.split("of")
                        chunk_num = int(chunk_num)
                        total_chunks = int(total)

                        # Get content after the marker line
                        content = '\n'.join(message.content.split('\n')[1:])
                        chunks[chunk_num] = content
                    except Exception:
                        continue

            if not chunks:
                logger.info("📄 No charter found in Discord, using file")
                return None

            # Reassemble in order
            if len(chunks) != total_chunks:
                logger.warning(f"⚠️ Charter incomplete: {len(chunks)}/{total_chunks} chunks")
                return None

            full_content = ""
            for i in range(1, total_chunks + 1):
                full_content += chunks.get(i, "")

            logger.info(f"✅ Charter loaded from Discord ({total_chunks} chunks, {len(full_content)} chars)")
            self._discord_charter_loaded = True
            return full_content

        except Exception as e:
            logger.error(f"❌ Failed to load charter from Discord: {e}")
            return None

    async def restore_from_discord(self) -> bool:
        """
        Load the Discord-persisted charter into the local file at startup.

        The file is what /charter search and Harry's AI context read, and it resets to the
        committed copy on every redeploy — so without this, charter edits silently revert.
        """
        content = await self.load_from_discord()
        if not content:
            return False
        if (self.read_charter() or "").strip() == content.strip():
            logger.info("📄 Local charter already matches the Discord copy")
            return True
        try:
            with open(self.charter_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"📄 Restored charter from Discord into {self.charter_file} ({len(content)} chars)")
            return True
        except Exception as e:
            logger.error(f"❌ Could not write restored charter: {e}")
            return False

    def read_charter(self) -> Optional[str]:
        """Read the current charter content from file (sync version)"""
        try:
            if os.path.exists(self.charter_file):
                with open(self.charter_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info(f"📄 Read charter from file: {len(content)} characters")
                return content
            else:
                logger.warning("⚠️ Charter file not found")
                return None
        except Exception as e:
            logger.error(f"❌ Error reading charter: {e}")
            return None


    def backup_charter(self) -> bool:
        """Create a backup of the current charter"""
        try:
            content = self.read_charter()
            if not content:
                return False

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f"charter_backup_{timestamp}.txt")

            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"💾 Charter backed up to {backup_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Error backing up charter: {e}")
            return False

    def write_charter(self, content: str) -> bool:
        """Write new content to the charter (file only - sync version)"""
        try:
            # First, create a backup
            self.backup_charter()

            # Write the new content
            with open(self.charter_file, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"✅ Charter updated in file: {len(content)} characters")
            return True
        except Exception as e:
            logger.error(f"❌ Error writing charter: {e}")
            return False

    async def write_charter_async(self, content: str) -> bool:
        """Write new content to charter - saves to both file AND Discord for persistence"""
        try:
            # First, create a backup
            self.backup_charter()

            # Write to local file
            with open(self.charter_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ Charter updated in file: {len(content)} characters")

            # Also save to Discord for persistence across deployments
            discord_saved = await self.save_to_discord(content)
            if discord_saved:
                logger.info("✅ Charter also saved to Discord for persistence")
            else:
                logger.warning("⚠️ Charter saved to file but NOT to Discord")

            return True
        except Exception as e:
            logger.error(f"❌ Error writing charter: {e}")
            return False

    # ---- Import from a shared document URL -------------------------------------------------

    GOOGLE_DOC_RE = re.compile(r"docs\.google\.com/document/d/([A-Za-z0-9_\-]+)")
    MAX_IMPORT_BYTES = 2_000_000

    @classmethod
    def export_urls(cls, url: str) -> List[str]:
        """
        URLs to try for a charter document, best first.

        A Google Docs link exports as markdown (keeps headings and bullets), with plain
        text as a fallback. Any other URL is fetched as-is.
        """
        match = cls.GOOGLE_DOC_RE.search(url or "")
        if match:
            doc_id = match.group(1)
            return [
                f"https://docs.google.com/document/d/{doc_id}/export?format=markdown",
                f"https://docs.google.com/document/d/{doc_id}/export?format=txt",
            ]
        return [url]

    @staticmethod
    def clean_exported_text(raw: str) -> str:
        """Normalize an exported document: strip BOM/CRLF and Google's markdown escapes."""
        text = raw.lstrip("\ufeff").replace("\r\n", "\n").strip()
        return re.sub(r"\\([.\->\[\]()#*_])", r"\1", text)

    async def import_from_url(self, url: str, user_id: int = 0, user_name: str = "unknown") -> Tuple[bool, str]:
        """
        Replace the charter with the text of a publicly readable document (e.g. the league's
        Google Doc). Backs up the old charter and persists the new one to Discord.

        Returns (ok, message).
        """
        import httpx

        response = None
        last_error = None
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as client:
                for fetch_url in self.export_urls(url):
                    try:
                        candidate = await client.get(fetch_url)
                    except Exception as e:
                        last_error = e
                        continue
                    response = candidate
                    if candidate.status_code == 200:
                        break
        except Exception as e:
            last_error = e

        if response is None:
            logger.error(f"❌ Charter import failed to fetch {url}: {last_error}")
            return False, f"Couldn't fetch that document: {last_error}"

        if response.status_code != 200:
            if response.status_code in (401, 403, 404):
                return False, (
                    f"The document isn't readable (HTTP {response.status_code}). "
                    "Set its sharing to 'Anyone with the link can view' and try again."
                )
            return False, f"The document returned HTTP {response.status_code}."

        if len(response.content) > self.MAX_IMPORT_BYTES:
            return False, "That document is too large to import (over 2 MB)."

        content = self.clean_exported_text(response.text)
        if len(content) < 100:
            return False, "That document looks empty — nothing was imported."
        if content.lstrip().lower().startswith("<!doctype html") or "<html" in content[:200].lower():
            return False, (
                "That link returned a web page instead of the document text. "
                "Use the document's share link and make sure it's viewable by anyone with the link."
            )

        previous = self.read_charter() or ""
        saved = await self.write_charter_async(content)
        if not saved:
            return False, "Fetched the document, but couldn't save the charter."

        self.add_changelog_entry(
            user_id=user_id,
            user_name=user_name,
            action="import",
            description=f"Imported charter from {url}",
            before_text=previous[:500],
            after_text=content[:500],
        )
        delta = len(content) - len(previous)
        return True, (
            f"Imported **{len(content):,}** characters "
            f"({'+' if delta >= 0 else ''}{delta:,} vs the old charter)."
        )

    async def add_rule_section(
        self,
        section_title: str,
        section_content: str,
        position: Optional[str] = None
    ) -> Dict:
        """
        Add a new rule section to the charter

        Args:
            section_title: Title of the new section
            section_content: Content of the new section
            position: Where to add it (e.g., "end", "after:1.7", "before:2.1")

        Returns:
            Dict with status and message
        """
        try:
            current_charter = self.read_charter()
            if not current_charter:
                return {
                    'success': False,
                    'message': 'Could not read current charter'
                }

            # Format the new section
            new_section = f"\n\n### {section_title}\n{section_content}\n"

            # Determine where to insert
            if not position or position == "end":
                # Add to the end
                updated_charter = current_charter + new_section
            elif position.startswith("after:"):
                # Add after a specific section
                target = position.split(":", 1)[1]
                # Find the target section and insert after it
                # This is a simple implementation - could be enhanced
                updated_charter = current_charter.replace(
                    f"### {target}",
                    f"### {target}{new_section}"
                )
            elif position.startswith("before:"):
                # Add before a specific section
                target = position.split(":", 1)[1]
                updated_charter = current_charter.replace(
                    f"### {target}",
                    f"{new_section}\n### {target}"
                )
            else:
                updated_charter = current_charter + new_section

            # Write the updated charter
            success = self.write_charter(updated_charter)

            if success:
                return {
                    'success': True,
                    'message': f'Successfully added section: {section_title}',
                    'new_content': new_section
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to write updated charter'
                }

        except Exception as e:
            logger.error(f"❌ Error adding rule section: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

    async def update_rule_section(
        self,
        section_identifier: str,
        new_content: str
    ) -> Dict:
        """
        Update an existing rule section

        Args:
            section_identifier: Identifier for the section (e.g., "1.1", "Scheduling")
            new_content: New content for the section

        Returns:
            Dict with status and message
        """
        try:
            current_charter = self.read_charter()
            if not current_charter:
                return {
                    'success': False,
                    'message': 'Could not read current charter'
                }

            # Try to find and replace the section
            # This is a simple implementation - looks for section headers
            lines = current_charter.split('\n')
            updated_lines = []
            in_target_section = False
            section_found = False

            for i, line in enumerate(lines):
                # Check if this is our target section
                if section_identifier in line and (line.startswith('##') or line.startswith('###')):
                    in_target_section = True
                    section_found = True
                    updated_lines.append(line)  # Keep the header
                    updated_lines.append(new_content)  # Add new content
                    continue

                # If we're in the target section, skip until next section
                if in_target_section:
                    if line.startswith('##'):
                        # We've reached the next section
                        in_target_section = False
                        updated_lines.append(line)
                    # Skip old content while in target section
                    continue

                # Keep all other lines
                updated_lines.append(line)

            if not section_found:
                return {
                    'success': False,
                    'message': f'Section "{section_identifier}" not found in charter'
                }

            updated_charter = '\n'.join(updated_lines)
            success = self.write_charter(updated_charter)

            if success:
                return {
                    'success': True,
                    'message': f'Successfully updated section: {section_identifier}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to write updated charter'
                }

        except Exception as e:
            logger.error(f"❌ Error updating rule section: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }

    async def format_rule_with_ai(
        self,
        rule_summary: str,
        context: Optional[str] = None
    ) -> Optional[str]:
        """
        Use AI to format a rule summary into proper charter format

        Args:
            rule_summary: Summary of the rule to add
            context: Optional context (e.g., from channel summary)

        Returns:
            Formatted rule text
        """
        if not self.ai_assistant:
            # Return basic formatting without AI
            return f"**Rule**: {rule_summary}"

        try:
            context_text = f"\n\nContext: {context}" if context else ""

            prompt = f"""You are Harry, helping to format a new league rule for the CFB 26 League Charter.

Given this rule summary: {rule_summary}{context_text}

Format it as a proper charter rule entry. Use this style:
- Clear, concise language
- Professional tone (save the sarcasm for chat!)
- Bullet points for details if needed
- Include any relevant conditions or exceptions

Just provide the formatted rule text, nothing else."""

            logger.info(f"🤖 Requesting AI formatting for rule: {rule_summary[:50]}...")
            formatted_rule = await self.ai_assistant.ask_ai(prompt, "Charter Editor")

            if formatted_rule:
                logger.info("✅ AI rule formatting successful")
                return formatted_rule
            else:
                logger.warning("⚠️ AI formatting failed, using basic format")
                return f"**Rule**: {rule_summary}"

        except Exception as e:
            logger.error(f"❌ Error formatting rule with AI: {e}")
            return f"**Rule**: {rule_summary}"


    def get_backup_list(self) -> List[Dict]:
        """Get a list of available charter backups"""
        try:
            backups = []
            for filename in sorted(os.listdir(self.backup_dir), reverse=True):
                if filename.startswith("charter_backup_") and filename.endswith(".txt"):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)

                    # Extract timestamp from filename
                    timestamp_str = filename.replace("charter_backup_", "").replace(".txt", "")

                    backups.append({
                        'filename': filename,
                        'filepath': filepath,
                        'timestamp': timestamp_str,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime)
                    })

            return backups
        except Exception as e:
            logger.error(f"❌ Error listing backups: {e}")
            return []

    def restore_backup(self, backup_filename: str) -> bool:
        """Restore a charter from backup"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)

            if not os.path.exists(backup_path):
                logger.error(f"❌ Backup file not found: {backup_filename}")
                return False

            # Read the backup
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()

            # Backup the current charter before restoring
            self.backup_charter()

            # Restore the backup
            success = self.write_charter(backup_content)

            if success:
                logger.info(f"✅ Charter restored from backup: {backup_filename}")

            return success

        except Exception as e:
            logger.error(f"❌ Error restoring backup: {e}")
            return False

    # ==================== Interactive Update Methods ====================

    def _load_changelog(self) -> List[Dict]:
        """Load the changelog from file"""
        changelog_file = "data/charter_changelog.json"
        try:
            if os.path.exists(changelog_file):
                with open(changelog_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"❌ Error loading changelog: {e}")
            return []

    def _save_changelog(self, changelog: List[Dict]) -> bool:
        """Save the changelog to file"""
        changelog_file = "data/charter_changelog.json"
        try:
            with open(changelog_file, 'w', encoding='utf-8') as f:
                json.dump(changelog, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"❌ Error saving changelog: {e}")
            return False

    def add_changelog_entry(
        self,
        user_id: int,
        user_name: str,
        action: str,
        description: str,
        before_text: Optional[str] = None,
        after_text: Optional[str] = None
    ) -> bool:
        """Add an entry to the changelog"""
        try:
            changelog = self._load_changelog()

            entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "user_name": user_name,
                "action": action,
                "description": description,
                "before": before_text[:500] if before_text else None,  # Limit size
                "after": after_text[:500] if after_text else None
            }

            changelog.append(entry)

            # Keep only last 100 entries
            if len(changelog) > 100:
                changelog = changelog[-100:]

            return self._save_changelog(changelog)
        except Exception as e:
            logger.error(f"❌ Error adding changelog entry: {e}")
            return False

    def get_recent_changes(self, limit: int = 10) -> List[Dict]:
        """Get recent changelog entries"""
        changelog = self._load_changelog()
        return changelog[-limit:][::-1]  # Most recent first





    async def find_rule_changes_in_messages(
        self,
        messages: List[str],
        channel_name: str = "voting channel"
    ) -> Optional[List[Dict]]:
        """
        Analyze messages to find rule changes, votes, and decisions

        Returns list of:
        - rule: the rule text
        - status: passed/failed/proposed
        - votes_for: count (if available)
        - votes_against: count (if available)
        - context: additional context
        """
        if not self.ai_assistant:
            logger.warning("⚠️ AI assistant not available for message analysis")
            return None

        if not messages:
            return None

        # Join messages for analysis
        messages_text = "\n".join(messages[:100])  # Limit to recent 100

        # Log what we're sending to AI for debugging
        logger.info(f"📝 Sending {len(messages)} messages to AI for rule analysis")
        if messages:
            logger.debug(f"📝 First 3 messages:\n" + "\n".join(messages[:3]))

        prompt = f"""You are analyzing a Discord channel called "{channel_name}" for rule changes and votes in a CFB 26 dynasty league.

MESSAGES FROM THE CHANNEL:
{messages_text}

EXAMPLE OF A POLL MESSAGE:
[BoozeRob] POLL: Should we change difficulty to Heisman?
  - Yes (5 votes)
  - No (2 votes)
  STATUS: CLOSED (Total: 7 votes) - WINNER: Yes

This would be extracted as:
{{"rule": "Change game difficulty from All-American to Heisman", "status": "passed", "votes_for": 5, "votes_against": 2, "context": "Poll passed with Yes winning 5-2"}}

YOUR TASK:
Look through the messages above and find ANY of these:
1. Polls with votes (look for "POLL:" and vote counts)
2. Rule proposals or discussions
3. Decisions that were made
4. Policy changes

For EACH item found, extract it as JSON.

RESPOND WITH ONLY A JSON ARRAY (no markdown, no explanation):
[
    {{
        "rule": "Description of what was voted on or proposed",
        "status": "passed" or "failed" or "proposed" or "decided",
        "votes_for": number or null,
        "votes_against": number or null,
        "context": "Brief explanation of outcome"
    }}
]

If truly nothing is found, respond with exactly: []

IMPORTANT: Even if you're not 100% sure, include anything that looks like a rule vote or proposal!"""

        try:
            response = await self.ai_assistant.ask_openai(prompt, "Rule Change Finder", max_tokens=2000)
            if not response:
                response = await self.ai_assistant.ask_anthropic(prompt, "Rule Change Finder", max_tokens=2000)

            if not response:
                return None

            # Clean up response
            response = response.strip()
            if response.startswith("```"):
                response = re.sub(r'^```\w*\n?', '', response)
                response = re.sub(r'\n?```$', '', response)

            # Parse JSON
            changes = json.loads(response)
            logger.info(f"📜 Found {len(changes)} rule changes in {channel_name}")
            # Log details for debugging
            for i, change in enumerate(changes):
                logger.debug(f"  Rule {i+1}: {change.get('rule', 'N/A')[:50]}...")
                logger.debug(f"    Status: {change.get('status')}, Context: {change.get('context', 'NONE')[:50] if change.get('context') else 'NONE'}...")
            return changes

        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse rule changes JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error finding rule changes: {e}")
            return None

