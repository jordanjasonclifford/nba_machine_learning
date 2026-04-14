import glob
import pandas as pd
import os

# create warehouse folder
os.makedirs("warehouse", exist_ok=True)

# read all team csv files
files = glob.glob("to_games_csvs/*.csv")

team_df = pd.concat(
    [pd.read_csv(f) for f in files],
    ignore_index=True
)

# -----------------------------
# normalize date column
# -----------------------------
team_df["GAME_DATE"] = pd.to_datetime(team_df["GAME_DATE"], errors="coerce")

# -----------------------------
# REMOVE DUPLICATES (IMPORTANT)
# LeagueGameFinder sometimes repeats rows
# each team should appear once per game
# -----------------------------
team_df = team_df.drop_duplicates(subset=["GAME_ID", "TEAM_ID"])

# -----------------------------
# chronological ordering
# -----------------------------
team_df = team_df.sort_values("GAME_DATE").reset_index(drop=True)

# -----------------------------
# save warehouse table
# -----------------------------
out_path = "warehouse/fact_team_game.csv"
team_df.to_csv(out_path, index=False)

print("Team warehouse created.")
print("Rows:", len(team_df))
print("Saved to:", out_path)