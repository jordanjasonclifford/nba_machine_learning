import glob
import pandas as pd

files = glob.glob("to_players_csvs/*.csv")

warehouse_df = pd.concat(
    [pd.read_csv(f) for f in files],
    ignore_index=True
)

warehouse_df["GAME_DATE"] = pd.to_datetime(warehouse_df["GAME_DATE"])

warehouse_df = warehouse_df.sort_values("GAME_DATE")

warehouse_df.to_csv("warehouse/fact_player_game.csv", index=False)