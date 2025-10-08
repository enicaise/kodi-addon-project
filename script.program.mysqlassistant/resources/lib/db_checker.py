"""Utilities for inspecting Kodi database versions on a MySQL server."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon("script.program.mysqlassistant")

# Attempt to import MySQL connector libraries
try:
    import mysql.connector as db_connector  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    try:
        import pymysql as db_connector  # type: ignore
    except ImportError:  # pragma: no cover - optional dependency
        db_connector = None  # type: ignore

KODI_DB_VERSION_MAP: Dict[int, Dict[str, str]] = {
    21: {"MyVideos": "122", "MyMusic": "84"},
    20: {"MyVideos": "121", "MyMusic": "82"},
    19: {"MyVideos": "119", "MyMusic": "82"},
    18: {"MyVideos": "116", "MyMusic": "72"},
    17: {"MyVideos": "107", "MyMusic": "60"},
}


def _show_missing_module_error() -> None:
    xbmcgui.Dialog().ok(
        ADDON.getLocalizedString(30010),
        ADDON.getLocalizedString(30011),
    )


def _parse_kodi_major(version: Optional[str]) -> Optional[int]:
    if not version:
        return None
    try:
        return int(version.split(".")[0])
    except (IndexError, ValueError):
        return None


def _expected_versions_for(major: Optional[int]) -> Dict[str, str]:
    if not KODI_DB_VERSION_MAP:
        return {}
    sorted_majors = sorted(KODI_DB_VERSION_MAP.keys())
    if major is None:
        chosen = sorted_majors[-1]
    else:
        chosen = sorted_majors[0]
        for candidate in sorted_majors:
            if major >= candidate:
                chosen = candidate
            else:
                break
        if major >= sorted_majors[-1]:
            chosen = sorted_majors[-1]
    return dict(KODI_DB_VERSION_MAP.get(chosen, {}))


def get_existing_kodi_dbs(host: str, port: int, user: str, password: str) -> Dict[str, str]:
    """Return discovered Kodi databases on the MySQL server with their version suffix."""
    if db_connector is None:
        _show_missing_module_error()
        return {}

    try:
        conn = db_connector.connect(host=host, port=port, user=user, password=password)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'MyVideos%'")
        video_dbs = [(row[0], row[0].replace("MyVideos", "")) for row in cursor.fetchall()]
        cursor.execute("SHOW DATABASES LIKE 'MyMusic%'")
        music_dbs = [(row[0], row[0].replace("MyMusic", "")) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return {name: version for name, version in video_dbs + music_dbs}
    except Exception as exc:  # pragma: no cover - MySQL environment specific
        logging.error("Failed to list Kodi databases: %s", exc)
        return {}


def get_kodi_version() -> str:
    """Return the running Kodi version (e.g. '20.1')."""
    try:
        import xbmc

        kodi_version = xbmc.getInfoLabel("System.BuildVersion")
        return kodi_version.split(" ")[0]
    except Exception as exc:  # pragma: no cover - Kodi runtime only
        logging.error("Failed to resolve Kodi version: %s", exc)
        return "0.0"


def get_kodi_db_names() -> List[str]:
    """Return standard Kodi database prefixes."""
    return ["MyVideos", "MyMusic"]


def get_kodi_db_versions() -> Dict[str, str]:
    """Return expected database versions for the running Kodi build."""
    major = _parse_kodi_major(get_kodi_version())
    return _expected_versions_for(major)


def get_kodi_db_info() -> Dict[str, str]:
    """Return a mapping of Kodi database prefixes to expected version numbers."""
    versions = get_kodi_db_versions()
    info: Dict[str, str] = {}
    for prefix in get_kodi_db_names():
        info[prefix] = versions.get(prefix, "0")
    return info


def is_version_compatible(db_name: str, kodi_version: str) -> bool:
    """Return True when the supplied database name matches or exceeds the expected schema version."""
    expected = _expected_versions_for(_parse_kodi_major(kodi_version))
    if db_name.startswith("MyVideos"):
        prefix = "MyVideos"
    elif db_name.startswith("MyMusic"):
        prefix = "MyMusic"
    else:
        return False

    try:
        db_version = int(db_name.replace(prefix, ""))
    except ValueError:
        logging.error("Unable to parse database version from '%s'", db_name)
        return False

    expected_version = expected.get(prefix)
    if expected_version is None:
        return True
    try:
        expected_int = int(expected_version)
    except ValueError:
        return True
    return db_version >= expected_int


def check_kodi_dbs(host: str, port: int, user: str, password: str) -> Dict[str, Any]:
    """Check the server for Kodi databases and classify them against expected versions."""
    existing = get_existing_kodi_dbs(host, port, user, password)
    kodi_ver = get_kodi_version()
    expected_info = get_kodi_db_info()

    if not existing:
        return {"error": ADDON.getLocalizedString(30012)}

    incompatible: Dict[str, str] = {}
    for db, version in existing.items():
        prefix = "MyVideos" if db.startswith("MyVideos") else "MyMusic"
        if prefix in expected_info and not is_version_compatible(db, kodi_ver):
            incompatible[db] = version

    if incompatible:
        return {"incompatible": incompatible}
    return {"compatible": existing}


def get_db_connection(host: str, port: int, user: str, password: str):
    """Return a MySQL connection handle or None, showing a dialog on failure."""
    if db_connector is None:
        _show_missing_module_error()
        return None
    try:
        return db_connector.connect(host=host, port=port, user=user, password=password)
    except Exception as exc:  # pragma: no cover - MySQL runtime specific
        logging.error("Database connection failed: %s", exc)
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(30013), str(exc))
        return None


def close_db_connection(conn) -> None:
    """Close the connection if it exists."""
    try:
        if conn:
            conn.close()
            logging.info("Database connection closed.")
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logging.error("Error closing connection: %s", exc)


def get_db_cursor(conn):
    """Return a cursor for the provided connection."""
    if not conn:
        logging.error("No connection provided for cursor creation.")
        return None
    try:
        return conn.cursor()
    except Exception as exc:  # pragma: no cover - MySQL runtime specific
        logging.error("Failed to create cursor: %s", exc)
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(30014), str(exc))
        return None


def close_db_cursor(cursor) -> None:
    """Close the cursor when present."""
    try:
        if cursor:
            cursor.close()
            logging.info("Database cursor closed.")
    except Exception as exc:  # pragma: no cover - best effort cleanup
        logging.error("Error closing cursor: %s", exc)


def execute_query(cursor, query: str, params: Optional[tuple] = None) -> Any:
    """Execute a SQL query and return all rows."""
    if not cursor:
        logging.error("No cursor provided for query execution.")
        return None
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Exception as exc:  # pragma: no cover - MySQL runtime specific
        logging.error("Query execution failed: %s", exc)
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(30015), str(exc))
        return None

