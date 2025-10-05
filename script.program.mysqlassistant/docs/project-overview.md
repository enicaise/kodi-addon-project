# MySQL Assistant Add-on Overview

## Purpose
MySQL Assistant (`script.program.mysqlassistant`) guides Kodi users through configuring a shared MySQL or MariaDB backend for both the video and music libraries. The add-on discovers database servers, validates credentials, migrates data from the local SQLite collections, and writes a ready-to-use `advancedsettings.xml` file.

## High-level Architecture
- **Entry point**: `default.py` orchestrates a dialogue-driven wizard using Kodi's built-in dialog API (`xbmcgui.Dialog`).
- **Support modules**:
  - `resources/lib/scanner.py` – scans the local /24 subnet for MySQL/MariaDB servers and validates credentials.
  - `resources/lib/config_writer.py` – generates `advancedsettings.xml` in Kodi's profile directory using standard `<videodatabase>` / `<musicdatabase>` nodes.
  - `resources/lib/db_checker.py` – inspects remote servers for Kodi databases and compares schema versions against the running Kodi build.
  - `resources/lib/migrator.py` – migrates tables from the local SQLite databases into the chosen MySQL schemas, creating the schemas when needed.
- **Localisation**: string catalogs in `resources/language/resource.language.*` provide UI text (English, French, Dutch).
- **Legacy prototypes**: Scripts under `src/` are kept for reference and are not part of the runtime flow.

## Runtime Flow (`default.py`)
1. **Mode selection** – the user chooses between scanning the local network or entering connection details manually.
2. **Credentials** – the wizard gathers host, port, username, and password, retrying until a connection is confirmed.
3. **Database selection** – suggested database names are derived from the current Kodi version; the user can enable video, music, or both.
4. **Migration options** – optional migration of video/music data plus toggles for importing watched states, resume points, and cleaning libraries.
5. **Finalisation** – migrations run (if selected), `advancedsettings.xml` is generated in `special://profile`, and a summary dialog lists the resulting configuration.

## Module Notes
- `scanner.py` currently scans synchronously and assumes IPv4; large networks may take noticeable time.
- `config_writer.py` writes Kodi-compliant database sections and optional library import flags, logging the output path.
- `db_checker.py` maps Kodi releases to the expected MySQL schema versions (Omega/Nexus/Matrix/Leia) to detect outdated databases.
- `migrator.py` uses `INSERT IGNORE` semantics to avoid duplicate key failures and skips tables missing on the MySQL side (allowing Kodi to bootstrap schemas first).

## Localisation
All user-facing text is routed through localisation IDs (30010–30069). English, French, and Dutch catalogs are shipped; additional languages can be added by mirroring the same IDs.

## Dependencies
- Kodi Python API modules: `xbmc`, `xbmcaddon`, `xbmcgui`, `xbmcvfs`.
- Python MySQL connector inside Kodi's Python environment: `mysql-connector-python` (preferred) or `PyMySQL`.
- Standard library modules: `socket`, `ipaddress`, `logging`, `sqlite3`, `xml.etree.ElementTree`, `glob`, etc.

## Data Inputs and Outputs
- **Inputs**: MySQL/MariaDB connection details, desired database names, migration options.
- **Outputs**:
  - `advancedsettings.xml` written to Kodi's profile directory (`special://profile`).
  - Optional migration of local SQLite data into the MySQL target schemas.
  - Summary and error dialogs for user feedback.

## Limitations
- Network scanning is a simple TCP connect sweep over `/24`; larger or segmented networks may require manual entry.
- The wizard currently focuses on core MySQL settings; advanced Kodi options (e.g., cache tuning) still require manual XML edits.
- Credentials are cached only for the duration of the wizard and are stored in `advancedsettings.xml` in plain text, as per Kodi's standard approach.

## Next Enhancements (Ideas)
- Allow chunked migration to reduce memory usage on very large tables.
- Offer optional backup/export of the local SQLite databases before migration.
- Detect and warn about mismatched character sets or collation settings on the target server.
