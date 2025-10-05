### Structure initiale du projet Kodi Addon: script.program.mysqlassistant

# default.py
# Entry point of the addon, routes actions and starts the wizard UI.

# addon.xml
# Kodi addon manifest, defines metadata and entry script.

# scanner.py
"""
This module discovers available MySQL servers on the local network.
It scans the subnet defined by Kodi's IP and netmask and checks for open port 3306.
Provides a fallback method for manual server entry and credential testing.
Exports:
- scan_network() -> List[Tuple[str, int]]: returns list of discovered servers
- test_connection(host: str, port: int, user: str, password: str) -> bool
"""
import socket
import ipaddress
import logging

try:
    import mysql.connector
except ImportError:
    mysql = None


def scan_network(timeout: float = 1.0) -> list:
    """
    Scans the local network for MySQL servers on port 3306.

    Args:
        timeout: socket timeout in seconds.

    Returns:
        List of (ip, port) tuples for reachable MySQL servers.
    """
    # Determine local network from host IP
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        subnet = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
    except Exception as e:
        logging.error(f"Invalid local network: {e}")
        return []

    servers = []
    for ip in subnet.hosts():
        try:
            with socket.create_connection((str(ip), 3306), timeout=timeout):
                servers.append((str(ip), 3306))
        except Exception:
            continue
    return servers


def test_connection(host: str, port: int, user: str, password: str, database: str = None) -> bool:
    """
    Tests connection to MySQL server with given credentials.
    If mysql.connector is unavailable, falls back to basic socket check.

    Args:
        host: server IP or hostname
        port: server port
        user: username
        password: password
        database: optional database name to connect to

    Returns:
        True if connection and simple query succeed, False otherwise.
    """
    if mysql:
        try:
            conn_params = {'host': host, 'port': port, 'user': user, 'password': password}
            if database:
                conn_params['database'] = database
            conn = mysql.connector.connect(**conn_params)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"MySQL auth failed: {e}")
            return False
    # Fallback: simple socket-based reachability
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception as e:
        logging.error(f"Socket test failed: {e}")
        return False

