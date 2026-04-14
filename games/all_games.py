import os
import time
import random
import pandas as pd

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
from requests.exceptions import ReadTimeout, ConnectionError

# ---------- config ----------
START_SEASON = 2015
END_SEASON = 2025  # 2025 means 2025-26

OUT_DIR = "to_games_csvs"

# throttling (bounded + readable)
SLEEP_MIN = 0.6
SLEEP_MAX = 1.0

# occasional cooldown to reduce block risk
COOLDOWN_EVERY = 120  # requests
COOLDOWN_SECONDS = 25

MAX_TRIES = 4
REQUEST_TIMEOUT = 60
# ---------------------------

def season_str(year_start: int) -> str:
    """2015 -> '2015-16'"""
    return f"{year_start}-{str(year_start + 1)[-2:]}"

def sleepy():
    """Human-like pacing using bounded randomness."""
    time.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))

def fetch_team_games(team_id: int, season: str, season_type: str) -> pd.DataFrame:
    """
    season_type: 'Regular Season' or 'Playoffs'
    Retries on timeout/connection failures so the script continues running.
    """
    delay = 0.8

    for attempt in range(1, MAX_TRIES + 1):
        try:
            finder = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                season_nullable=season,
                season_type_nullable=season_type,
                timeout=REQUEST_TIMEOUT
            )

            df = finder.get_data_frames()[0]
            df["SEASON"] = season
            df["SEASON_TYPE"] = season_type
            return df

        except (ReadTimeout, ConnectionError, TimeoutError) as e:
            if attempt == MAX_TRIES:
                print(f"Failed after {MAX_TRIES} attempts: team_id={team_id} {season} {season_type} ({e})")
                return pd.DataFrame()

            wait = delay + random.uniform(0.0, 1.5)
            print(f"Retry {attempt}/{MAX_TRIES} after error: {e}. Waiting {wait:.1f}s")
            time.sleep(wait)
            delay *= 2.2

        except Exception as e:
            print(f"Unexpected error for team_id={team_id} {season} {season_type}: {e}")
            return pd.DataFrame()

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    team_list = teams.get_teams()
    total_requests = 0

    for team in team_list:
        team_id = team["id"]
        team_abbr = team["abbreviation"]
        team_name = team.get("full_name", team_abbr)

        out_file = f"{team_abbr.lower()}_games_{START_SEASON}_{END_SEASON+1}.csv"
        out_path = os.path.join(OUT_DIR, out_file)

        # Skip if already extracted
        if os.path.exists(out_path):
            print(f"Skipping {team_abbr} (already exists): {out_path}")
            continue

        print(f"\n===== {team_abbr} ({team_id}) =====")

        team_dfs = []

        for y in range(START_SEASON, END_SEASON + 1):
            season = season_str(y)
            print(f"Pulling {team_abbr} {season}")

            # Regular Season
            reg_df = fetch_team_games(team_id, season, "Regular Season")
            if not reg_df.empty:
                reg_df["TEAM_ABBR"] = team_abbr
                reg_df["TEAM_ID"] = team_id
                reg_df["TEAM_NAME"] = team_name
                team_dfs.append(reg_df)
                print(f"  Regular: {len(reg_df)}")
            else:
                print("  Regular: no data returned")

            total_requests += 1
            sleepy()

            # Playoffs
            po_df = fetch_team_games(team_id, season, "Playoffs")
            if not po_df.empty:
                po_df["TEAM_ABBR"] = team_abbr
                po_df["TEAM_ID"] = team_id
                po_df["TEAM_NAME"] = team_name
                team_dfs.append(po_df)
                print(f"  Playoffs: {len(po_df)}")
            else:
                print("  Playoffs: no data returned")

            total_requests += 1
            sleepy()

            # checkpoint cooldown
            if total_requests % COOLDOWN_EVERY == 0:
                print(f"Cooldown... ({COOLDOWN_SECONDS}s)")
                time.sleep(COOLDOWN_SECONDS)

        if not team_dfs:
            print(f"No data returned for {team_abbr}. Skipping file.")
            continue

        team_combined = pd.concat(team_dfs, ignore_index=True).drop_duplicates()
        team_combined.to_csv(out_path, index=False)

        print(f"Saved {team_abbr}: {out_path} | rows={len(team_combined)}")

    print("\nAll done")
    print(f"Total API requests attempted: {total_requests}")

if __name__ == "__main__":
    main()