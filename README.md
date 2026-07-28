# Courtside Modeling: NBA Machine Learning Simulator

This repository contains the machine learning and simulation layer of my NBA analytics project.

For the data warehouse, ETL pipeline, and Power BI reporting side of the project, start here:

[jordanjasonclifford/nba_data_engineering](https://github.com/jordanjasonclifford/nba_data_engineering)

## Project Overview

Courtside Modeling uses cleaned warehouse CSVs to power an interactive basketball prediction product. It includes a single-game simulator, player box-score simulation, play-by-play style game flow, overtime handling, and a playoff simulator.

The broader project is split into two portfolio pieces: the data engineering repository builds the warehouse and Power BI reporting layer, while this repository turns that modeled data into a machine learning and simulation application.

## What This App Does

- Simulates a single NBA game between two selected teams
- Generates a final score, play-by-play feed, and player box score
- Uses random seeds internally so each simulation can vary
- Keeps debug seed controls hidden in debug sections for reproducible runs
- Runs overtime automatically if regulation ends in a tie
- Simulates the 2025-26 playoff/play-in bracket
- Uses higher regular-season wins to assign home court in playoff series
- Lets users highlight a playoff team's path through the bracket

## Data Notes

This project assumes the 2025-26 season and uses the warehouse CSVs in this repo as the modeling source.

At a high level, the project focuses on players who are officially on the team roster by the end of the 2025-26 season. That means it may not include players who appeared during the season but did not end on the final roster.

Player roles in the simulator are based on observed 2025-26 season participation, not ideal full-strength rotations. The player event weights use games played, total minutes, average minutes, and box-score event shares to approximate who was actually available and involved during the season. As a result, a star player who missed most of the season may receive a smaller simulated role than their real talent level would suggest, because the simulator is reflecting the season data rather than overriding it with live injury or manual availability assumptions.

## Run Locally

From a fresh clone, create and activate a virtual environment, then install the project dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source venv/bin/activate
```

### Streamlit App

For the shareable browser app:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

Then open the local Streamlit URL shown in the terminal. This version includes both the single-game simulator and playoff simulator.

To make it public without requiring anyone to download the project, deploy `streamlit_app.py` from this repo on Streamlit Community Cloud and use `requirements.txt` for dependencies.

### Flask App

From the project root:

```powershell
.\venv\Scripts\Activate.ps1
python -m flask --app app.app run --host 127.0.0.1 --port 5055 --debug
```

Then open:

```text
http://127.0.0.1:5055/
```

If port `5055` is already in use, choose another port:

```powershell
python -m flask --app app.app run --host 127.0.0.1 --port 5060 --debug
```

## Notebooks

The `notebooks/` folder contains the exploratory and modeling workflow:

- Data profiling
- Team game prediction
- Player event weighting
- Game simulation logic

These notebooks can be run locally in VS Code with the project virtual environment selected as the Python/Jupyter kernel.
