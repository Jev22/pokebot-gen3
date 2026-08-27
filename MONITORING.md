# MONITORING.md — værktøjer til at tjekke botten & Pokémon

Referencedokument til at aflæse den kørende PokéBot (profil **Server**, Pokémon Emerald)
uden at forstyrre emulatoren. Alt går gennem **HTTP-API'et** — læsning sker via en work-queue
på main-thread, så data er konsistente (aldrig midt-i-frame-skrald).

## Grundlæggende

- **Base URL:** `http://127.0.0.1:8888` (konfigureret i `profiles/http.yml`, `enable: true`, port 8888).
- Bot-processen: `python3 pokebot.py --headless Server` (headless, ingen GUI).
- **VIGTIGT — encounters tælles kun når botten IKKE er i `Manual`:** i manuel tilstand
  kører emulatoren videre (frame_count stiger, fps ~60), men der er ingen bot-mode der
  jager, så `total_encounters` og `encounter_rate` står stille. Tjek altid `bot_mode`
  (via `/emulator`) før du konkluderer at botten "sidder fast".
- Swagger/OpenAPI-dokumentation live på `http://127.0.0.1:8888/docs` (+ rå `/api.json`).

## HTTP-endpoints (GET medmindre andet nævnt)

### Pokémon
| Endpoint | Returnerer |
|---|---|
| `/party` | Fuld liste over Pokémon i holdet (arter, level, IV/EV, moves, HP …). |
| `/opponent` | Nuværende/seneste modstander — **kun** hvis `game_state == BATTLE`, ellers `null`. |
| `/pokemon_storage` | Alle PC-bokse. `?format=size-only` giver kun antal pr. boks. |
| `/pokedex` | Seen/caught-status. |
| `/daycare` | Hvad der er afleveret i Daycare (æg-optælling m.m.). |

### Stats (kilden til shiny/encounter-optælling)
| Endpoint | Returnerer |
|---|---|
| `/stats` | `{"pokemon": {...pr. art...}, "totals": {...}}` — se afsnit nedenfor. |
| `/encounter_rate` | `{"encounter_rate": <enc/time>}` (0 i manuel). |
| `/encounter_log` | Seneste 10 encounters (fuld Pokémon-data). |
| `/shiny_log` | Seneste shiny-**faser** (ikke enkelt-Pokémon) — se struktur nedenfor. |

### Kort / verden
| Endpoint | Returnerer |
|---|---|
| `/map` | Nuværende kort + tile spilleren står på + alle tiles. |
| `/map_encounters` | Wild encounter-tabel (rå + effektiv ift. Repel/lead-level). |
| `/map/{group}/{number}` | Detaljer om et specifikt kort. |
| `/player` | Sjældent-skiftende spillerdata (navn, TID, SID, penge, coins). |
| `/player_avatar` | Position: map bank/ID, X/Y. |
| `/items` | `{"bag": {...}, "storage": [...]}` — bag = rygsæk, storage = PC-items. |

### Spil / emulator
| Endpoint | Returnerer |
|---|---|
| `/game_state` | Fx `"OVERWORLD"`, `"BATTLE"`, `"POKE_STORAGE"`, `"BATTLE_STARTING"`. |
| `/event_flags` | Alle event-flags (`?flag=FLAG_NAME` for én). |
| `/emulator` | `bot_mode`, `current_message`, `emulation_speed`, `frame_count`, `current_fps`, spil/profil. |
| `/bot_modes` | Liste over installerede bot-modes (til gyldige `bot_mode`-værdier). |
| `/fps` | FPS pr. sekund, seneste 60 sek. |
| `/input` | Aktuelt trykkede knapper. |

### Skrivende endpoints (ændrer tilstand — brug med omtanke)
- **`POST /emulator`** — JSON, fx `{"bot_mode": "Spin"}`, `{"emulation_speed": 4}`,
  `{"video_enabled": true}`, `{"audio_enabled": false}`. Gyldige speeds: 0,1,2,3,4,8,16,32
  (0 = ubegrænset). Gyldige modes: se `/bot_modes`. **Sådan tager man botten ud af manuel.**
- **`POST /input`** — JSON-array af knapper, fx `["B","Right"]` eller `[]` for slip alle.
  Virker **kun** når `bot_mode == "Manual"`.

