# Version Management Guide 📜

This guide explains how to manage versions and maintain the changelog for CFB Bot (Harry).

**Current Version:** 3.7.0  
**Version File:** `src/cfb_bot/utils/version_manager.py`

---

## Semantic Versioning (SemVer)

Version format: `MAJOR.MINOR.PATCH`

### MAJOR Version (X.0.0)
Increment for **breaking changes** or **major redesigns**

**Examples:**
- Complete bot rewrite
- Breaking changes to command syntax
- Removing features

### MINOR Version (1.X.0)
Increment for **new features** (backwards-compatible)

**Examples:**
- Adding new slash commands
- New modules (CFB Data, Dashboard)
- Significant improvements

### PATCH Version (1.1.X)
Increment for **bug fixes** (backwards-compatible)

**Examples:**
- Bug fixes
- Performance improvements
- Documentation updates

---

## How to Update Version

### Step 1: Determine Version Increment

- **New features?** → MINOR (1.12.0 → 1.13.0)
- **Bug fixes only?** → PATCH (1.12.0 → 1.12.1)
- **Breaking changes?** → MAJOR (1.12.0 → 2.0.0)

### Step 2: Edit version_manager.py

Open `src/cfb_bot/utils/version_manager.py`

#### Update CURRENT_VERSION

```python
# Change this line:
CURRENT_VERSION = "1.13.0"

# To new version:
CURRENT_VERSION = "1.14.0"
```

#### Add Changelog Entry

Add a new entry to the `CHANGELOG` dictionary (at the top!):

```python
CHANGELOG: Dict[str, Dict] = {
    "1.14.0": {  # NEW VERSION HERE
        "date": "2026-01-15",  # Release date
        "title": "Brief Description",  # Short title
        "emoji": "🚀",  # Emoji for this release
        "features": [
            {
                "category": "Feature Category",
                "emoji": "⚡",
                "changes": [
                    "First change description",
                    "Second change description",
                    "Third change description"
                ]
            },
        ]
    },
    "1.13.0": {  # Keep existing versions below
        # ... existing changelog
    }
}
```

### Step 3: Write Good Changelog Entries

**Good entries are:**
- ✅ Clear and concise
- ✅ User-focused (what users can do)
- ✅ Specific about what changed
- ✅ Action-oriented

**Examples:**

✅ **Good:**
- "Added `/channel` command for per-channel configuration"
- "Smart player suggestions when lookup fails"
- "Fixed stat calculation error in bulk lookups"

❌ **Bad:**
- "Updated code"
- "Fixed stuff"
- "Made changes to bot.py"

### Step 4: Commit and Push

```bash
git add src/cfb_bot/utils/version_manager.py
git commit -m "Bump version to 1.14.0

- Feature 1 description
- Feature 2 description"
git push
```

---

## Testing Your Changes

Before deploying:

1. **Run bot locally** and check startup logs for version
2. **Test `/version`** command
3. **Test `/changelog`** command
4. **Test `/whats_new`** command
5. **Verify embeds** display correctly

---

## Quick Reference Checklist

When releasing a new version:

- [ ] Determine version number (MAJOR.MINOR.PATCH)
- [ ] Update `CURRENT_VERSION` in `version_manager.py`
- [ ] Add changelog entry with:
  - [ ] Version number
  - [ ] Release date
  - [ ] Title and emoji
  - [ ] All features categorized
- [ ] Update `docs/CHANGELOG.md`
- [ ] Test version commands locally
- [ ] Commit and push
- [ ] Verify deployment
- [ ] Announce with `/whats_new`

---

## Version History Reference

### Recent Versions

| Version | Date | Title |
|---------|------|-------|
| 1.14.0 | 2026-01-09 | Admin Channel & Notifications |
| 1.13.0 | 2026-01-09 | Storage Abstraction Layer |
| 1.12.0 | 2026-01-09 | Per-Channel Controls |
| 1.11.0 | 2026-01-09 | Auto Response Toggle |
| 1.10.0 | 2026-01-08 | Smart Player Suggestions |
| 1.9.0 | 2026-01-08 | Web Dashboard |
| 1.8.0 | 2026-01-08 | Per-Server Configuration |
| 1.7.0 | 2026-01-08 | Full CFB Data Suite |
| 1.6.0 | 2026-01-08 | Player Lookup |
| 1.5.0 | 2025-12-31 | Charter Persistence |
| 1.4.0 | 2025-12-31 | Server-Wide Timer |
| 1.3.0 | 2025-12-31 | Interactive Charter |
| 1.2.0 | 2025-12-29 | Dynasty Week System |
| 1.1.0 | 2025-11-04 | Major Feature Update |
| 1.0.0 | 2024-09-17 | Initial Release |

---

## Common Mistakes to Avoid

❌ **Forgetting to update version** - Always update when adding features!

❌ **Vague changelog entries** - Be specific about what changed

❌ **Wrong version increment** - Follow SemVer rules

❌ **Not testing** - Test version commands before deploying

❌ **Forgetting docs/CHANGELOG.md** - Keep both in sync!

---

## Need Help?

If unsure about version numbering:

1. **Small fixes/tweaks?** → PATCH
2. **New features/commands?** → MINOR
3. **Breaking changes?** → MAJOR

**When in doubt, increment MINOR for any user-facing changes!**

---

**Document Version:** 2.0  
**Last Updated:** January 9, 2026
