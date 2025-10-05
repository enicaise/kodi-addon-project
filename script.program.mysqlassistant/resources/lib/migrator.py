"""Migration helpers for MySQL Assistant.

This module orchestrates copying data from Kodi's local SQLite libraries to a
user-selected MySQL or MariaDB database. It exposes convenience wrappers for
video and music libraries as well as a generic migrator that operates on a
single SQLite database file.
"""

from __future__ import annotations

import glob
import logging
import os
import sqlite3
from contextlib import closing
from typing import Any, Dict, Iterable, Optional, Sequence

import xbmcaddon
import xbmcgui
import xbmcvfs

try:  # Prefer mysql-connector, fall back to PyMySQL if available
    import mysql.connector as connector
except ImportError:  # pragma: no cover - runtime dependency
    try:
        import pymysql as connector  # type: ignore
    except ImportError:  # pragma: no cover - runtime dependency
        connector = None  # type: ignore

ADDON = xbmcaddon.Addon("script.program.mysqlassistant")


def _localize(string_id: int, fallback: str) -> str:
    """Fetch a translated string, falling back to a hard-coded value."""
    try:
        text = ADDON.getLocalizedString(string_id)
        return text or fallback
    except Exception:  # pragma: no cover - Kodi environment specific
        return fallback


def _show_error(message: str) -> None:
    """Present an error message to the user and log it."""
    xbmcgui.Dialog().ok(_localize(30015, "Migration error"), message)
    logging.error(message)


def _show_success(summary: str, detail: str) -> None:
    xbmcgui.Dialog().ok(summary, detail)
    logging.info("%s - %s", summary, detail)


