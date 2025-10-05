"""Entry point for the MySQL Assistant Kodi add-on."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

import xbmc
import xbmcaddon
import xbmcgui

from resources.lib.config_writer import write_advancedsettings
from resources.lib.db_checker import get_kodi_db_versions
from resources.lib.migrator import migrate_music_library, migrate_video_library
from resources.lib.scanner import scan_network, test_connection

ADDON_ID = "script.program.mysqlassistant"
ADDON = xbmcaddon.Addon(ADDON_ID)


def _localize(string_id: int, fallback: str) -> str:
    try:
        text = ADDON.getLocalizedString(string_id)
        return text or fallback
    except Exception:
        return fallback


def _get_keyboard_input(heading: str, default: str = "", hidden: bool = False) -> Optional[str]:
    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()
    if not keyboard.isConfirmed():
        return None
    return keyboard.getText()


def _select_mode() -> Optional[str]:
    dialog = xbmcgui.Dialog()
    options = [
        _localize(30035, "Scan local network"),
        _localize(30036, "Enter connection manually"),
    ]
    choice = dialog.select(_localize(30034, "Server discovery"), options)
    if choice == -1:
        return None
    return "scan" if choice == 0 else "manual"


def _choose_server(servers: Sequence[Sequence[Any]]) -> Optional[Dict[str, Any]]:
    dialog = xbmcgui.Dialog()
    if servers:
        entries = [f"{server[0]}:{server[1]}" for server in servers]
        entries.append(_localize(30036, "Enter connection manually"))
        selection = dialog.select(_localize(30037, "Select MySQL server"), entries)
        if selection == -1:
            return None
        if selection < len(servers):
            host, port = servers[selection]
            return {"host": host, "port": port}
    else:
        dialog.ok(
            _localize(30037, "Select MySQL server"),
            _localize(30038, "No servers were detected. Please enter the connection manually."),
        )
    return {"host": "", "port": 3306}


def _prompt_required_text(heading_id: int, fallback: str, default: str = "", hidden: bool = False) -> Optional[str]:
    heading = _localize(heading_id, fallback)
    dialog = xbmcgui.Dialog()
    while True:
        value = _get_keyboard_input(heading, default, hidden)
        if value is None:
            return None
        value = value.strip()
        if value:
            return value
        dialog.ok(heading, _localize(30043, "This value is required."))


def _normalize_port(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _prompt_port(default: int) -> Optional[int]:
    heading = _localize(30040, "Enter the MySQL server port")
    dialog = xbmcgui.Dialog()
    while True:
        value = _get_keyboard_input(heading, str(default))
        if value is None:
            return None
        value = value.strip()
        if not value:
            value = str(default)
        normalized = _normalize_port(value)
        if normalized is not None:
            return normalized
        dialog.ok(_localize(30025, "Port error"), _localize(30026, "The MySQL port must be a number."))


def _collect_connection_details(mode: str) -> Optional[Dict[str, Any]]:
    dialog = xbmcgui.Dialog()
    last_host = ""
    last_port = 3306
    last_user = ""
    last_password = ""

    while True:
        servers = scan_network() if mode == "scan" else []
        choice = _choose_server(servers)
        if choice is None:
            return None

        host_default = choice.get("host", "") or last_host
        port_default = choice.get("port", 0) or last_port or 3306
        user_default = last_user

        host = _prompt_required_text(30039, "Enter the MySQL server address", host_default)
        if host is None:
            return None

        port = _prompt_port(port_default)
        if port is None:
            return None

        user = _prompt_required_text(30041, "Enter the MySQL username", user_default)
        if user is None:
            return None

        password = _get_keyboard_input(
            _localize(30042, "Enter the MySQL password"),
            last_password,
            hidden=True,
        )
        if password is None:
            return None

        if test_connection(host, port, user, password):
            return {"host": host, "port": port, "user": user, "password": password}

        last_host = host
        last_port = port
        last_user = user
        last_password = password

        retry = dialog.yesno(
            _localize(30029, "Connection failed"),
            _localize(30030, "Unable to connect to the database server. Please verify the details."),
            nolabel=_localize(30062, "Cancel"),
            yeslabel=_localize(30061, "Retry"),
        )
        if not retry:
            return None


def _step_configure_databases(connection: Dict[str, Any]) -> Optional[Dict[str, Optional[Dict[str, Any]]]]:
    dialog = xbmcgui.Dialog()
    versions = get_kodi_db_versions()
    video_default = f"MyVideos{versions.get('MyVideos', '')}".strip()
    music_default = f"MyMusic{versions.get('MyMusic', '')}".strip()

    result: Dict[str, Optional[Dict[str, Any]]] = {"video": None, "music": None}

    video_prompt = _localize(30065, "Store the video library on {host}?").format(host=connection.get("host"))
    if dialog.yesno(
        _localize(30045, "Configure the video library?"),
        video_prompt,
        nolabel=_localize(30068, "Skip"),
        yeslabel=_localize(30069, "Configure"),
    ):
        name = _prompt_required_text(30044, "Video database name", video_default or "MyVideos")
        if name is None:
            return None
        result["video"] = {"database": name.strip()}

    music_prompt = _localize(30066, "Store the music library on {host}?").format(host=connection.get("host"))
    if dialog.yesno(
        _localize(30047, "Configure the music library?"),
        music_prompt,
        nolabel=_localize(30068, "Skip"),
        yeslabel=_localize(30069, "Configure"),
    ):
        name = _prompt_required_text(30046, "Music database name", music_default or "MyMusic")
        if name is None:
            return None
        result["music"] = {"database": name.strip()}

    if not result["video"] and not result["music"]:
        dialog.ok(_localize(30034, "Server discovery"), _localize(30048, "You need to configure at least one library."))
        return None

    return result


def _step_migration_options(video_section: Optional[Dict[str, Any]], music_section: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    dialog = xbmcgui.Dialog()
    options: List[str] = []
    option_keys: List[str] = []

    if video_section:
        options.append(_localize(30050, "Video library"))
        option_keys.append("migrate_video")
    if music_section:
        options.append(_localize(30051, "Music library"))
        option_keys.append("migrate_music")

    migrate_video = False
    migrate_music = False

    if options:
        selections = dialog.multiselect(
            _localize(30049, "Select data to migrate"),
            options,
            preselect=list(range(len(options))),
        )
        if selections is None:
            return None
        migrate_video = any(option_keys[index] == "migrate_video" for index in selections)
        migrate_music = any(option_keys[index] == "migrate_music" for index in selections)

    preference_labels = [
        _localize(30053, "Import watched state"),
        _localize(30054, "Import resume points"),
        _localize(30055, "Clean library after updates"),
    ]
    preference_keys = ["import_watched", "import_resume", "clean_on_start"]

    preference_selection = dialog.multiselect(
        _localize(30052, "Import options"),
        preference_labels,
        preselect=[],
    )
    if preference_selection is None:
        return None

    preferences = {key: False for key in preference_keys}
    for index in preference_selection:
        if 0 <= index < len(preference_keys):
            preferences[preference_keys[index]] = True

    return {
        "migrate_video": migrate_video,
        "migrate_music": migrate_music,
        **preferences,
    }


def _build_database_section(
    connection: Dict[str, Any],
    section: Optional[Dict[str, Any]],
    default_prefix: str,
) -> Optional[Dict[str, Any]]:
    if not section:
        return None
    name = section.get("database") or section.get("name") or default_prefix
    name = str(name).strip()
    if not name:
        return None
    return {
        "type": "mysql",
        "host": connection.get("host"),
        "port": connection.get("port"),
        "user": connection.get("user"),
        "password": connection.get("password"),
        "name": name,
        "database": name,
    }


def _perform_migrations(
    connection: Dict[str, Any],
    video_section: Optional[Dict[str, Any]],
    music_section: Optional[Dict[str, Any]],
    migrate_opts: Dict[str, Any],
) -> bool:
    if migrate_opts.get("migrate_video") and video_section:
        if not migrate_video_library("special://database/MyVideos*.db", connection, video_section):
            return False
    if migrate_opts.get("migrate_music") and music_section:
        if not migrate_music_library("special://database/MyMusic*.db", connection, music_section):
            return False
    return True


def _show_summary(
    connection: Dict[str, Any],
    video_section: Optional[Dict[str, Any]],
    music_section: Optional[Dict[str, Any]],
    advancedsettings_path: str,
) -> None:
    summary_lines = [
        _localize(30058, "Host: {host}:{port}").format(
            host=connection.get("host"),
            port=connection.get("port"),
        )
    ]
    if video_section:
        summary_lines.append(_localize(30059, "Video database: {name}").format(name=video_section.get("name")))
    if music_section:
        summary_lines.append(_localize(30060, "Music database: {name}").format(name=music_section.get("name")))
    summary_lines.append(_localize(30057, "Path to advancedsettings.xml:"))
    summary_lines.append(advancedsettings_path)

    text = "\n".join(filter(None, summary_lines))
    dialog = xbmcgui.Dialog()
    try:
        dialog.textviewer(_localize(30056, "Setup complete"), text)
    except AttributeError:
        dialog.ok(_localize(30056, "Setup complete"), text)


def main() -> None:
    mode = _select_mode()
    if not mode:
        return

    connection = _collect_connection_details(mode)
    if not connection:
        return

    db_sections = _step_configure_databases(connection)
    if not db_sections:
        return

    video_section = _build_database_section(connection, db_sections.get("video"), "MyVideos")
    music_section = _build_database_section(connection, db_sections.get("music"), "MyMusic")

    migrate_opts = _step_migration_options(video_section, music_section)
    if migrate_opts is None:
        return

    if not _perform_migrations(connection, video_section, music_section, migrate_opts):
        return

    advancedsettings_path = write_advancedsettings(video_section, music_section, migrate_opts)
    _show_summary(connection, video_section, music_section, advancedsettings_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    xbmc.log("MySQL Assistant started", xbmc.LOGINFO)
    main()
    xbmc.log("MySQL Assistant finished", xbmc.LOGINFO)
