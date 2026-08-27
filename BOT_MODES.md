# BOT_MODES.md — oversigt over alle bot modes

Dokumentation af de indbyggede bot modes i `modules/modes/` (Pokémon Gen3: R/S/E + FR/LG).
Hver mode beskriver: **hvad** den automatiserer, **hvilke spil** den understøtter, **hvad den
kræver**, og **hvordan** den bruges. Krav er udledt af den faktiske kode (`is_selectable()` +
`assert_*`-kald i `run()`), ikke gætterier.

## Sådan fungerer en mode

En mode er en `BotMode`-subklasse (`modules/modes/_interface.py`) med tre nøgler:
- `name()` — navnet i GUI-dropdownen.
- `is_selectable()` — hurtigt tjek (typisk "står jeg på det rigtige kort?") for om moden vises.
- `run()` — en **generator**, der kaldes én gang pr. frame (`yield` = lad én frame passere).
  Konkrete forudsætninger tjekkes her via `assert_*` og kaster `BotModeError` med en forklaring,
  hvis noget mangler.

**Sådan vælges en mode (tre måder):**
- GUI: vælg i mode-dropdownen.
- Kommandolinje: `python pokebot.py <profil> -m "<mode-navn>"`.
- HTTP-API: `POST http://127.0.0.1:8888/emulator` med `{"bot_mode": "<mode-navn>"}`
  (gyldige navne fås fra `GET /bot_modes`). Se `MONITORING.md`.

**Fælles mønstre:**
- De fleste jagt-modes kræver **Poké Balls** + **plads i party/bokse** (tjekkes ved start og efter
  hver kamp). Shinies og custom-catch-filter-match fanges/udløser skift til manuel.
- **Soft-reset-modes** kræver et **in-game gemt spil** (ikke en save-state) foran target'et — ofte
  gemt på præcis den rigtige tile med korrekt facing.
- Mange RSE-modes kan **auto-registrere en cykel** (Mach/Acro/Bicycle) til Select for hurtigere
  navigation.

---

## Kontinuerlige encounter-jagter (gå / spin / fisk)

### Spin (`SpinMode`, `spin.py`)
- **Gør:** Spinner på ét felt så hurtigt som muligt for at trigge encounters uden at tælle skridt (velegnet til Repel-trick og Safari Zone).
- **Understøtter:** Alle spil (RSE og FRLG).
- **Kræver:** At spilleren står på et felt hvor der er encounters (`map_location.has_encounters` — græs/vand/hule). Poké Balls i tasken og plads til fangst i party/bokse (`assert_player_has_poke_balls` + `assert_boxes_or_party_can_fit_pokemon`), tjekkes både ved start og efter hver kamp. I Safari Zone skiftes automatisk til manuel tilstand hvis Safari Balls kommer under 15.
- **Bruges:** Stå i overworld i en plet græs/vand/hule med encounters og start moden. Bruger White Flute automatisk hvis den er i tasken.

### Acro Bike Bunny Hop (`BunnyHopMode`, `bunny_hop.py`)
- **Gør:** Får spilleren til at hoppe på stedet med Acro Bike for at fremkalde encounters uden at tælle skridt — nyttigt til Safari Zone og repel-trick.
- **Understøtter:** Kun RSE (Ruby/Sapphire/Emerald); ikke tilgængelig i FR/LG.
- **Kræver:** Spilleren skal stå på et kort med encounters (græs/grotte). Ved start kræves Poké Balls i tasken, plads i party eller PC-bokse til at fange, samt at Acro Bike findes i tasken (den registreres automatisk til Select). Efter hver kamp kontrolleres igen for Poké Balls og plads.
- **Bruges:** Stil dig i en encounter-plet (græs/grotte) i overworld og start moden; botten registrerer selv Acro Bike og begynder at bunny-hoppe. Bemærk: bunny-hop giver i snit færre encounters/time end Spin-moden.

