# MySQL Assistant for Kodi

MySQL Assistant (`script.program.mysqlassistant`) guides you through configuring Kodi to use a shared MySQL or MariaDB backend for the video and music libraries. The add-on can discover database servers on your network, verify credentials, migrate existing SQLite collections, and generate a Kodi-ready `advancedsettings.xml` file.

## Features
- **Guided setup** – interactive dialogs collect server credentials, database names, and migration preferences.
- **Network discovery** – scan the local subnet for accessible MySQL/MariaDB servers.
- **Validation** – optional inspection of existing Kodi databases to ensure version compatibility.
- **Migration** – copy video and music data from the local SQLite files into the selected MySQL schemas.
- **Configuration generation** – write a standards-compliant `advancedsettings.xml` in the Kodi profile folder.

## Requirements
- Kodi 19 (Matrix) or later with Python 3 support.
- A reachable MySQL or MariaDB server with privileges to create databases and tables.
- One of the Python connectors available inside Kodi's Python environment (`mysql-connector-python` or `PyMySQL`).

## Installation
1. Copy the `script.program.mysqlassistant` directory into your Kodi add-ons folder (e.g. `~/.kodi/addons/`).
2. Ensure the required MySQL connector module is installed for Kodi's Python interpreter.
3. Restart Kodi and enable the add-on from **Add-ons → Program add-ons**.

## Usage
1. Launch *MySQL Assistant* from Kodi's program add-ons.
2. Choose whether to scan the network for MySQL servers or enter connection details manually.
3. Provide the MySQL host, port, user, and password. The assistant validates the connection before proceeding.
4. Select the video and/or music databases to use (the wizard suggests database names based on the running Kodi version).
5. Decide whether to migrate your existing local SQLite data and pick the import options (watched status, resume points, etc.).
6. Review the completion summary. The generated `advancedsettings.xml` is stored in Kodi's profile directory and will take effect on the next Kodi restart.

## Notes
- The assistant creates the MySQL schemas if they do not already exist.
- Migration skips tables that are missing in the MySQL target, allowing you to bootstrap an empty schema first by letting Kodi start once with the new settings.
- The generated `advancedsettings.xml` can be edited manually if you need to customise additional settings beyond the wizard's scope.

## Contributing
Bug reports and pull requests are welcome. Please make sure any new localisation strings are added to each language catalogue.

## Licence
This project is released under the MIT Licence.
