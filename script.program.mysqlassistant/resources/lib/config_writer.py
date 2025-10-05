"""Generate Kodi advancedsettings.xml for the MySQL Assistant add-on."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon("script.program.mysqlassistant")


def write_advancedsettings(
    video_config: Optional[Dict[str, Any]],
    music_config: Optional[Dict[str, Any]],
    migration_opts: Optional[Dict[str, Any]] = None,
) -> str:
    """Persist a Kodi-ready advancedsettings.xml file."""
    profile_dir = xbmcvfs.translatePath("special://profile")
    os.makedirs(profile_dir, exist_ok=True)
    target_path = os.path.join(profile_dir, "advancedsettings.xml")

    root = ET.Element("advancedsettings")

    if video_config:
        _append_database_section(root, "videodatabase", video_config)
    if music_config:
        _append_database_section(root, "musicdatabase", music_config)

    if migration_opts:
        _append_library_preferences(root, migration_opts)

    tree = ET.ElementTree(root)
    try:
        tree.write(target_path, encoding="utf-8", xml_declaration=True)
    except OSError as exc:
        xbmcgui.Dialog().ok(
            _localize(30032, "Failed to save configuration"),
            f"{target_path}\n{exc}",
        )
        raise

    xbmc.log(f"MySQL Assistant wrote advancedsettings.xml to {target_path}", xbmc.LOGINFO)
    return target_path


def _append_database_section(parent: ET.Element, tag: str, config: Dict[str, Any]) -> None:
    section = ET.SubElement(parent, tag)
    mapping = {
        "type": "type",
        "host": "host",
        "port": "port",
        "user": "user",
        "username": "user",
        "password": "pass",
        "pass": "pass",
        "name": "name",
        "database": "name",
        "charset": "charset",
        "collation": "collation",
        "timeout": "timeout",
    }

    for key, xml_tag in mapping.items():
        if key in config and config[key] is not None:
            _set_text(section, xml_tag, config[key])

    if section.find("type") is None:
        _set_text(section, "type", "mysql")


def _append_library_preferences(parent: ET.Element, options: Dict[str, Any]) -> None:
    if not options:
        return

    video_node = ET.SubElement(parent, "videolibrary")
    music_node = ET.SubElement(parent, "musiclibrary")

    preferences = {
        "import_watched": ("importwatchedstate", "importwatchedstate"),
        "import_resume": ("importresumepoints", "importresumepoints"),
        "clean_on_start": ("cleanonupdate", "cleanonupdate"),
    }

    for key, (video_tag, music_tag) in preferences.items():
        if key in options:
            value = options[key]
            _set_text(video_node, video_tag, _bool_to_str(value))
            _set_text(music_node, music_tag, _bool_to_str(value))


def _set_text(parent: ET.Element, tag: str, value: Any) -> None:
    element = parent.find(tag)
    if element is None:
        element = ET.SubElement(parent, tag)
    element.text = _coerce_to_str(value)


def _bool_to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return "true" if value else "false"
    if isinstance(value, str):
        return value.lower()
    return "false"


def _coerce_to_str(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _localize(string_id: int, fallback: str) -> str:
    try:
        text = ADDON.getLocalizedString(string_id)
        return text or fallback
    except Exception:
        return fallback
