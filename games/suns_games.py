import os
import time
import pandas as pd

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder

# ---------- config ----------
TEAM_ABBR = "PHX"   # Suns
START_SEASON = 2015
END_SEASON = 2025   # 2025 means 2025-26
SLEEP_SECONDS = 0.6
OUT_DIR = "to_csvs"
OUT_FILE = f"suns_games_{START_SEASON}_{END_SEASON+1}.csv"
# ---------------------------

def season_str(year_start: int) -> str:
    """2015 -> '2015-16'"""
    return f"{year_start}-{str(year_start + 1)[-2:]}"

def get_team_id_by_abbr(abbr: str) -> int:
    team_list = teams.get_teams()
    match = next((t for t in team_list if t["abbreviation"] == abbr.upper()), None)
    if not match:
        raise ValueError(f"Could not find team with abbreviation '{abbr}'.")
    return match["id"]

def fetch_team_games(team_id: int, season: str, season_type: str) -> pd.DataFrame:
    """
    season_type: 'Regular Season' or 'Playoffs'
    """
    finder = leaguegamefinder.LeagueGameFinder(
        team_id_nullable=team_id,
        season_nullable=season,
        season_type_nullable=season_type
    )
    df = finder.get_data_frames()[0]
    df["SEASON"] = season
    df["SEASON_TYPE"] = season_type
    return df

def main():
    team_id = get_team_id_by_abbr(TEAM_ABBR)
    print(f"{TEAM_ABBR} team_id = {team_id}")

    all_dfs = []

    for y in range(START_SEASON, END_SEASON + 1):
        season = season_str(y)
        print(f"\nPulling Suns games for {season}...")

        # Regular Season
        reg_df = fetch_team_games(team_id, season, "Regular Season")
        all_dfs.append(reg_df)
        print(f"  Regular Season games: {len(reg_df)}")
        time.sleep(SLEEP_SECONDS)

        # Playoffs
        po_df = fetch_team_games(team_id, season, "Playoffs")
        all_dfs.append(po_df)
        print(f"  Playoffs games: {len(po_df)}")
        time.sleep(SLEEP_SECONDS)

    combined = pd.concat(all_dfs, ignore_index=True)

    # Drop exact duplicates (sometimes endpoints can repeat rows)
    combined = combined.drop_duplicates()

    # Ensure output folder exists
    os.makedirs(OUT_DIR, exist_ok=True)

    out_path = os.path.join(OUT_DIR, OUT_FILE)
    combined.to_csv(out_path, index=False)

    print(f"\nSaved: {out_path}")
    print(f"Total rows: {len(combined)}")

if __name__ == "__main__":
    main()