def migrate_video_library(
    sqlite_pattern: str,
    server_params: Dict[str, Any],
    video_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Copy the local video library into the configured MySQL database."""
    return _migrate_kodi_library(sqlite_pattern, server_params, video_config, "MyVideos")


def migrate_music_library(
    sqlite_pattern: str,
    server_params: Dict[str, Any],
    music_config: Optional[Dict[str, Any]] = None,
) -> bool:
    """Copy the local music library into the configured MySQL database."""
    return _migrate_kodi_library(sqlite_pattern, server_params, music_config, "MyMusic")


def _migrate_kodi_library(
    sqlite_pattern: str,
    server_params: Dict[str, Any],
    library_config: Optional[Dict[str, Any]],
    default_prefix: str,
) -> bool:
    if connector is None:
        _show_error(_localize(30011, "MySQL connector module is not available."))
        return False

    target_database = _resolve_database_name(library_config, default_prefix)
    if not target_database:
        _show_error(_localize(30018, "Missing database name for migration."))
        return False

    sqlite_path = _resolve_sqlite_path(sqlite_pattern, default_prefix)
    if not sqlite_path:
        _show_error(_localize(30019, "Could not locate local SQLite library."))
        return False

    mysql_params = _build_mysql_params(server_params, target_database)
    if mysql_params is None:
        return False

    return migrate_database(sqlite_path, mysql_params)


def _resolve_database_name(config: Optional[Dict[str, Any]], default_prefix: str) -> Optional[str]:
    if not config:
        return None
    for key in ("database", "name", "dbname"):
        value = config.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    suffix = config.get("version") if config else None
    if isinstance(suffix, (str, int)) and str(suffix).strip():
        return f"{default_prefix}{suffix}"
    return None


def _resolve_sqlite_path(pattern: str, default_prefix: str) -> Optional[str]:
    folder, filename = os.path.split(pattern)
    if not filename:
        filename = f"{default_prefix}*.db"
    if folder.startswith("special://"):
        folder = xbmcvfs.translatePath(folder)
    matches = sorted(glob.glob(os.path.join(folder, filename)))
    if not matches:
        return None
    return matches[-1]


def _build_mysql_params(server_params: Dict[str, Any], database: str) -> Optional[Dict[str, Any]]:
    required_keys = ("host", "user", "password")
    missing = [key for key in required_keys if not server_params.get(key)]
    if missing:
        _show_error(
            _localize(30020, "Missing MySQL connection details: {0}").format(", ".join(missing))
        )
        return None

    params: Dict[str, Any] = {
        "host": server_params.get("host"),
        "user": server_params.get("user"),
        "password": server_params.get("password"),
        "database": database,
    }

    port = server_params.get("port")
    if port:
        try:
            params["port"] = int(port)
        except (TypeError, ValueError):
            _show_error(_localize(30021, "Invalid MySQL port value."))
            return None

    return params


def migrate_database(sqlite_path: str, mysql_params: Dict[str, Any]) -> bool:
    """Transfer rows from an SQLite database into an existing MySQL schema."""
    if connector is None:
        _show_error(_localize(30011, "MySQL connector module is not available."))
        return False

    if not os.path.exists(sqlite_path):
        _show_error(_localize(30022, "SQLite source not found: {path}").format(path=sqlite_path))
        return False

    database_name = mysql_params.get("database")
    if not database_name:
        _show_error(_localize(30018, "Missing database name for migration."))
        return False

    mysql_conn = None
    try:
        server_params = {k: v for k, v in mysql_params.items() if k != "database"}
        _ensure_database_exists(server_params, database_name)
        mysql_conn = connector.connect(database=database_name, **server_params)
    except Exception as exc:  # pragma: no cover - requires database
        _show_error(_localize(30023, "MySQL connection failed: {error}").format(error=exc))
        return False

    migrated_tables = 0
    try:
        with closing(sqlite3.connect(sqlite_path)) as sqlite_conn:
            sqlite_conn.row_factory = sqlite3.Row
            with closing(sqlite_conn.cursor()) as sqlite_cursor, closing(mysql_conn.cursor()) as mysql_cursor:
                for table in _iter_sqlite_tables(sqlite_cursor):
                    if not _mysql_table_exists(mysql_cursor, table):
                        logging.warning("Skipping table '%s' (missing in MySQL)", table)
                        continue
                    rows = _fetch_all_rows(sqlite_cursor, table)
                    if not rows:
                        continue
                    columns = list(rows[0].keys())
                    insert_sql = _build_insert_sql(table, columns)
                    values = [tuple(row[col] for col in columns) for row in rows]
                    try:
                        mysql_cursor.executemany(insert_sql, values)
                        mysql_conn.commit()
                        migrated_tables += 1
                        logging.info("Migrated %d rows into '%s'", len(values), table)
                    except Exception as exc:  # pragma: no cover - requires database
                        mysql_conn.rollback()
                        logging.exception("Failed to migrate table '%s': %s", table, exc)
        summary = _localize(30016, "Migration complete")
        detail = _localize(30017, "Imported data into {tables} tables.").format(tables=migrated_tables)
        _show_success(summary, detail)
        return True
    except Exception as exc:  # pragma: no cover - requires filesystem
        _show_error(_localize(30024, "Unexpected migration error: {error}").format(error=exc))
        return False
    finally:
        try:
            mysql_conn.close()
        except Exception:  # pragma: no cover - connection cleanup
            pass


def _ensure_database_exists(server_params: Dict[str, Any], database: str) -> None:
    """Create the target database if it does not already exist."""
    db_identifier = database.replace("`", "``")
    with closing(connector.connect(**server_params)) as conn:  # type: ignore[arg-type]
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_identifier}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()


def _iter_sqlite_tables(cursor: sqlite3.Cursor) -> Iterable[str]:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    for row in cursor.fetchall():
        yield row[0]


def _fetch_all_rows(cursor: sqlite3.Cursor, table: str) -> Sequence[sqlite3.Row]:
    cursor.execute(f"SELECT * FROM {table}")
    return cursor.fetchall()


def _mysql_table_exists(cursor: Any, table: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table,))
    return cursor.fetchone() is not None


def _build_insert_sql(table: str, columns: Iterable[str]) -> str:
    column_names = list(columns)
    column_list = ", ".join(f"`{col}`" for col in column_names)
    placeholders = ", ".join(["%s"] * len(column_names))
    return f"INSERT IGNORE INTO `{table}` ({column_list}) VALUES ({placeholders})"




