"""
extract_unmatched.py

Reads unmatched_players.txt, cleans names, finds player IDs using both
the static list and the CommonAllPlayers endpoint (catches recent rookies
not yet in the static snapshot), then runs the full extract pipeline.

Saves CSVs to 2026_Rosters_EOS/{TEAM}/ — same convention as batch_extract_rosters.py.
Rewrites unmatched_players.txt with only players that still couldn't be resolved.
"""

import os
import re
import time
import random
import unicodedata
import pandas as pd

from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import playergamelog, commonallplayers

# ---------- paths ----------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROSTER_DIR = os.path.join(BASE_DIR, "2026_Rosters_EOS")
UNMATCHED  = os.path.join(BASE_DIR, "unmatched_players.txt")

# ---------- seasons ----------
MIN_YEAR = 2025
MAX_YEAR = 2025
SEASONS  = [f"{y}-{str(y+1)[2:]}" for y in range(MIN_YEAR, MAX_YEAR + 1)]
SEASON_TYPES = ["Regular Season", "Playoffs"]

# ---------- rate limiting ----------
BASE_SLEEP     = 4.0
JITTER         = 0.6
COOLDOWN_EVERY = 100
COOLDOWN_SECS  = 50
MAX_TRIES      = 3

_req_count = 0

def _rate_limit():
    global _req_count
    _req_count += 1
    time.sleep(BASE_SLEEP + random.random() * JITTER)
    if _req_count % COOLDOWN_EVERY == 0:
        print(f"  [cooldown] {COOLDOWN_SECS}s after {_req_count} requests...")
        time.sleep(COOLDOWN_SECS)


# ------------------------------------------------------------------ #
#  Name cleaning
# ------------------------------------------------------------------ #

def clean_name(raw: str) -> str:
    name = re.sub(r"\*+", "", raw)           # remove *****
    name = re.sub(r"\b20\d{2}\b", "", name)  # remove draft year e.g. 2025
    name = re.sub(r"\d+$", "", name)         # remove jersey number
    return name.strip()

def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# ------------------------------------------------------------------ #
#  Player lookup — static list first, CommonAllPlayers fallback
# ------------------------------------------------------------------ #

_static_pool = None
_common_pool = None

def _get_static_pool():
    global _static_pool
    if _static_pool is None:
        _static_pool = nba_players.get_players()
    return _static_pool

def _get_common_pool():
    global _common_pool
    if _common_pool is None:
        print("  [lookup] fetching CommonAllPlayers (current season)...")
        _rate_limit()
        cap = commonallplayers.CommonAllPlayers(
            is_only_current_season=1,
            league_id="00",
            season="2025-26",
        )
        df = cap.get_data_frames()[0]
        _common_pool = [
            {"id": int(row["PERSON_ID"]), "full_name": row["DISPLAY_FIRST_LAST"]}
            for _, row in df.iterrows()
        ]
    return _common_pool

def _search_pool(pool: list, name: str) -> dict | None:
    lower         = name.lower()
    lower_stripped = strip_accents(lower)
    parts         = lower_stripped.split()

    # exact
    for p in pool:
        if p["full_name"].lower() == lower:
            return p
    # exact accent-stripped
    for p in pool:
        if strip_accents(p["full_name"].lower()) == lower_stripped:
            return p
    # all parts present (accent-stripped)
    matches = [p for p in pool if all(pt in strip_accents(p["full_name"].lower()) for pt in parts)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        active = [p for p in matches if p.get("is_active", True)]
        if len(active) == 1:
            return active[0]
        print(f"    [ambiguous] {[p['full_name'] for p in matches]}")
        return None
    # last name only
    last = parts[-1]
    last_matches = [p for p in pool if strip_accents(p["full_name"].lower()).endswith(last)]
    if len(last_matches) == 1:
        return last_matches[0]

    return None

def find_player(name: str) -> dict | None:
    # 1. try static list
    result = _search_pool(_get_static_pool(), name)
    if result:
        return result
    # 2. fall back to CommonAllPlayers (catches recent rookies)
    result = _search_pool(_get_common_pool(), name)
    return result


# ------------------------------------------------------------------ #
#  Gamelog extraction
# ------------------------------------------------------------------ #

def fetch_season(player_id, season: str, season_type: str) -> pd.DataFrame:
    delay = 2
    for attempt in range(1, MAX_TRIES + 1):
        try:
            _rate_limit()
            gl = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star=season_type,
            )
            return gl.get_data_frames()[0]
        except Exception as e:
            if "Expecting value: line 1 column 1" in str(e):
                return pd.DataFrame()
            if attempt == MAX_TRIES:
                print(f"    [fail] {season} {season_type}: {e}")
                return pd.DataFrame()
            print(f"    [retry {attempt}/{MAX_TRIES}] {season} {season_type}: {e}")
            time.sleep(delay)
            delay *= 3

def extract_player(player_id, player_name: str) -> pd.DataFrame:
    frames = []
    for season in SEASONS:
        for season_type in SEASON_TYPES:
            if season == "2025-26" and season_type == "Playoffs":
                continue
            df = fetch_season(player_id, season, season_type)
            if df is not None and not df.empty:
                df["SEASON"]      = season
                df["SEASON_TYPE"] = season_type
                df["PLAYER_ID"]   = str(player_id)
                df["PLAYER_NAME"] = player_name
                frames.append(df)
                print(f"    {season} [{season_type}]: {len(df)} games")
            else:
                print(f"    {season} [{season_type}]: (no games)")
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    if "GAME_DATE" in combined.columns:
        combined["_dt"] = pd.to_datetime(combined["GAME_DATE"], errors="coerce")
        combined = combined.sort_values("_dt").drop(columns=["_dt"])
    return combined

def output_path(player_name: str, team: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "", player_name.lower().replace(" ", "_"))
    return os.path.join(ROSTER_DIR, team, f"{safe}_gamelogs_2015_2026.csv")


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    if not os.path.exists(UNMATCHED):
        print("unmatched_players.txt not found.")
        return

    with open(UNMATCHED, encoding="utf-8") as f:
        raw_lines = [l.strip() for l in f if l.strip()]

    entries = []
    for line in raw_lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            entries.append((parts[0].strip(), parts[1].strip()))

    print(f"{len(entries)} players to attempt\n")
    still_unmatched = []

    for i, (team, raw_name) in enumerate(entries, 1):
        name = clean_name(raw_name)
        print(f"[{i}/{len(entries)}] {raw_name!r} -> {name!r}  ({team})")

        out = output_path(name, team)
        if os.path.exists(out):
            print(f"  skip (CSV exists)")
            continue

        info = find_player(name)
        if not info:
            print(f"  [unmatched] could not resolve")
            still_unmatched.append(f"{team}\t{raw_name}")
            continue

        pid       = info["id"]
        full_name = info["full_name"]
        print(f"  -> {full_name}  (ID {pid})")

        out_canonical = output_path(full_name, team)
        if os.path.exists(out_canonical):
            print(f"  skip (CSV exists under canonical name)")
            continue

        try:
            df = extract_player(pid, full_name)
            if df.empty:
                print(f"  [skip] no gamelog data — likely too few NBA games to record")
            else:
                df.to_csv(out, index=False)
                print(f"  saved {len(df)} rows -> {out}")
        except Exception as e:
            print(f"  [error] {e}")
            still_unmatched.append(f"{team}\t{raw_name}")

    with open(UNMATCHED, "w", encoding="utf-8") as f:
        for line in still_unmatched:
            f.write(line + "\n")

    print(f"\nDone. {len(still_unmatched)} still unresolved -> {UNMATCHED}")


if __name__ == "__main__":
    main()
