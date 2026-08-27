# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PokéBot Gen3 is a shiny-hunting bot for Pokémon Ruby, Sapphire, Emerald, FireRed and
LeafGreen. It drives `libmgba` (bundled mGBA core + Python bindings in `mgba/`) frame-by-frame,
reading and writing game memory to play the game as if a human were at the controls. The design
philosophy (see `Readme.md`) is to act like a human player rather than to cheat with RNG
manipulation — e.g. wait for a sprite to render before soft-resetting instead of reading the
result one frame early.

## Commands

Run the bot (auto-checks/installs Python deps via `requirements.py` on startup):

```bash
python pokebot.py                      # opens profile-selection GUI
python pokebot.py <profile> -m Spin    # start a profile directly in a bot mode
python pokebot.py <profile> -hl        # headless (no GUI, console only)
```

Common flags: `-s <speed>` (0 = unthrottled), `-nv`/`-na` (no video/audio), `-d` (debug menu +
breakpoints on error). Full list in `pokebot.py:parse_arguments`.

Tests (run from repo root; require dumped ROMs — see below):

```bash
python -m unittest discover -s tests                                    # all
python -m unittest tests.test_mode_spin                                 # one file
python -m unittest tests.test_mode_spin.TestModeSpin.test_it_catches_shinies  # one test
```

Formatting: **black with `--line-length 120`** (enforced by `.github/workflows/lint.yml`).

Python 3.11–3.13 supported (3.13 recommended).

## ROMs and profiles (required to run, not committed)

- **ROMs** go in `roms/` (git-ignored). Tests need exact SHA1 matches for English Emerald,
  Ruby Rev.2, and FireRed Rev.1 — hashes in `tests/README.md`.
- **Profiles** live in `profiles/<name>/` (git-ignored). Each profile holds a save state and
  per-profile YAML config that overrides the global config. On first run, `context.py`
  copies missing config files from `modules/config/templates/` into `profiles/` — edit the
  copies, not the templates (templates are overwritten on update).

## Architecture

**Frame-driven generator loop.** `modules/main.py:main_loop()` runs one iteration per emulated
frame. The core mechanism is a **controller stack** of Python generators (`context.controller_stack`):
each frame it calls `next()` on the top generator, which does a bit of work and `yield`s to
advance exactly one frame. Bot modes and helper routines are written as generator functions —
`yield` means "let one frame pass, then resume here." When a generator raises `StopIteration`
it is popped off the stack.

**Global context singleton.** `modules/context.py` exposes `context` (import as
`from modules.context import context`), the single source of truth for the emulator handle,
current profile/ROM, config, stats, active bot mode, and the controller/listener stacks. Almost
every module reaches into `context`.

**Bot modes** (`modules/modes/`) are the selectable behaviors (Spin, Starters, Fishing,
RockSmash, etc.). Each subclasses `BotMode` (`modules/modes/_interface.py`):
- `name()` — label shown in the GUI dropdown.
- `is_selectable()` — cheap sanity check (right map?) for whether to show the mode.
- `run()` — a **generator** containing the actual per-frame logic.
Register a new mode by adding it to the list in `modules/modes/__init__.py:get_bot_modes()`.
`ManualBotMode` (in `main.py`) is the default and just yields.

**Bot listeners** (`modules/modes/_listeners.py`, assembled in `get_bot_listeners()`) run every
frame regardless of mode, watching for cross-cutting events (a battle starting, an egg hatching,
a trainer approaching, whiteout, poison). They can interrupt the current mode by pushing their
own generator onto the controller stack.

**Battle strategies** (`modules/battle_strategies/`) decide what to do inside a battle
(catch, run, level up, steal item) independently of the bot mode that triggered the encounter.

**Memory access.** `modules/memory.py`, `modules/pokemon.py`, `modules/game.py`, `modules/map*.py`
etc. read/parse structured game state from emulator memory. Game-version differences are handled
via decompiled symbol tables and per-game data in `modules/data/`. Check `context.rom` (e.g.
`context.rom.is_emerald`) to branch on game version.

**Plugins** (`modules/plugins.py`, `modules/plugin_interface.py`). External plugins in `plugins/`
(git-ignored) can add bot modes/listeners and hook lifecycle events without modifying core code
(which gets replaced on update). User plugins load early in `pokebot.py`; built-in plugins
(`modules/built_in_plugins/`) load lazily in `main_loop` once the profile config is known.

**Web/API.** Optional HTTP server (`modules/web/http.py`) runs in a separate thread when enabled
in config. Because the emulator must only be touched from the main thread, the HTTP thread
schedules work onto `main.py:work_queue`, drained at the top of each frame.

> **Monitoring a running bot:** see `MONITORING.md` for how to inspect the live bot (profile
> `Server`, HTTP API on `:8888`) — all endpoints for checking Pokémon/party/stats, the `.pk3`
> catch-accounting (`★` = shiny), and the `catch_baseline.json` used to track new catches.
> Note: encounters only advance when `bot_mode != "Manual"`.

**GUI.** `modules/gui/` (tkinter) for the normal desktop UI; `modules/gui/headless.py` for the
`-hl` console mode. Both are handed `main_loop` and invoke it as the emulation driver.

## Testing notes

Tests subclass `BotTestCase` (`tests/utility.py`) and load `.ss1` save states from
`tests/states/<game>/`. Two rules from `tests/README.md` that matter when adding tests:
- Import anything from `modules/` **inside** the test method, not at module top level — the test
  runner must install its mocks before `modules` is imported.
- Import test helpers as `from tests.utility import ...` (not `from utility import ...`).
Decorate tests with `@with_save_state(...)` (a list runs the test once per state) and
`@with_frame_timeout(...)`.