### Sweet Scent (`SweetScentMode`, `sweet_scent.py`)
- **Gør:** Bruger field-moven Sweet Scent til automatisk at fremkalde en vild encounter (også brugbar i Safari Zone med dedikerede fange-strategier).
- **Understøtter:** Alle versioner (RSE og FRLG).
- **Kræver:** Spilleren skal stå på et kort med encounters (`map_location.has_encounters`), og en Pokémon i partiet skal kunne bruge Sweet Scent. Der kræves Poké Balls (`assert_player_has_poke_balls`) og plads i party/boks (`assert_boxes_or_party_can_fit_pokemon`) — tjekkes både ved start og efter hver kamp der ikke tabes.
- **Bruges:** Stå i overworld i græs/vand/hule med encounters, hav en Pokémon der kan Sweet Scent samt Poké Balls og plads, og start moden. Kræver ikke gemt spil.

### Fishing (`FishingMode`, `fishing.py`)
- **Gør:** Fisker automatisk med en registreret fiskestang for at fremkalde og fange vand-Pokémon.
- **Understøtter:** RSE og FR/LG (inkl. Safari Zone-strategier, hvor botten skifter til manuel mode hvis Safari Balls falder under 15).
- **Kræver:** Spilleren skal stå og kigge mod en vand-tile (surfbar tile). Ved start kræves Poké Balls og plads i party/PC-bokse, samt mindst én fiskestang (Old/Good/Super Rod) i tasken. Er ingen stang registreret, vælges den automatisk hvis kun én findes, ellers spørges der i en GUI.
- **Bruges:** Registrér en fiskestang (eller lad botten spørge/vælge), stil dig med front mod vand og start moden. Anbefalet: en Pokémon med Sticky Hold/Suction Cups i første party-slot (må gerne være besvimet) for højere bidrate.

### Feebas (`FeebasMode`, `feebas.py`)
- **Gør:** Leder efter Feebas ved systematisk at surfe til og fiske på alle vand-tiles på Route 119; når Feebas findes, bliver botten på den tile og shiny-hunter videre.
- **Understøtter:** Kun RSE (Ruby/Sapphire/Emerald).
- **Kræver:** Spilleren skal være i gang med at surfe (Surfing-flag) på Route 119. Ved start tjekkes for Poké Balls og plads i party/PC-bokse, og der skal være en fiskestang i tasken (ellers fejler moden); har man Old Rod registreres den automatisk til Select. Uden Rain Badge (BADGE08) og en Pokémon der kan Waterfall springes tiles nord for vandfaldet over. Anbefalet (kun advarsel): i Emerald en Pokémon med Sticky Hold/Suction Cups i første party-slot for bedre bidrate.
- **Bruges:** Start med at surfe et vilkårligt sted i vandet på Route 119 og aktivér moden; botten navigerer selv rundt og fisker hver tile op til 3 gange. Kender du allerede Feebas-tilen, så kig mod den før du starter, så begynder botten dér.

### Rock Smash (`RockSmashMode`, `rock_smash.py`)
- **Gør:** Farmer løbende Rock Smash-encounters — Nosepass i Granite Cave og Shuckle i Emeralds Safari Zone — ved at knuse sten på faste ruter og håndtere hver encounter.
- **Understøtter:** Kun RSE (ikke valgbar på FRLG). R/S understøtter kun Granite Cave B2F; Safari Zone-delen findes kun i Emerald.
- **Kræver:** Dynamo-badget (`BADGE03_GET`) så Rock Smash kan bruges udenfor kamp. En party-Pokémon der kan Rock Smash. Plads til fangst i party/bokse. Poké Balls i tasken — i Safari Zone kræves dog mindst 10 Safari Balls. Spilleren skal stå på Granite Cave B2F eller (Emerald) et af Safari Zone-kortene/entréen. **Safari Zone-varianten:** kræver in-game save i Safari Zone-entrébygningen på Route 121, Pokéblock Case i tasken (aktivt + gemt spil), plads til fangst i gemt spil, samt kontanter (≥500₽ pr. entré). **Granite Cave med Repel:** vises en "Use Repel?"-dialog (headless vælger automatisk "No Repel"); vælges Repel kræves save på B2F, Poké Balls/plads/Repel i gemt spil og en lead-Pokémon på niveau 13-16.
- **Bruges:** **Granite Cave uden Repel:** stå på B2F og start moden (vælg "No Repel"). **Granite Cave med Repel:** lead på niveau 13, Repels, evt. White Flute/Vital Spirit-lead, gem in-game på B2F, vælg "Use Repel". **Safari Zone (Emerald):** stå ved Safari Zone-entréen på Route 121 med kontanter og Pokéblock Case, gem in-game, evt. registrér Mach Bike, og start moden.

