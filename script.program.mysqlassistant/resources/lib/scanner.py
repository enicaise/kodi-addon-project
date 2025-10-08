"""Network discovery helpers for MySQL Assistant."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

try:
    import mysql.connector  # type: ignore
except ImportError:  # pragma: no cover - optional dependency inside Kodi
    mysql = None  # type: ignore

ProgressCallback = Callable[[int, int, str, int], bool]
DEFAULT_PORTS: Tuple[int, int] = (3306, 3307)


def scan_network(
    timeout: float = 1.0,
    ports: Sequence[int] = DEFAULT_PORTS,
    progress_cb: Optional[ProgressCallback] = None,
) -> List[Tuple[str, int]]:
    """Scan the local /24 subnet for reachable MySQL/MariaDB servers."""
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        subnet = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
    except Exception as exc:
        logging.error("Invalid local network: %s", exc)
        return []

    hosts: List[str] = [str(ip) for ip in subnet.hosts()]
    ports_to_check: Tuple[int, ...] = tuple(dict.fromkeys(int(port) for port in ports if port))
    total_targets = max(1, len(hosts) * max(1, len(ports_to_check)))
    checked = 0
    discovered: List[Tuple[str, int]] = []

    for host in hosts:
        for port in ports_to_check:
            checked += 1
            if progress_cb and progress_cb(checked, total_targets, host, port):
                return discovered
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    discovered.append((host, port))
            except Exception:
                continue
    return discovered


def test_connection(
    host: str,
    port: int,
    user: str,
    password: str,
    database: Optional[str] = None,
) -> bool:
    """Validate connectivity to the server using either mysql.connector or sockets."""
    if mysql:
        try:
            conn_params = {"host": host, "port": port, "user": user, "password": password}
            if database:
                conn_params["database"] = database
            conn = mysql.connector.connect(**conn_params)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as exc:  # pragma: no cover - connector feedback from Kodi
            logging.error("MySQL authentication failed: %s", exc)
            return False

    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception as exc:
        logging.error("Socket reachability test failed: %s", exc)
        return False


