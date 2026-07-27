# NBA ML Notebooks

These notebooks are designed to run locally from this repository using the CSVs in `warehouse/`.

## Notebook Order

1. `01_data_profile.ipynb` checks the two warehouse CSVs and shows the basic data shape.
2. `02_team_game_predictor.ipynb` builds one row per game, creates rolling team features, trains baseline score/winner models, and saves model artifacts.
3. `03_player_event_weights.ipynb` turns player box scores into event weights for shots, threes, assists, rebounds, and turnovers.
4. `04_game_simulator.ipynb` uses team tendencies plus player weights to generate a possession-by-possession game feed with clock times.

## VS Code Setup

From the repo root in a PowerShell terminal:

```powershell
.\venv\Scripts\python.exe -m pip install -r .\notebooks\requirements-notebook.txt
.\venv\Scripts\python.exe -m ipykernel install --user --name nba_ml --display-name "NBA ML"
```

Then:

1. Open this folder in VS Code.
2. Install the VS Code Python and Jupyter extensions if prompted.
3. Open a notebook from the `notebooks/` folder.
4. Click the kernel picker in the top right.
5. Select `NBA ML`.
6. Run cells from top to bottom.

## Local VS Code vs Google Colab

Local VS Code is the better fit for this project right now because your warehouse CSVs already live in this repo. You can read them directly with paths like `../warehouse/fact_team_game.csv`, save model files into `../models/`, and turn notebook code into Python modules later.

Google Colab is useful if you want to share a notebook or run it from another machine, but you would need to upload the CSVs or mount Google Drive every time. For this dataset and baseline models, local CPU is enough.