### Item Steal (`ItemStealMode`, `item_steal.py`)
- **Gør:** Går rundt/spinner for at fremkalde vilde encounters, bruger Thief eller Covet én gang for at stjæle modstanderens holdte item og flygter derefter; encounters uden item flygtes der straks fra. Kører som et Pokécenter-loop, så partiet heales automatisk mellem kampe.
- **Understøtter:** Alle spil (RSE + FRLG). Samme lokationer som Level Grind.
- **Kræver:** At mindst én Pokémon i partiet kan Thief eller Covet (tjekkes i både `is_selectable()` og `run()`). Nuværende tile skal have encounters (højt græs/vand) og kortet skal have et Pokécenter i nærheden (`map_has_pokemon_center_nearby`).
- **Bruges:** Stå på en encounter-tile (græs eller vand) på en understøttet rute med et Pokécenter tilgængeligt til fods, sørg for at have en Pokémon med Thief/Covet, og start mode "Item Steal".

### Level Grind (`LevelGrindMode`, `level_grind.py`)
- **Gør:** Kæmper løbende vilde kampe for at levele Pokémon og healer automatisk på nærmeste Pokécenter, kører videre i et loop. ⚠️ **Lokalt modificeret:** denne fil kører headless og vælger altid hårdkodet "Level-balance"-strategien (roterer altid den laveste Pokémon ind) uden GUI-prompt; ren lead-levelling nås derfor ikke i praksis her.
- **Understøtter:** Alle spil (RSE + FRLG). Kun bestemte ruter med direkte overworld-forbindelse til et Pokécenter (se listen i wikien).
- **Kræver:** Nuværende tile skal have encounters og kortet skal have et Pokécenter i nærheden (`is_selectable()`). Der skal være mindst én ikke-æg Pokémon i partiet.
- **Bruges:** Stå i højt græs (eller vand) på en understøttet rute med gåbar sti til et Pokécenter og start mode "Level Grind (group)". Den vælger automatisk level-balance og kører hands-off.

### EV Train (`EVTrainMode`, `ev_train.py`)
- **Gør:** Kæmper løbende wild encounters for at EV-træne din leder-Pokémon mod en valgt EV-fordeling, healer automatisk på nærmeste Pokémon Center når HP bliver lav, og springer kampe over der ikke giver ønskede EV'er.
- **Understøtter:** RSE og FR/LG, men kun på specifikke ruter med direkte overworld-forbindelse til et Pokémon Center (se listen i wikien). R/S understøttes ikke på ikke-engelske sprog.
- **Kræver:** Spilleren skal stå i højt græs (en tile med encounters) der har et Pokémon Center i nærheden med en gåbar rute. EV-målet vælges i en GUI og skal give mening: samlet ≤ 510, hver stat 0-255 og ikke lavere end lederens nuværende EV'er, og den aktuelle encounter-tabel skal faktisk kunne yde de ønskede EV'er.
- **Bruges:** Stil lederen (party-slot 1) i højt græs med en let overworld-sti til et Pokémon Center, start moden og indtast den ønskede EV-spredning. Er moden ikke valgbar, understøttes ruten ikke.

