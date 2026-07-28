"""Build the player-game warehouse fact table from roster player extracts.

Input:
    2026_Rosters_EOS/**/*.csv

Output:
    warehouse/fact_player_game.csv

Each player CSV contains historical game logs for one player. The combined fact
table powers player event weights for the simulator: scoring share, three-point
share, assist share, rebound share, turnover share, shooting percentages, and
expected minutes.
"""

import glob

import pandas as pd


# Recursively load every player gamelog CSV under the end-of-season roster
# folders. The recursive glob handles the 2026_Rosters_EOS/{TEAM}/ structure.
files = glob.glob("2026_Rosters_EOS/**/*.csv", recursive=True)

# Stack all player logs into one table with one row per player-game.
warehouse_df = pd.concat(
    [pd.read_csv(f) for f in files],
    ignore_index=True
)

# Chronological ordering matters for profiling and notebook checks.
warehouse_df["GAME_DATE"] = pd.to_datetime(warehouse_df["GAME_DATE"])
warehouse_df = warehouse_df.sort_values("GAME_DATE")

warehouse_df.to_csv("warehouse/fact_player_game.csv", index=False)
