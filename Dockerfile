# PokéBot Gen3 — headless server image
# --------------------------------------
# Runs the bot with no GUI and serves the web UI (modules/web) so you can
# monitor and control it from a browser. Designed for a Linux server / VPS.
#
# Base is Ubuntu 24.04 because the mGBA python binding needs `libmgba.so.0.10`,
# which Ubuntu ships as the `libmgba0.10t64` package (mGBA 0.10.x). Python 3.12
# from the base image is within the bot's supported range (3.11–3.13).
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    TZ=UTC

# System dependencies:
#   libmgba0.10t64 -> provides libmgba.so.0.10 (the core emulator lib the python
#                     binding links against); apt pulls its ffmpeg/lua/png/zip/
#                     sqlite dependencies automatically.
#   libportaudio2  -> required by `sounddevice`, which is imported by
#                     modules/libmgba.py even in headless mode.
#   python3-tk     -> tk runtime; some optional desktop-integration libs import it.
#   curl, unzip    -> fetch + extract the prebuilt mGBA binding at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        tzdata \
        python3 \
        python3-venv \
        python3-pip \
        python3-tk \
        libmgba0.10t64 \
        libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Isolated virtualenv — avoids Ubuntu 24.04's PEP 668 "externally managed"
# restriction and matches how the bot expects to run (inside a venv).
RUN python3 -m venv "$VIRTUAL_ENV" && pip install --upgrade pip

WORKDIR /app

# Prebuilt mGBA python binding. It is not on PyPI; the bot normally downloads it
# on first run. We fetch the same pinned release here so the image is
# self-contained and never needs network access at startup. It extracts to
# ./mgba, a top-level package the bot imports. Keep these ARGs in sync with
# `libmgba_tag` / `libmgba_ver` in requirements.py.
ARG LIBMGBA_TAG=0.2.0-2
ARG LIBMGBA_VER=0.2.0
RUN curl -fsSL -o /tmp/libmgba.zip \
        "https://github.com/hanzi/libmgba-py/releases/download/${LIBMGBA_TAG}/libmgba-py_${LIBMGBA_VER}_ubuntu-lunar.zip" \
    && unzip -q /tmp/libmgba.zip -d /app \
    && rm /tmp/libmgba.zip

# Install python requirements from the project's own source of truth
# (requirements.py) so they never drift from what the bot expects. Only the few
# files this import needs are copied first, keeping this (slow) layer cached
# until the dependency list actually changes.
COPY requirements.py ./requirements.py
COPY modules/runtime.py modules/version.py ./modules/
RUN touch modules/__init__.py \
    && python -c "from requirements import required_modules; print(chr(10).join(required_modules))" \
        > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

# Now copy the rest of the application.
COPY . /app

# Seed `.last-requirements-check` with the current requirements hash so the bot's
# startup check sees everything is already installed and never tries to pip-install
# or re-download the binding at runtime (which would need network / interactive input).
RUN python -c "from requirements import get_requirements_hash; open('.last-requirements-check','w').write(get_requirements_hash())"

# The bot only runs its auto-updater when it does NOT look like a git checkout.
# The updater is interactive (prompts on a new release) and would hang a headless
# container, so we drop an empty `.git` marker to make the bot skip it entirely.
RUN mkdir -p /app/.git

# Runtime data lives under these; declared as volumes and also mounted by
# docker-compose so profiles (saves, stats, config) and ROMs persist on the host.
RUN mkdir -p /app/profiles /app/roms
VOLUME ["/app/profiles", "/app/roms"]

# The web UI port (overridable via POKEBOT_WEB_PORT).
EXPOSE 8888

ENTRYPOINT ["/app/docker/entrypoint.sh"]
