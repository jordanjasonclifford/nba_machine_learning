"""
batch_extract_rosters.py

Reads every 2026_Rosters_EOS/{TEAM}/roster.txt, resolves each player's
nba_api ID, checks which seasons they were actually active (2015-16 onward),
and extracts per-game logs into to_players_csvs/.

No data prior to 2015-16 is ever fetched.
Skips players whose CSV already exists in to_players_csvs/.
Writes unresolved names to unmatched_players.txt for manual review.
"""

import os
import re
import time
import random
import pandas as pd

from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import playergamelog

# ---------- paths ----------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ROSTER_DIR  = os.path.join(BASE_DIR, "2026_Rosters_EOS")
UNMATCHED   = os.path.join(BASE_DIR, "unmatched_players.txt")

# ---------- season range ----------
MIN_YEAR = 2015   # 2015-16
MAX_YEAR = 2025   # 2025-26

# ---------- rate limiting (mirrors extract_player.py) ----------
BASE_SLEEP      = 4.0
JITTER          = 0.6
COOLDOWN_EVERY  = 100
COOLDOWN_SECS   = 50
MAX_TRIES       = 3

_req_count = 0

def _rate_limit():
    global _req_count
    _req_count += 1
    time.sleep(BASE_SLEEP + random.random() * JITTER)
    if _req_count % COOLDOWN_EVERY == 0:
        print(f"  [cooldown] sleeping {COOLDOWN_SECS}s after {_req_count} requests...")
        time.sleep(COOLDOWN_SECS)


# ------------------------------------------------------------------ #
#  Roster parsing
# ------------------------------------------------------------------ #

def parse_roster(filepath: str) -> list[str]:
    """
    Return a list of cleaned player names from a roster.txt file.
    Each player line looks like:  Name+JerseyNum<TAB>POS<TAB>...
    Some players have no jersey number appended.
    """
    names = []
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  [warn] Could not read {filepath}: {e}")
        return names

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("http"):          # ESPN headshot URL
            continue
        if line.startswith("Name\t"):        # header row
            continue

        parts = line.split("\t")
        if len(parts) < 2:                   # need at least name + position
            continue

        raw_name = parts[0]
        # Strip trailing jersey number (handles "0", "00", "23", etc.)
        name = re.sub(r"\d+$", "", raw_name).strip()
        if name:
            names.append(name)

    return names


# ------------------------------------------------------------------ #
#  Player ID lookup
# ------------------------------------------------------------------ #

_player_cache: list[dict] | None = None

def _all_players() -> list[dict]:
    global _player_cache
    if _player_cache is None:
        _player_cache = nba_players.get_players()
    return _player_cache


