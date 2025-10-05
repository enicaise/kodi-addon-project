# Copilot Prompt: Kodi Addon for MySQL Library Setup

# This Kodi addon is a "program" type addon written in Python 3 and targets Kodi 20+ (xbmc.python >= 3.0.0).
# It helps users configure a shared MySQL/MariaDB backend for Kodi's video and music libraries.

# GOAL:
# Provide a user-friendly assistant (wizard-style) to scan the local network for MySQL/MariaDB servers,
# generate a compatible advancedsettings.xml file, and migrate existing local libraries into a centralized DB.

# FEATURES REQUIRED:
# 1. Network Discovery:
#   - Automatically detect available SQL servers using port scanning on subnet (default: same as Kodi's IP/netmask)
#   - Fallback to manual entry (IP, port, username, password)
#   - Test connection (check credentials and DB creation rights)

# 2. Configuration Wizard:
#   - Step-by-step layout using Kodi's XML-based GUI with skin support
#   - Explanatory tooltips or info bubbles at each step (simple language for non-technical users)
#   - Separate configuration for:
#     - MySQL Video DB (MyVideosXXX)
#     - MySQL Music DB (MyMusicXXX)
#     - Option to configure both at once

# 3. Validation and Migration:
#   - Check if a Kodi DB already exists on the server (MyVideos / MyMusic)
#   - Compare DB version with current Kodi version
#   - Warn the user if the existing DB is outdated and ask for permission to upgrade it
#   - Ask for permission before migrating local SQLite DBs (with checkboxes: watched status, resume points, etc.)
#   - Export and import supported for both video and audio libraries

# 4. Output:
#   - Generate and save `advancedsettings.xml` in the user's Kodi data folder
#   - Provide success/failure messages after testing and applying the config

# 5. Translations and Skins:
#   - Localized in English, French, and Dutch using Kodi's standard `resources/language/resource.language.*/strings.po`
#   - Use `xbmc.getLocalizedString(id)` throughout for text
#   - Follow theming and layout standards to work well across different Kodi skins

# 6. File Structure:
#   - addon.xml
#   - resources/lib/
#     - scanner.py (network scanner)
#     - config_writer.py (XML writer)
#     - db_checker.py (MySQL DB structure checker)
#     - migrator.py (SQLite to MySQL logic)
#   - resources/skins/default/720p/*.xml (GUI layout)
#   - resources/language/resource.language.en_gb/strings.po
#   - resources/language/resource.language.fr_fr/strings.po
#   - resources/language/resource.language.nl_nl/strings.po
#   - default.py (entry point)
