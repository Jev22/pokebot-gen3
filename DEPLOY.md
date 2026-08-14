# Deploying PokéBot Gen3 on a server (Docker)

Run the bot headless (no desktop) on a Linux server and monitor/control it from
the built-in web dashboard. This uses Docker + Docker Compose.

The image is based on Ubuntu 24.04 and installs everything the bot needs
(`libmgba0.10t64` for the emulator core, PortAudio, the pinned mGBA python
binding, and the Python requirements from `requirements.py`). Nothing is fetched
at container startup, so it also runs on an air-gapped/offline host once built.

---

## 1. Prerequisites

- A Linux server with **Docker Engine** and the **Docker Compose plugin**:
  ```bash
  docker --version
  docker compose version
  ```
  If missing, install via <https://docs.docker.com/engine/install/> (the
  "Server" instructions for your distro). Not Debian/Ubuntu? Any distro that can
  run Docker works — everything the bot needs lives inside the image, so your
  host distro doesn't matter.
- A **Gen3 ROM** file you legally own (Ruby, Sapphire, Emerald, FireRed or
  LeafGreen). ROMs are never included in the image or the repo.

## 2. Get the code

```bash
git clone https://github.com/40Cakes/pokebot-gen3.git
cd pokebot-gen3
```
(Or copy your existing checkout to the server.)

## 3. Configure

```bash
cp .env.example .env
mkdir -p roms profiles
cp /path/to/your/rom.gba roms/
```

Edit `.env` and set at least:

```ini
POKEBOT_ROM=rom.gba          # exact file name inside ./roms
POKEBOT_PROFILE=default
POKEBOT_BOT_MODE=Manual      # see wiki/pages/Pokemon By Bot Mode.md
```

## 4. Launch

```bash
docker compose up -d --build
docker compose logs -f       # watch it boot; Ctrl-C to stop watching
```

On first start the container:
1. creates the `POKEBOT_PROFILE` profile from `POKEBOT_ROM`,
2. enables the web dashboard for that profile,
3. starts the bot headless.

Common commands:

| Action                | Command                              |
|-----------------------|--------------------------------------|
| Follow logs           | `docker compose logs -f`             |
| Stop                  | `docker compose down`                |
| Restart               | `docker compose restart`             |
| Update image + code   | `git pull && docker compose up -d --build` |
| Shell into container  | `docker compose exec pokebot bash`   |

## 5. Reaching the dashboard (read this — the UI has no login)

**The web UI has no authentication.** Anyone who can reach the port can read your
game data and send inputs to the emulator. By default it is published on
`127.0.0.1:8888` (loopback only), so it is *not* exposed to your network out of
the box. Pick one of these to access it safely:

- **Tailscale (recommended).** With the server on your tailnet:
  - Simplest & most secure — serve it only to your tailnet, still no public
    exposure, and Tailscale adds its own HTTPS + identity:
    ```bash
    tailscale serve --bg 8888
    ```
    Then open the URL `tailscale serve status` prints. Keep `POKEBOT_BIND=127.0.0.1`.
  - Or bind the container's port straight to the server's Tailscale IP by setting
    in `.env`:
    ```ini
    POKEBOT_BIND=100.x.y.z   # this server's Tailscale IP (`tailscale ip -4`)
    ```
    and browse to `http://100.x.y.z:8888` from another tailnet device.
- **SSH tunnel** (no VPN): from your laptop
  ```bash
  ssh -N -L 8888:127.0.0.1:8888 user@your-server
  ```
  then open <http://localhost:8888>.

Do **not** set `POKEBOT_BIND=0.0.0.0` unless the port is already firewalled or
behind an authenticating reverse proxy.

## 6. Where your data lives

Everything persists on the host via bind mounts, so rebuilding the image never
loses progress:

```
./roms/                     your ROM files
./profiles/<name>/          saves, save states, stats.db, screenshots, config
./profiles/<name>/http.yml  web-server config (auto-created; edit as you like)
```

Back up `./profiles/` to back up your bot.

## 7. Environment variables

All optional except `POKEBOT_ROM` on first run. Full list with descriptions is
in [`.env.example`](.env.example). Summary:

| Variable             | Default     | Purpose                                            |
|----------------------|-------------|----------------------------------------------------|
| `POKEBOT_ROM`        | *(unset)*   | ROM file name in `./roms` (first-run profile setup)|
| `POKEBOT_PROFILE`    | `default`   | Profile to run / create                            |
| `POKEBOT_BOT_MODE`   | `Manual`    | Starting bot mode                                  |
| `POKEBOT_BIND`       | `127.0.0.1` | Host interface for the dashboard port              |
| `POKEBOT_WEB_PORT`   | `8888`      | Dashboard port                                     |
| `POKEBOT_ENABLE_WEB` | `1`         | Set `0` to run with no web UI                      |
| `POKEBOT_AUDIO`      | `0`         | Set `1` to enable emulator audio (needs a device)  |
| `POKEBOT_NO_VIDEO`   | `0`         | Set `1` to skip video rendering (saves CPU)        |
| `POKEBOT_EXTRA_ARGS` | *(unset)*   | Extra raw args passed to `pokebot.py`              |

## 8. Managing profiles manually

The container auto-creates the profile named by `POKEBOT_PROFILE`. To create a
second one by hand:

```bash
# List ROMs the bot can see, then create a profile from one:
docker compose run --rm pokebot python docker/bootstrap.py myprofile Emerald.gba
```

To switch which profile runs, change `POKEBOT_PROFILE` in `.env` and
`docker compose up -d`.

## 9. Troubleshooting

- **`Profile '...' does not exist and POKEBOT_ROM is not set`** — put the ROM in
  `./roms` and set `POKEBOT_ROM` to its exact file name.
- **`ROM '...' was not found`** — the file name in `POKEBOT_ROM` doesn't match a
  file in `./roms` (check case/extension); the error lists what was found.
- **Dashboard won't load** — confirm the container is up (`docker compose ps`),
  then that you're connecting via loopback/Tailscale/tunnel as in step 5, not a
  raw public IP.
- **Lowest-latency WebRTC video** — the HTTP video stream works over the normal
  published port. If you specifically want the WebRTC (`/rtc`) path, add
  `network_mode: host` to the service in `docker-compose.yml` (Linux only; then
  the `ports:` mapping is ignored and the bot listens directly on the host).
