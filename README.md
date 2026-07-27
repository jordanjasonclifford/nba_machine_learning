# NBA ML Game Simulator

You thought you'd get a normal README!

But it was me, Collin Gillespie!

<img src="images/collinballin.jpeg" alt="Collin Gillespie" width="420">

## Project Overview

This repository is the machine learning and simulation layer of my NBA project. It uses cleaned warehouse CSVs to power a game predictor, player box-score simulation, play-by-play style game flow, overtime handling, and a playoff simulator.

The goal of this project is to add an ML-focused piece to the broader NBA portfolio project, especially for resume depth: data engineering builds the warehouse, and this repo turns that data into an interactive basketball prediction product.

For more on the data engineering side, including the pipeline and warehouse work behind the CSVs, see:

[jordanjasonclifford/nba_data_engineering](https://github.com/jordanjasonclifford/nba_data_engineering)

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

## Run Locally

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
