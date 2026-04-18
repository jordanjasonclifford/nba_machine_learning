import os
import pandas as pd

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROSTER_DIR = os.path.join(BASE_DIR, "2026_Rosters_EOS")

grand_total = 0

for team in sorted(os.listdir(ROSTER_DIR)):
    team_dir = os.path.join(ROSTER_DIR, team)
    if not os.path.isdir(team_dir):
        continue

    csvs = [f for f in os.listdir(team_dir) if f.endswith(".csv")]
    if not csvs:
        print(f"{team:4}  —  no CSVs yet")
        continue

    team_rows = 0
    for csv in csvs:
        try:
            df = pd.read_csv(os.path.join(team_dir, csv))
            team_rows += len(df)
        except Exception as e:
            print(f"  [warn] could not read {csv}: {e}")

    grand_total += team_rows
    print(f"{team:4}  {len(csvs):2} players  {team_rows:,} rows")

print(f"\nTOTAL  {grand_total:,} rows across all teams")