### Streams (Server-Sent Events / video)
- `/stream_events?topic=...` — SSE, abonnér på ét eller flere topics. Topics (fra
  `DataSubscription` i `modules/web/http_stream.py`): `Player, PlayerAvatar, Party, Pokedex,
  Opponent, WildEncounter, FishingAttempt, GameState, Map, MapTile, MapEncounters,
  PokenavCall, BotMode, Message, EmulatorSettings, Inputs, PerformanceData, CustomEvent`.
  Detaljer i `modules/web/docs/event_stream.md`.
- `/stream_video?fps=30` — MJPEG-stream af skærmen. WebRTC via `POST /rtc`.
- `/stream-overlay` — stream-overlay-side.

## `/stats`-strukturen

```
{
  "pokemon": { "<Art>": { total_encounters, shiny_encounters, catches,
                          total_highest_iv_sum, total_lowest_iv_sum,
                          total_highest_sv, total_lowest_sv, phase_*, last_encounter_time } },
  "totals":  { total_encounters, shiny_encounters, catches,
               total_highest_iv_sum:{value,species_name}, ...,
               phase_encounters, phase_highest_iv_sum, ... }
}
```

- `sv` = "shiny value" (0–65535; lavt = shiny/tæt på shiny).
- `phase_*` nulstilles ved hver shiny; `phase_encounters` = encounters siden sidste shiny.

Nyttige one-liners:

```bash
# Totaler
curl -s http://127.0.0.1:8888/stats | python3 -c "import sys,json;print(json.load(sys.stdin)['totals'])"

# bot_mode + game_state (tjek om botten reelt jager)
curl -s http://127.0.0.1:8888/emulator | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['bot_mode'],d['current_fps'],'fps')"
curl -s http://127.0.0.1:8888/game_state
```

## `/shiny_log`-strukturen

Returnerer en liste af **faser** (op til de seneste ~10), ikke enkelt-Pokémon. Hver post har:
- `phase`: fase-id, start/slut, `encounters`, streaks, IV/SV-rekorder for fasen.
- `snapshot`: `total_encounters`, `total_shiny_encounters`, `species_encounters`,
  `species_shiny_encounters` på det tidspunkt.
- `shiny_encounter`: selve shiny-fangsten (`encounter_id`, tid, `matching_custom_catch_filters` …).

## Fangst-recap med IV'er (to fangst-kategorier)

Botten fanger **to slags** Pokémon: **shinies** (★) og **4× perfekte IV'er** (fire stats på 31).
Rapporten skal give en **recap med per-stat IV'er på alle fangster**, fremhæve de nævneværdigt
gode, og vurdere hvordan IV-spreadet passer til team-brug.

**Sådan læses IV'er ud af en `.pk3`-fil (fund):**
- De gemte `.pk3` er i **dekrypteret standard-format** (fra `Pokemon.to_pk3()`), IKKE det interne
  krypterede layout. Derfor kan `modules.pokemon.parse_pokemon()` **ikke** parse dem direkte
  (checksum-tjek fejler → returnerer `None`).
- IV'erne ligger som en uint32 i Misc-substrukturen på **byte 72** (little-endian). Bit-felter:
  `HP 0-4, Atk 5-9, Def 10-14, Spe 15-19, SpA 20-24, SpD 25-29` (bit 30 = egg, 31 = ability).
- Valideret: IV-summen matcher `[..]`-tallet i filnavnet for alle 135 fangster.

**Værktøj:** `python3 iv_recap.py` (i repo-roden) gør dette automatisk og udskriver per fangst:
6 IV'er, antal 31'ere, nature (+ hvilken stat den hæver/sænker), og en heuristisk vurdering.
```bash
python3 iv_recap.py                       # alle fangster, tabel
python3 iv_recap.py --min-perfect 5       # kun nævneværdige (5-6×31)
python3 iv_recap.py --species Seedot      # filtrér på art
python3 iv_recap.py --json                # maskinlæsbart (til rapport-logikken)
```

**Team-egnethed — sådan vurderes en fangst:**
- Tæl 31'ere. **6×31** = 🌟 flawless, **5×31** = ⭐.
- **Nature betyder alt:** en nature sænker én stat 10%. En imperfekt IV i den *sænkede* stat er
  "gratis" (skader ikke en typisk build) → en 4×31 kan reelt være **effektivt 5×31**.
- **Dump-stat-reglen:** en fysisk angriber/væg bruger ikke Sp. Atk (og en special-mon bruger ikke
  Atk). Er fejlen i den ubrugte stat, betyder den intet for den rolle. Nævn det i recap'en:
  "perfekt i alle relevante stats for rollen".
