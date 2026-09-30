"""kiban.alamone.net's game pages by MAME set -> data/kiban_games.json, for linking each core's games.

kiban is where the readings are shown next to prices, repairs and the rest of a game's page, and
its MiSTer section links here; this closes the loop so a reader can go from a core to the game.
kiban publishes the mapping (/api/games/rom-map: every set, clones included, to the page covering
its family) and this step saves a copy into the repository, so a report build is reproducible and
never depends on kiban being reachable. Refresh it with `python -m fva kiban`.
"""
import json
import os
import urllib.request

from .paths import REPO

URL = "https://kiban.alamone.net/api/games/rom-map"
OUT = os.path.join(REPO, "data", "kiban_games.json")
GAME_URL = "https://kiban.alamone.net/games/{slug}"


def refresh():
    req = urllib.request.Request(URL, headers={"User-Agent": "fpga-verified-against"})
    games = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))["games"]
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"source": URL, "games": dict(sorted(games.items()))}, f, ensure_ascii=False, indent=0)
        f.write("\n")
    print(f"kiban: {len(games)} sets -> {OUT}")


def load():
    """{setname: [slug, name_en, name_ja]}, or {} when the file has not been fetched."""
    if not os.path.exists(OUT):
        return {}
    with open(OUT, encoding="utf-8") as f:
        return json.load(f)["games"]
