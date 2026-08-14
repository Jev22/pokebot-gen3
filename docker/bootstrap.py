"""Container bootstrap helpers for running PokéBot Gen3 headless on a server.

Headless mode requires a profile to already exist and can only reach its web UI
if the profile's `http.yml` enables the server and binds to a reachable address.
Neither can be done through the (GUI-only) profile wizard on a headless box, so
this script does both, idempotently, before the bot starts.

Run from the bot's base directory. Invoked by docker/entrypoint.sh.

    python docker/bootstrap.py <profile> [rom_filename] [web_port] [web_host]
"""

import sys

from modules.profiles import (
    PROFILES_DIRECTORY,
    create_profile,
    profile_directory_exists,
)
from modules.roms import ROMS_DIRECTORY, list_available_roms


def ensure_profile(name: str, rom_filename: str | None) -> None:
    """Create the profile from a ROM in ./roms if it does not exist yet."""
    if profile_directory_exists(name):
        return

    if not rom_filename:
        sys.exit(
            f"Profile '{name}' does not exist and POKEBOT_ROM is not set.\n"
            f"Place a ROM into {ROMS_DIRECTORY} and set POKEBOT_ROM to its file name."
        )

    roms = {rom.file.name: rom for rom in list_available_roms()}
    if rom_filename not in roms:
        available = ", ".join(sorted(roms)) or "(no valid Gen3 ROMs found)"
        sys.exit(
            f"ROM '{rom_filename}' was not found in {ROMS_DIRECTORY}.\n"
            f"Available ROMs: {available}"
        )

    create_profile(name, roms[rom_filename])
    print(f"[bootstrap] Created profile '{name}' from ROM '{rom_filename}'.")


def ensure_web(name: str, port: int, host: str) -> None:
    """Write a per-profile http.yml so the web UI is enabled and reachable.

    Only written if absent, so any manual edits the user makes are preserved.
    """
    config_path = PROFILES_DIRECTORY / name / "http.yml"
    if config_path.exists():
        return

    config_path.write_text(
        "# Written by docker/bootstrap.py so the dashboard is reachable from\n"
        "# outside the container. Edit freely; it will not be overwritten.\n"
        "http_server:\n"
        "  enable: true\n"
        f"  ip: {host}\n"
        f"  port: {port}\n"
    )
    print(f"[bootstrap] Enabled web UI for profile '{name}' on {host}:{port}.")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: bootstrap.py <profile> [rom_filename] [web_port] [web_host]")

    name = sys.argv[1]
    rom_filename = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    port = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 8888
    # Bind to 0.0.0.0 *inside the container* so the published port works. Host-side
    # exposure is controlled by docker-compose's port mapping, not this value.
    host = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else "0.0.0.0"

    ensure_profile(name, rom_filename)
    ensure_web(name, port, host)


if __name__ == "__main__":
    main()