- Fremhæv i rapporten kun de virkelig gode (≥5×31, eller 4×31 hvor begge fejl er i dump/sænket
  stat) med en kort linje om hvilken stat der er svag, og om det matter for et realistisk team.

**Rapport-tilføjelse:** ved en ny fangst medtages linjen
`IVs: HP/Atk/Def/SpA/SpD/Spe (N×31, nature ±) — <team-note hvis nævneværdig>`.
Ved periodisk recap: kør `iv_recap.py` og opsummer nye fangster siden sidste baseline.

## .pk3-filer = den fysiske fangst-optælling

Gemte Pokémon ligger i `profiles/Server/pokemon/*.pk3`. Navneformat:

```
<dex> ★ - <Art> - <Natur> [<IV-sum>] - <PID>.pk3
```

- **`★` i navnet = shiny.** Uden ★ = "IV-fangst" (fanget pga. høj IV-sum, ikke shiny, fx Skarmory).
- Optælling af de to grupper:

```bash
cd /app
total=$(ls profiles/Server/pokemon/*.pk3 | wc -l)
shiny=$(ls profiles/Server/pokemon/*.pk3 | grep -c "★")
echo "pk3 total: $total | shiny: $shiny | IV-fangster: $((total-shiny))"
```

Andre profil-mapper: `profiles/Server/{saves,states,screenshots/{gifs,cards}}`.

## Rapporteringsformat (heartbeat-rutine)

Rekonstrueret fra den oprindelige session (var aldrig committet — gik tabt én gang). Formål:
løbende "bot lever"-rapporter under en shiny-jagt, med detektion af nye fangster.

**Ved hver check:**
1. Læs `/emulator` (bot_mode!), `/game_state`, `/stats` (totals), tæl `.pk3` (shiny vs IV).
2. Sammenlign mod `catch_baseline.json`; opdater baseline bagefter.
3. Tjek `/items` for **Rare Candy** — nævn kun en linje hvis den er i tasken (ellers "no line").

**Ny fangst:**
```
✨ New catch!
<Art> ★ — <Natur> — IV sum <N> — dupe|new
IVs: HP<h>/Atk<a>/Def<d>/SpA<sa>/SpD<sd>/Spe<sp> (<N>×31, nature +<up>/−<down>)<team-note hvis nævneværdig>
Running tally: <S> shinies + <IV> IV-catches (<total> total .pk3). Bot alive — <lokation>,
state=<STATE>, +<delta> encounters since last check (~<rate>/hr).
Still missing: <liste>.
```
(Kategori: ★ = shiny-fangst; ellers 4×31 IV-fangst. Kør `iv_recap.py --json` for tallene.)

**Ingen ændring:**
```
✅ Bot still running — no new catches. <total_enc> encounters (+<delta> since last check),
~<rate>/hr, on <lokation>, state=<STATE>. Still <S> shinies + <IV> IV-catches (<total> .pk3).
Still missing: <liste>.
```

**Kadence & regler:**
- Rapportér ved nye fangster og ellers periodisk (loggen brugte ~hver ~2.400 encounters / løbende).
- **Overnatnings-pause:** ingen heartbeats om natten; genoptag kl. 09:00 (og tidligere kun ved
  en ny fangst værd at flage).
- `state=UNKNOWN` = forbigående læsning → stol på encounter-delta.
- **Encounters står stille i Manual** → så er der intet at rapportere (jagten er sat på pause).

**Nuværende mål (2026-08-27):** find **1 shiny Seedot til** (står på 1/2) før vi går videre.
Route 102, Pokémon Emerald. Ralts-linjen er komplet (3/3). Tidligere også nævnt manglende:
Goldeen (Old Rod).

## Baseline til overvågning

`catch_baseline.json` (repo-roden) holder sidste kendte tal, så nye fangster kan detekteres
mellem heartbeats. Genopbyg fra sandheden når som helst:

```bash
cd /app
curl -s http://127.0.0.1:8888/stats | python3 -c "
import sys,json,subprocess
t=json.load(sys.stdin)['totals']
pk3=subprocess.run('ls profiles/Server/pokemon/*.pk3',shell=True,capture_output=True,text=True).stdout.splitlines()
shiny=sum('★' in f for f in pk3)
json.dump({'total_encounters':t['total_encounters'],'shiny_encounters':t['shiny_encounters'],
           'catches':t['catches'],'pk3_total':len(pk3),'pk3_shiny':shiny,'pk3_iv':len(pk3)-shiny},
          open('catch_baseline.json','w'),indent=2)
print('baseline skrevet')
"
```
