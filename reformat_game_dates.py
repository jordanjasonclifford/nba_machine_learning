import os
import pandas as pd

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(BASE_DIR, "to_games_csvs")

for filename in sorted(os.listdir(GAMES_DIR)):
    if not filename.endswith(".csv"):
        continue

    path = os.path.join(GAMES_DIR, filename)
    df = pd.read_csv(path)

    if "GAME_DATE" not in df.columns:
        print(f"{filename}: no GAME_DATE column, skipping")
        continue

    # Parse both MM/DD/YYYY and MM-DD-YYYY (and any other common format)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], errors="coerce").dt.strftime("%#m/%#d/%Y")
    df = df.sort_values("GAME_DATE", key=lambda s: pd.to_datetime(s, errors="coerce")).reset_index(drop=True)

    df.to_csv(path, index=False)
    print(f"{filename}: done ({len(df)} rows)")

print("\nAll done.")