def find_player(name: str) -> dict | None:
    """
    Resolve a display name to an nba_api player dict.
    Strategy:
      1. Exact full_name match (case-insensitive)
      2. All name parts present in full_name (handles middle names / initials)
      3. Last-name-only match when unique
    """
    pool = _all_players()
    lower = name.lower()

    # 1. exact
    for p in pool:
        if p["full_name"].lower() == lower:
            return p

    # 2. all parts present
    parts = lower.split()
    matches = [p for p in pool if all(pt in p["full_name"].lower() for pt in parts)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # prefer active player if ambiguous
        active = [p for p in matches if p.get("is_active")]
        if len(active) == 1:
            return active[0]
        # still ambiguous — return None so it goes to unmatched
        print(f"  [ambiguous] '{name}' matched {[p['full_name'] for p in matches]}")
        return None

    # 3. last name only (unique)
    last = parts[-1]
    last_matches = [p for p in pool if p["full_name"].lower().endswith(last)]
    if len(last_matches) == 1:
        return last_matches[0]

    return None


# ------------------------------------------------------------------ #
#  Active season detection
# ------------------------------------------------------------------ #

def _season_str(year: int) -> str:
    """2015 -> '2015-16'"""
    return f"{year}-{str(year + 1)[2:]}"


def get_active_seasons() -> list[str]:
    """Return all seasons in range. Empty seasons return no data and get skipped automatically."""
    return [_season_str(y) for y in range(MIN_YEAR, MAX_YEAR + 1)]


# ------------------------------------------------------------------ #
#  Gamelog extraction  (mirrors extract_player.py logic)
# ------------------------------------------------------------------ #

SEASON_TYPES = ["Regular Season", "Playoffs"]


def fetch_season(player_id: int | str, season: str, season_type: str) -> pd.DataFrame:
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
            if attempt == MAX_TRIES:
                print(f"    [fail] {season} {season_type} after {MAX_TRIES} tries: {e}")
                return pd.DataFrame()
            print(f"    [retry {attempt}/{MAX_TRIES}] {season} {season_type}: {e}")
            time.sleep(delay)
            delay *= 3


def extract_player(player_id: int | str, player_name: str, seasons: list[str]) -> pd.DataFrame:
    frames = []
    for season in seasons:
        for season_type in SEASON_TYPES:
            if season == "2025-26" and season_type == "Playoffs":
                print(f"    {season} [Playoffs]: (skipped — not yet played)")
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


# ------------------------------------------------------------------ #
#  Output filename  (same convention as extract_player.py)
# ------------------------------------------------------------------ #

def output_path(player_name: str, team: str) -> str:
    safe = re.sub(r"[^a-z0-9_]", "", player_name.lower().replace(" ", "_"))
    return os.path.join(ROSTER_DIR, team, f"{safe}_gamelogs_2015_2026.csv")


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    os.makedirs(ROSTER_DIR, exist_ok=True)

    # --- discover available teams ---
    available = sorted(
        t for t in os.listdir(ROSTER_DIR)
        if os.path.isfile(os.path.join(ROSTER_DIR, t, "roster.txt"))
    )

    print("Available teams:")
    for idx, t in enumerate(available, 1):
        print(f"  {idx:2}. {t}")
    print()

    raw = input("Enter team abbreviation (e.g. ATL) or number: ").strip().upper()

    if raw.isdigit():
        choice = int(raw)
        if not (1 <= choice <= len(available)):
            print(f"Invalid number. Pick 1-{len(available)}.")
            return
        selected_team = available[choice - 1]
    elif raw in available:
        selected_team = raw
    else:
        print(f"'{raw}' not found. Valid teams: {', '.join(available)}")
        return

    print(f"\nRunning: {selected_team}\n")

    # --- load only the selected team's roster ---
    roster_path = os.path.join(ROSTER_DIR, selected_team, "roster.txt")
    names = parse_roster(roster_path)
    print(f"{selected_team}: {len(names)} players\n")

    # display_name -> team (single team, no dedup needed)
    player_teams: dict[str, str] = {n: selected_team for n in names}

    total = len(player_teams)
    unmatched = []
    failed    = []

    for i, (name, team) in enumerate(player_teams.items(), 1):
        # --- skip check #1: roster display name ---
        out = output_path(name, team)
        if os.path.exists(out):
            print(f"[{i}/{total}] skip  {name}  (CSV exists)")
            continue

        print(f"[{i}/{total}] {name}  ({team})")

        try:
            info = find_player(name)
            if not info:
                print(f"  [unmatched] could not resolve '{name}'")
                unmatched.append(f"{team}\t{name}")
                continue

            pid       = info["id"]
            full_name = info["full_name"]
            print(f"  -> {full_name}  (ID {pid})")

            # --- skip check #2: canonical nba_api name (catches manual extractions) ---
            out_canonical = output_path(full_name, team)
            if os.path.exists(out_canonical):
                print(f"  skip  (CSV already exists as canonical name)")
                continue

            seasons = get_active_seasons()
            if not seasons:
                print(f"  [skip] no qualifying seasons for {full_name}")
                continue
            print(f"  seasons: {seasons}")

            df = extract_player(pid, full_name, seasons)

            if df.empty:
                print(f"  [skip] no gamelog data returned for {full_name}")
            else:
                df.to_csv(out, index=False)
                print(f"  saved {len(df)} rows -> {out}")

        except Exception as e:
            print(f"  [error] {name}: {e}")
            failed.append(f"{team}\t{name}\t{e}")
            continue

    # --- summary ---
    print(f"\n--- {selected_team} done ---")
    if unmatched:
        with open(UNMATCHED, "a", encoding="utf-8") as f:
            for line in unmatched:
                f.write(line + "\n")
        print(f"{len(unmatched)} unmatched players appended to {UNMATCHED}")

    if failed:
        failed_path = os.path.join(BASE_DIR, "failed_players.txt")
        with open(failed_path, "a", encoding="utf-8") as f:
            for line in failed:
                f.write(line + "\n")
        print(f"{len(failed)} failed players appended to failed_players.txt")

    if not unmatched and not failed:
        print("All players extracted successfully.")


if __name__ == "__main__":
    main()