### Safari (`SafariMode`, `safari.py`)
- **Gør:** Lader dig vælge en bestemt Pokémon at jage i Safari Zone; botten navigerer til det optimale felt og bruger den bedste strategi (spin/surf/fisk) med auto-catch, og re-entrerer eller soft-resetter alt efter kontanter.
- **Understøtter:** RSE (Route 121 Safari Zone) og FRLG (Fuchsia City Safari Zone). Feeder-funktionen virker kun på engelske spil.
- **Kræver:** Et eksisterende in-game save gemt i Safari Zone-entrébygningen — Route 121 (RSE) eller Fuchsia City (FRLG). Plads til fangst i party/bokse (aktivt + gemt spil). Mere end 500₽ for at starte. Mål-afhængige krav: Surf-mål kræver Badge 05 og en Surf-bruger; fiske-mål kræver den relevante fiskestang; Safari Zone Northwest kræver Mach Bike, North kræver Acro Bike. Valgfrit: ≥2 Pokéblocks af samme flavor til feeder; nok Repels til en fuld cyklus.
- **Bruges:** Gem in-game ved Safari Zone-entréen, sørg for kontanter (og evt. Repels/Pokéblocks/rette cykel eller Surf-bruger), start moden, vælg mål-Pokémon og svar på feeder-/Repel-dialogerne.

---

## Soft-reset-jagter (statiske, gaver, startere, exploits)

