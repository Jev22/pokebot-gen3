#!/usr/bin/env bash
# Container entrypoint for PokéBot Gen3 (headless + web UI).
#
# Responsibilities:
#   1. Create the profile from POKEBOT_ROM if it does not exist yet.
#   2. Enable the web UI for that profile (unless POKEBOT_ENABLE_WEB=0).
#   3. Launch the bot headless, replacing this shell so signals reach python.
set -euo pipefail

cd /app

PROFILE="${POKEBOT_PROFILE:-default}"
BOT_MODE="${POKEBOT_BOT_MODE:-Manual}"
WEB_PORT="${POKEBOT_WEB_PORT:-8888}"

# --- Bootstrap profile + web config ---------------------------------------
if [ "${POKEBOT_ENABLE_WEB:-1}" = "1" ]; then
    python docker/bootstrap.py "$PROFILE" "${POKEBOT_ROM:-}" "$WEB_PORT"
else
    # Still ensure the profile exists, just don't touch its web config.
    python docker/bootstrap.py "$PROFILE" "${POKEBOT_ROM:-}" "$WEB_PORT" >/dev/null
fi

# --- Assemble launch arguments --------------------------------------------
args=(--headless --profile "$PROFILE" --bot-mode "$BOT_MODE")

# A server usually has no audio device; skip audio unless explicitly enabled
# (sounddevice would otherwise raise on an absent output device).
if [ "${POKEBOT_AUDIO:-0}" != "1" ]; then
    args+=(--no-audio)
fi

# Video is ON by default because the web UI streams the emulator frames.
# Set POKEBOT_NO_VIDEO=1 to save CPU if you don't need the live view.
if [ "${POKEBOT_NO_VIDEO:-0}" = "1" ]; then
    args+=(--no-video)
fi

echo "[entrypoint] Starting PokéBot Gen3 — profile='$PROFILE' mode='$BOT_MODE' web_port=$WEB_PORT"

# shellcheck disable=SC2086  # POKEBOT_EXTRA_ARGS is intentionally word-split.
exec python pokebot.py "${args[@]}" ${POKEBOT_EXTRA_ARGS:-}
