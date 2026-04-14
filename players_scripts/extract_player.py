import os
import time
import random
import pandas as pd

from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players

# ---------- config ----------
# Get the player's ID from 'find_player.py' output
PLAYER_ID = "1629627"  #  For example, Zion Williamson's ID is 1629627. Change this to the desired player's ID.
START_SEASON = "2015-16"
END_SEASON = "2025-26"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "to_players_csvs")
OUT_FILE = f"player_{PLAYER_ID}_gamelogs_2015_2026.csv"

# Rate limiting config (to avoid hitting API limits and getting IP banned)
BASE_SLEEP = 1.0       # safer than 0.6
JITTER = 0.6           # random extra delay
COOLDOWN_EVERY = 120
COOLDOWN_SECONDS = 25
MAX_TRIES = 3
# --------------------------

SEASONS = [
    "2015-16","2016-17","2017-18","2018-19","2019-20",
    "2020-21","2021-22","2022-23","2023-24","2024-25","2025-26"
]

def get_player_name(player_id: str) -> str:
    # quick lookup from nba_api static list
    plist = players.get_players()
    match = next((p for p in plist if str(p["id"]) == str(player_id)), None)
    return match["full_name"] if match else f"Unknown ({player_id})"

def sleepy():
    time.sleep(BASE_SLEEP + random.random() * JITTER)

def fetch_with_retries(player_id: str, season: str, max_tries: int = MAX_TRIES) -> pd.DataFrame:
    delay = 2
    for attempt in range(1, max_tries + 1):
        try:
            gl = playergamelog.PlayerGameLog(player_id=player_id, season=season)
            df = gl.get_data_frames()[0]
            return df
        except Exception as e:
            if attempt == max_tries:
                print(f"  Failed {player_id} {season} after {max_tries} tries: {e}")
                return pd.DataFrame()
            print(f"  Error {player_id} {season} (attempt {attempt}/{max_tries}): {e}")
            time.sleep(delay)
            delay *= 3  # 2s -> 6s -> 18s

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    player_name = get_player_name(PLAYER_ID)
    print(f"Player: {player_name} (ID={PLAYER_ID})")

    # change the naming convention of output for it to be easier to identify the player from the filename
    player_name = get_player_name(PLAYER_ID)
    safe_name = player_name.replace(" ", "_").lower()
    OUT_FILE = f"{safe_name}_gamelogs_2015_2026.csv"

    all_dfs = []
    req_count = 0

    for season in SEASONS:
        print(f"Pulling {season}...")

        df = fetch_with_retries(PLAYER_ID, season)
        req_count += 1

        if df is None or df.empty:
            print("  (no games found)")
        else:
            # *** Keep all endpoint columns + add SEASON column
            df["SEASON"] = season
            # Add easy tracking columns
            df["PLAYER_ID"] = str(PLAYER_ID)
            df["PLAYER_NAME"] = player_name
            all_dfs.append(df)
            print(f"  games: {len(df)}")

        sleepy()

        if req_count % COOLDOWN_EVERY == 0:
            print(f"Cooldown... ({COOLDOWN_SECONDS}s)")
            time.sleep(COOLDOWN_SECONDS)

    if not all_dfs:
        print("No data returned for any season. Check PLAYER_ID / endpoint response.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)

    # --- sort ascending by date (oldest -> newest) ---
    # GAME_DATE in nba_api is usually like 'OCT 25, 2023'
    if "GAME_DATE" in combined_df.columns:
        combined_df["GAME_DATE_DT"] = pd.to_datetime(combined_df["GAME_DATE"], errors="coerce")
        combined_df = combined_df.sort_values("GAME_DATE_DT", ascending=True)
        combined_df = combined_df.drop(columns=["GAME_DATE_DT"])
    else:
        # fallback: sort by SEASON then GAME_ID
        combined_df = combined_df.sort_values(["SEASON", "GAME_ID"], ascending=[True, True])

    out_path = os.path.join(OUT_DIR, OUT_FILE)
    combined_df.to_csv(out_path, index=False)

    print(f"\nDone and saved: {out_path}")
    print(f"Total rows: {len(combined_df)}")

if __name__ == "__main__":
    main()