### Starters (`StartersMode`, `starters.py`)
- **Gør:** Soft-resetter gentagne gange for at finde en shiny starter-Pokémon; efter hvert reset vælges den ønskede starter, og resultatet tjekkes for shiny/CCF.
- **Understøtter:** FRLG (Kanto-startere), RSE Hoenn-startere (Route 101) og Emerald Johto-startere (Birch's Lab). Bemærk: Johto-startere aktiverer midlertidigt `starters`-cheatet, da shininess tjekkes via memhacks.
- **Kræver:** Et eksisterende in-game save. Spillet skal være gemt på det korrekte kort/felt: FRLG = i Oaks lab foran en starter-bold; RSE Hoenn = gemt på Route 101 vendt mod starter-tasken (felt (7,14)); RSE Johto = gemt i Birch's Lab foran en starter-bold. Johto kræver desuden mindst ét tomt party-slot.
- **Bruges:** Stå foran den ønskede starter-bold/-taske, gem in-game, start Starters-moden og vælg starter (eller "Random"). Kører til shiny eller manuel.

### Static Soft Resets (`StaticSoftResetsMode`, `static_soft_resets.py`)
- **Gør:** Soft-resetter mod statiske Pokémon, der bare kræver A-spam til kampen starter (ingen ekstra menu-navigation), og tjekker for shiny ved kampstart.
- **Understøtter:** RSE og FRLG (versionsafhængig liste, fx Kanto-legendariske/Hypno i FRLG; Deoxys/Regis/Rayquaza/Lugia i Emerald; Groudon/Kyogre/Kecleon/Lati i R/S).
- **Kræver:** Et gemt spil, gemt netop på target-tilen med korrekt facing (`assert_saved_on_map`, `facing=True`). Condition-baserede targets (fx Hypno/Kecleon) må ikke allerede være mødt. Poké Balls og plads — begge tjekkes i det gemte spil.
- **Bruges:** Stå foran den statiske Pokémon, gem in-game præcis på tilen, og start moden. Sporer RNG for unikke frames (kan blive langsommere over tid; ny TID eller `random_soft_reset_rng`-cheat afhjælper).

### Static Gift Resets (`StaticGiftResetsMode`, `static_gift_resets.py`)
- **Gør:** Soft-resetter for statiske gave-Pokémon, som lægges direkte i partiet uden kamp (fossiler, Eevee, Hitmons, Lapras, Magikarp, Togepi, Castform, Beldum, Wynaut osv.), indtil en shiny/target rammes.
- **Understøtter:** Både RSE og FRLG (nogle encounters er versionsspecifikke).
- **Kræver:** Spilleren skal kigge på NPC'en/tilen, der giver gaven, og target'et skal ligge på det gemte kort. Et gemt spil + mindst én ledig party-plads i det gemte spil. Ekstra pr. target: Wynaut kræver registreret Mach Bike + ubrugt Lavaridge-æg; Togepi kræver registreret Bicycle, ubrugt æg og party-slot 1 med max friendship; fossiler kræver at fossilet er afleveret, rummet forladt/genbesøgt og gemt bagefter.
- **Bruges:** Stå foran gavekilden, sørg for ledig party-plads og eventuelle registrerede items/friendship-krav, gem in-game, og start moden. Æg-baserede targets klækkes ved at cykle frem og tilbage.

### Static Run Away (`StaticRunAway`, `static_run_away.py`)
- **Gør:** Jager stationære legendariske Pokémon ved at gå hen til dem, starte kampen og flygte/genindlæse kortet så de respawner, i stedet for at soft-resette (hurtigere).
- **Understøtter:** Emerald (Lugia, Ho-Oh, Regi-trio, Lati@s, Kyogre, Groudon, Rayquaza, Mew) og FRLG (kun Lugia og Ho-Oh på Navel Rock). Ikke Ruby/Sapphire.
- **Kræver:** Spilleren skal være på et af de tilladte legendariske kort. Target'et må ikke allerede være fanget/besejret (event-flag-tjek). Poké Balls og plads i party/boks.
- **Bruges:** Stå ved den ønskede legendariske og start moden. Kræver ikke gemt spil på tilen. **Vigtigt:** sæt `pickup: false` i `battle.yml`. Lati@s kræver at den anden roamer først er fanget; Mew kræver venstre tile udenfor skoven på Faraway Island.

### Sudowoodo (`SudowoodoMode`, `sudowoodo.py`)
- **Gør:** Soft-resetter mod den statiske Sudowoodo ved Battle Frontier ved at bruge det registrerede item (Wailmer Pail) og tjekke for shiny ved kampstart.
- **Understøtter:** Kun Emerald.
- **Kræver:** Spilleren skal kigge på Sudowoodo-tilen (Battle Frontier Outside East, (54, 62)). Et gemt spil på præcis den tile med korrekt facing, samt Wailmer Pail registreret til Select. Poké Balls og plads (tjekkes i gemt spil).
- **Bruges:** Registrér Wailmer Pail på Select, stå foran Sudowoodo, gem in-game på tilen, og start moden.

### Game Corner (`GameCornerMode`, `game_corner.py`)
- **Gør:** Soft-resetter gentagne gange for at købe en Pokémon fra præmiedisken i Celadon Game Corner (art vælges via menu) og logger gave-Pokémonen, så man kan lede efter shiny.
- **Understøtter:** Kun FRLG. FireRed: Abra, Clefairy, Dratini, Scyther, Porygon; LeafGreen: Abra, Clefairy, Pinsir, Dratini, Porygon.
- **Kræver:** Et gemt spil, hvor spilleren står i Celadon Game Corner-præmierummet på tile (4,3) vendt mod disken. Mindst én ledig party-plads. Nok mønter i det gemte spil.
- **Bruges:** Stå foran NPC'en i præmierummet (tile 4,3), gem in-game, vælg mode "Game Corner" og vælg art i menuen.

### Kecleon (`KecleonMode`, `kecleon.py`)
- **Gør:** Bruger Selfdestruct/Explosion på den usynlige Kecleon vest for Fortree City (Route 119), taber med vilje og whiter ud for at soft-nulstille på jagt efter shiny; navigerer tilbage efter whiteout.
- **Understøtter:** Kun Emerald (i R/S forsvinder Kecleon efter whiteout).
- **Kræver:** Poké Balls, plads i party/bokse, en Pokémon med Selfdestruct eller Explosion (med PP). Devon Scope modtaget (`RECEIVED_DEVON_SCOPE`). Denne Kecleon må ikke allerede være mødt. Seneste heal-lokation skal være Fortree City. Præcis én Pokémon i partiet. Valgfrit: registreret Acro/Mach Bike til hurtigere navigation.
- **Bruges:** Start moden stående på Route 119 vendt mod den usynlige Kecleon på tile (31,6), med kun én Pokémon (der kan Selfdestruct/Explosion) og Fortree City som seneste heal-punkt.

### Nugget Bridge (`NuggetBridgeMode`, `nugget_bridge.py`)
- **Gør:** Udnytter en script-fejl: taber gentagne gange med vilje til Rocket-træneren for enden af Nugget Bridge og whiter ud for uendelige Nuggets (₽5.000/stk.); healer via Cerulean Citys Pokécenter.
- **Understøtter:** Kun FRLG; kun engelske og japanske ROMs (fejlen er patchet i andre sprog).
- **Kræver:** Nugget endnu ikke modtaget (`HIDE_NUGGET_BRIDGE_ROCKET` må ikke være sat). Præcis én Pokémon i partiet, level ≤ 6 (medmindre Magikarp), så man taber. Al ens penge tabes ved hver whiteout.
- **Bruges:** Start moden uden for Cerulean City Pokécenter eller på Route 24, med én lav-level Pokémon. Loopet kører automatisk.

---

## Roamers

### Roamer (Re-Encounter) (`RoamerReencounterMode`, `roamer_reencounter.py`)
- **Gør:** Løber rundt på en fast rute (med Repel aktivt for at undgå andre encounters), indtil den støder ind i den omstrejfende Pokémon igen efter den er flygtet fra kamp, og skifter så til manuel tilstand.
- **Understøtter:** Alle RSE- og FRLG-spil. Roamer er Latios/Latias (RSE) hhv. Raikou/Entei/Suicune (FRLG).
- **Kræver:** En aktiv roamer (`get_roamer()` ≠ None). Spilleren skal stå på et tilladt kort: RSE = Route 110, Slateport City eller Slateport Battle Tent Lobby (Emerald) / Slateport-huset (R/S); FRLG = Route 1, Pallet Town eller rivalens hus. Første ikke-besvimede Pokémon skal have niveau 14-40 (RSE) / 6-50 (FRLG). Poké Balls, plads i party/bokse, og mindst én Repel. Valgfrit: Mach Bike (RSE)/Bicycle (FRLG) auto-registreres; en lead med Illuminate/Arena Trap gør ruten kortere.
- **Bruges:** Sørg for at roameren strejfer om (er flygtet fra kamp), stå på et tilladt kort med korrekt lead-niveau, Repel og Poké Balls, og start moden. Ingen in-game save kræves.

### Roamer (Reset) (`RoamerResetMode`, `roamer_reset.py`)
- **Gør:** Soft-resetter gentagne gange og kører til roameren for at finde en shiny udgave; ved shiny/CCF-match håndteres encounteren, ellers resettes der igen.
- **Understøtter:** Alle RSE- og FRLG-spil (Latios/Latias på RSE, Raikou/Entei/Suicune på FRLG).
- **Kræver:** Et gemt spil på det korrekte startkort: FRLG = One Island Pokémon Center 1F; Emerald = øverste etage af spillerens hus (kræver event-var `LITTLEROOT_HOUSES_STATE_MAY == 3`); R/S = nederste etage af spillerens hus. Første ikke-besvimede Pokémon ≤ roamer-niveau (40 RSE / 50 FRLG) og over højeste encounter-niveau (så Repel virker). En Fly-bruger i party. Poké Balls og plads (aktivt + gemt spil). Mindst én Repel i gemt spil. FRLG: Sapphire i tasken, ikke afleveret til Celio. R/S: TV'et blinker (`SYS_TV_LATI`) efter Elite Four. Valgfrit: Illuminate (RSE/FRLG) / Arena Trap (Emerald) lead giver ~18% speedup.
- **Bruges:** Forbered party (Fly-bruger, korrekt lead-niveau forrest, Repels) FØR de spilspecifikke point-of-no-return, gem in-game på det rette kort og start moden. På Emerald/R/S vælges Latios eller Latias.

---

## Avl, minigames & puzzles

### Daycare (`DaycareMode`, `daycare.py`)
- **Gør:** Cykler/løber frem og tilbage foran Daycare for at klække æg, henter automatisk nye æg (op til fem) og frigiver ikke-shiny klækkede Pokémon i Daycare-PC'en.
- **Understøtter:** RSE (Route 117) og FR/LG (Four Island).
- **Kræver:** Spilleren skal være i overworld på Route 117 (R/S/E) eller Four Island (FR/LG). Der skal stå et kompatibelt avlspar i Daycare (fejler ved inkompatibilitet). Anbefalet (ikke krævet): i Emerald en Pokémon med Flame Body/Magma Armor for hurtigere klækning, samt en cykel — moden auto-registrerer Mach/Acro/Bicycle, henter endda Mach Bike i Mauville hvis nødvendigt, og advarer hvis cyklen mangler.
- **Bruges:** Stå på Route 117 (R/S/E) eller Four Island (FR/LG) med et kompatibelt par i Daycare og start moden.

### Berry Blend (`BerryBlendMode`, `berry_blend.py`)
- **Gør:** Spiller Berry Blender-minigamet automatisk med 100 % ramme-nøjagtighed for at fremstille Pokéblocks.
- **Understøtter:** Kun RSE. Både japansk og internationale sprogversioner.
- **Kræver:** Spilleren skal stå og kigge direkte på et bemandet Berry Blender-bord (1-3 NPC'er) — i Emerald i Lilycove Contest Lobby, i R/S også i Battle Tent-lobbyerne (Fallarbor/Slateport/Verdanturf). Desuden Pokéblock Case i tasken (ikke fuld, <40 stk.) og mindst ét bær.
- **Bruges:** Stil dig foran et bemandet bord og start moden; vælg bær i pop op-vinduet. Slå gerne "L=A" til for flere hits i hurtig rækkefølge.

### Puzzle Solver (`PuzzleSolverMode`, `puzzle_solver.py`)
- **Gør:** Navigerer automatisk gennem og løser et af flere gåde-/kort-forløb afhængigt af hvor spilleren står: Mirage Tower, Sky Pillar, Sealed Chamber, Regirock/Regice/Registeel, Seafloor Cavern, Deoxys (Birth Island), Tanoby Key og Glass Workshop-askeindsamling (til White Flute).
- **Understøtter:** RSE og FRLG afhængigt af gåden. Vælges kun hvis man står på et understøttet gåde-kort.
- **Kræver:** Afhænger af gåden (asserts i `run()`): Mirage Tower (Mach Bike + Rock Smash); Sky Pillar (Mach Bike + Repel); Sealed Chamber (Dig, Dive, Surf + Wailord/Relicanth i yderslots); Regirock (Rock Smash/Strength + badge); Registeel (Flash/Fly + badge); Regice (kræver Sealed Chamber-start løst); Seafloor Cavern (Strength, Rock Smash, Surf + kamp-stærkt party); Deoxys (Aurora Ticket); Tanoby Key (Strength); Glass Workshop (Soot Sack, samler 1000 aske). Flere bruger og gen-anvender Repel automatisk.
- **Bruges:** Stå på/ved det relevante gåde-kort med de nødvendige moves/items opfyldt og start mode "Puzzle Solver" — den registrerer selv hvilken gåde der skal løses ud fra dit kort.
