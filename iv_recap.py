#!/usr/bin/env python3
"""IV-recap over fangede Pokémon (.pk3-filer).

Læser per-stat IV'er direkte ud af de dekrypterede .pk3-filer i en profil-mappe
(Misc-substruktur, IV-dword på byte 72) og rapporterer:
  - hver fangsts 6 IV'er + antal perfekte (31)
  - nature og hvilken stat den hæver/sænker (+10% / -10%)
  - en heuristisk kvalitets-vurdering til team-brug

Brug:
    python3 iv_recap.py [profil-mappe] [--json] [--min-perfect N] [--species NAME]
Standard profil-mappe: profiles/Server/pokemon
"""
import glob, os, struct, re, json, sys

STATS = ["HP", "Atk", "Def", "SpA", "SpD", "Spe"]

# Nature -> (hævet stat, sænket stat). Neutrale natures har None.
NATURES = {
    "Hardy": (None, None), "Docile": (None, None), "Bashful": (None, None),
    "Quirky": (None, None), "Serious": (None, None),
    "Lonely": ("Atk", "Def"), "Brave": ("Atk", "Spe"), "Adamant": ("Atk", "SpA"),
    "Naughty": ("Atk", "SpD"), "Bold": ("Def", "Atk"), "Relaxed": ("Def", "Spe"),
    "Impish": ("Def", "SpA"), "Lax": ("Def", "SpD"), "Timid": ("Spe", "Atk"),
    "Hasty": ("Spe", "Def"), "Jolly": ("Spe", "SpA"), "Naive": ("Spe", "SpD"),
    "Modest": ("SpA", "Atk"), "Mild": ("SpA", "Def"), "Quiet": ("SpA", "Spe"),
    "Rash": ("SpA", "SpD"), "Calm": ("SpD", "Atk"), "Gentle": ("SpD", "Def"),
    "Sassy": ("SpD", "Spe"), "Careful": ("SpD", "SpA"),
}


def read_ivs(data: bytes):
    v = struct.unpack_from("<I", data, 72)[0]
    return {
        "HP": v & 31, "Atk": (v >> 5) & 31, "Def": (v >> 10) & 31,
        "Spe": (v >> 15) & 31, "SpA": (v >> 20) & 31, "SpD": (v >> 25) & 31,
    }


def analyse(path: str):
    data = open(path, "rb").read()
    ivs = read_ivs(data)
    name = os.path.basename(path)
    shiny = "★" in name
    m = re.search(r"- ([A-Za-z]+) \[", name)
    nature = m.group(1) if m else "?"
    up, down = NATURES.get(nature, (None, None))
    perfect = [s for s in STATS if ivs[s] == 31]
    flaws = [(s, ivs[s]) for s in STATS if ivs[s] < 31]
    # Heuristik: en -nature på en stat man alligevel ikke vil have perfekt er godt;
    # en imperfekt IV i den sænkede stat er "gratis" (skader ikke en typisk build).
    wasted_down = down in perfect  # perfekt IV i en sænket stat = spildt potentiale
    free_flaw = down is not None and any(s == down for s, _ in flaws)
    species_m = re.search(r"\d+ (?:★ )?- ([A-Za-z']+) -", name)
    species = species_m.group(1) if species_m else "?"
    return {
        "file": name, "species": species, "shiny": shiny, "nature": nature,
        "nature_up": up, "nature_down": down, "ivs": ivs,
        "perfect_count": len(perfect), "perfect_stats": perfect,
        "flaws": flaws, "sum": sum(ivs.values()),
        "wasted_down_nature": wasted_down, "flaw_in_down_stat": free_flaw,
    }


def quality_tag(a):
    n = a["perfect_count"]
    if n == 6:
        return "🌟 flawless (6×31)"
    if n == 5:
        return "⭐ 5×31" + (" — fejl i sænket stat = gratis" if a["flaw_in_down_stat"] else "")
    if n == 4:
        eff = " — effektivt 5×31 (fejl i sænket stat)" if a["flaw_in_down_stat"] else ""
        return f"4×31{eff}"
    return f"{n}×31"


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    group_mode = "--group" in args
    args = [a for a in args if a not in ("--json", "--group")]
    min_perfect = 0
    species_filter = None
    positional = []
    i = 0
    while i < len(args):
        if args[i] == "--min-perfect":
            min_perfect = int(args[i + 1]); i += 2
        elif args[i] == "--species":
            species_filter = args[i + 1].lower(); i += 2
        else:
            positional.append(args[i]); i += 1
    folder = positional[0] if positional else "profiles/Server/pokemon"

    files = sorted(glob.glob(os.path.join(folder, "*.pk3")))
    rows = [analyse(f) for f in files]
    rows = [r for r in rows if r["perfect_count"] >= min_perfect]
    if species_filter:
        rows = [r for r in rows if r["species"].lower() == species_filter]

    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if group_mode:
        from collections import Counter
        shiny = Counter(r["species"] for r in rows if r["shiny"])
        ivonly = Counter(r["species"] for r in rows if not r["shiny"])
        notable = [r for r in rows if r["shiny"] and r["perfect_count"] >= 3]
        print("Shinies (grupperet):", ", ".join(f"{n}× {s} ★" for s, n in shiny.most_common()) or "ingen")
        print("IV-fangster (4×31): ", ", ".join(f"{n}× {s}" for s, n in ivonly.most_common()) or "ingen")
        print(f"Nævneværdige shinies (≥3×31): {len(notable)}")
        for r in notable:
            iv = r["ivs"]
            print(f"  {r['species']} ★ {r['nature']}: " + "/".join(str(iv[s]) for s in STATS) + f" ({r['perfect_count']}×31)")
        return

    shiny_n = sum(r["shiny"] for r in rows)
    print(f"{len(rows)} fangster ({shiny_n} shiny / {len(rows)-shiny_n} IV-only) i {folder}\n")
    header = f"{'Art':12} {'S':1} {'Nature':8} " + " ".join(f"{s:>3}" for s in STATS) + "  31s  vurdering"
    print(header); print("-" * len(header))
    for r in sorted(rows, key=lambda x: (-x["perfect_count"], x["species"])):
        iv = r["ivs"]
        cells = " ".join(f"{iv[s]:>3}" for s in STATS)
        star = "★" if r["shiny"] else " "
        nat = r["nature"]
        if r["nature_down"]:
            nat = f"{nat}"
        print(f"{r['species']:12} {star} {nat:8} {cells}  {r['perfect_count']:>2}   {quality_tag(r)}")


if __name__ == "__main__":
    main()
