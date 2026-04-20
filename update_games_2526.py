"""
update_games_2526.py

Refreshes the 2025-26 season data in every to_games_csvs/{team}_games_2015_2026.csv.
Loads the existing CSV, re-fetches only 2025-26 (Regular Season + Playoffs),
merges, deduplicates on GAME_ID + TEAM_ID, and saves back.
"""

import os
import time
import random
import pandas as pd

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
from requests.exceptions import ReadTimeout, ConnectionError

# ---------- config ----------
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
OUT_DIR   = os.path.join(BASE_DIR, "to_games_csvs")
SEASON    = "2025-26"

SLEEP_MIN      = 0.6
SLEEP_MAX      = 1.0
COOLDOWN_EVERY = 120
COOLDOWN_SECS  = 25
MAX_TRIES      = 4
TIMEOUT        = 60
# ----------------------------

def sleepy():
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

def fetch_team_games(team_id: int, season_type: str) -> pd.DataFrame:
    delay = 0.8
    for attempt in range(1, MAX_TRIES + 1):
        try:
            finder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                season_nullable=SEASON,
                season_type_nullable=season_type,
                timeout=TIMEOUT,
            )
            df = finder.get_data_frames()[0]
            if not df.empty:
                df["SEASON"]      = SEASON
                df["SEASON_TYPE"] = season_type
            return df
        except (ReadTimeout, ConnectionError, TimeoutError) as e:
            if attempt == MAX_TRIES:
                print(f"  [fail] {season_type} after {MAX_TRIES} tries: {e}")
                return pd.DataFrame()
            wait = delay + random.uniform(0.0, 1.5)
            print(f"  [retry {attempt}/{MAX_TRIES}] {e} — waiting {wait:.1f}s")
            time.sleep(wait)
            delay *= 2.2
        except Exception as e:
            print(f"  [error] {season_type}: {e}")
            return pd.DataFrame()

def main():
    team_list     = teams.get_teams()
    total_requests = 0

    for team in team_list:
        team_id   = team["id"]
        team_abbr = team["abbreviation"]
        team_name = team.get("full_name", team_abbr)

        csv_path = os.path.join(OUT_DIR, f"{team_abbr.lower()}_games_2015_2026.csv")

        if not os.path.exists(csv_path):
            print(f"\n{team_abbr}: CSV not found, skipping")
            continue

        print(f"\n{team_abbr} — updating {SEASON}")

        existing = pd.read_csv(csv_path)
        new_frames = [existing]

        for season_type in ["Regular Season"]:  # Playoffs 2025-26 not yet played
            df = fetch_team_games(team_id, season_type)
            total_requests += 1
            sleepy()

            if df is not None and not df.empty:
                df["TEAM_ABBR"] = team_abbr
                df["TEAM_ID"]   = team_id
                df["TEAM_NAME"] = team_name
                new_frames.append(df)
                print(f"  {season_type}: {len(df)} games fetched")
            else:
                print(f"  {season_type}: no data")

            if total_requests % COOLDOWN_EVERY == 0:
                print(f"  [cooldown] {COOLDOWN_SECS}s")
                time.sleep(COOLDOWN_SECS)

        combined = pd.concat(new_frames, ignore_index=True)

        # deduplicate — keep latest fetch for any duplicate GAME_ID + TEAM_ID
        if "GAME_ID" in combined.columns and "TEAM_ID" in combined.columns:
            combined = combined.drop_duplicates(subset=["GAME_ID", "TEAM_ID"], keep="last")

        combined.to_csv(csv_path, index=False)
        print(f"  saved {len(combined)} rows -> {csv_path}")

    print(f"\nAll done. {total_requests} API requests made.")

if __name__ == "__main__":
    main()
