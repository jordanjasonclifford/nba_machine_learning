from __future__ import annotations

import random
from math import exp

from flask import Flask, render_template, request

from app.playoffs import PlayoffSimulator
from app.simulator import DEFAULT_SEASON, GameSimulator


app = Flask(__name__)
simulator = GameSimulator()
playoff_simulator = PlayoffSimulator(simulator)

TEAM_THEME = {
    "ATL": {"primary": "#e03a3e", "secondary": "#26282a"},
    "BKN": {"primary": "#000000", "secondary": "#707372"},
    "BOS": {"primary": "#007a33", "secondary": "#ba9653"},
    "CHA": {"primary": "#1d1160", "secondary": "#00788c"},
    "CHI": {"primary": "#ce1141", "secondary": "#000000"},
    "CLE": {"primary": "#860038", "secondary": "#041e42"},
    "DAL": {"primary": "#00538c", "secondary": "#002b5e"},
    "DEN": {"primary": "#0e2240", "secondary": "#fec524"},
    "DET": {"primary": "#c8102e", "secondary": "#1d42ba"},
    "GSW": {"primary": "#1d428a", "secondary": "#ffc72c"},
    "HOU": {"primary": "#ce1141", "secondary": "#000000"},
    "IND": {"primary": "#002d62", "secondary": "#fdbb30"},
    "LAC": {"primary": "#c8102e", "secondary": "#1d428a"},
    "LAL": {"primary": "#552583", "secondary": "#fdb927"},
    "MEM": {"primary": "#5d76a9", "secondary": "#12173f"},
    "MIA": {"primary": "#98002e", "secondary": "#f9a01b"},
    "MIL": {"primary": "#00471b", "secondary": "#eee1c6"},
    "MIN": {"primary": "#0c2340", "secondary": "#78be20"},
    "NOP": {"primary": "#0c2340", "secondary": "#c8102e"},
    "NYK": {"primary": "#006bb6", "secondary": "#f58426"},
    "OKC": {"primary": "#007ac1", "secondary": "#ef3b24"},
    "ORL": {"primary": "#0077c0", "secondary": "#000000"},
    "PHI": {"primary": "#006bb6", "secondary": "#ed174c"},
    "PHX": {"primary": "#1d1160", "secondary": "#e56020"},
    "POR": {"primary": "#e03a3e", "secondary": "#000000"},
    "SAC": {"primary": "#5a2d81", "secondary": "#63727a"},
    "SAS": {"primary": "#000000", "secondary": "#c4ced4"},
    "TOR": {"primary": "#ce1141", "secondary": "#000000"},
    "UTA": {"primary": "#002b5c", "secondary": "#f9a01b"},
    "WAS": {"primary": "#002b5c", "secondary": "#e31837"},
}

TEAM_NAMES = {
    "ATL": "Atlanta Hawks",
    "BKN": "Brooklyn Nets",
    "BOS": "Boston Celtics",
    "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",
    "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks",
    "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors",
    "HOU": "Houston Rockets",
    "IND": "Indiana Pacers",
    "LAC": "LA Clippers",
    "LAL": "Los Angeles Lakers",
    "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",
    "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks",
    "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers",
    "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings",
    "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors",
    "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _regular_season_rows():
    rows = simulator.team[
        (simulator.team["SEASON"] == DEFAULT_SEASON)
        & (simulator.team["SEASON_TYPE"] == "Regular Season")
    ].copy()
    return rows.drop_duplicates(["GAME_ID", "TEAM_ABBREVIATION"])


def team_records():
    regular = _regular_season_rows()
    grouped = regular.groupby("TEAM_ABBREVIATION")
    return {
        team: {
            "wins": int((group["WL"] == "W").sum()),
            "losses": int((group["WL"] == "L").sum()),
        }
        for team, group in grouped
    }


def team_profiles():
    regular = _regular_season_rows().sort_values("GAME_DATE")
    records = team_records()
    profiles = {}
    for team, group in regular.groupby("TEAM_ABBREVIATION"):
        recent = group.tail(10)
        fga = max(float(recent["FGA"].sum()), 1.0)
        possessions = max(float((recent["FGA"] + 0.44 * recent["FTA"] + recent["TOV"]).sum()), 1.0)
        profiles[team] = {
            "abbr": team,
            "name": TEAM_NAMES.get(team, team),
            "record": records.get(team, {"wins": 0, "losses": 0}),
            "recent": float((recent["WL"] == "W").sum()),
            "pace": round(float((recent["FGA"] + 0.44 * recent["FTA"] + recent["TOV"]).mean()), 1),
            "net": round(float(recent["PLUS_MINUS"].mean()), 1),
            "shooting": round(float(((recent["FGM"] + 0.5 * recent["FG3M"]).sum() / fga) * 100), 1),
            "rebounding": round(float(recent["REB"].mean()), 1),
            "turnover": round(float((recent["TOV"].sum() / possessions) * 100), 1),
        }
    return profiles


def prediction_view_model(result):
    if not result:
        return None
    profiles = team_profiles()
    away = result.away_team
    home = result.home_team
    away_score = result.score[away]
    home_score = result.score[home]
    margin = home_score - away_score
    home_prob = round(100 / (1 + exp(-margin / 8)))
    home_prob = max(8, min(92, home_prob))
    away_prob = 100 - home_prob
    winner = home if home_score > away_score else away
    confidence = "High" if abs(margin) >= 15 else "Medium" if abs(margin) >= 7 else "Toss-up"
    return {
        "away": profiles.get(away, {"abbr": away, "name": away, "record": {"wins": 0, "losses": 0}}),
        "home": profiles.get(home, {"abbr": home, "name": home, "record": {"wins": 0, "losses": 0}}),
        "away_prob": away_prob,
        "home_prob": home_prob,
        "winner": winner,
        "confidence": confidence,
        "summary": (
            f"{TEAM_NAMES.get(winner, winner)} grades out ahead in this simulation behind the final "
            f"score margin, recent scoring profile, and possession efficiency indicators."
        ),
    }


def comparison_rows(away_team, home_team):
    profiles = team_profiles()
    away = profiles.get(away_team, {})
    home = profiles.get(home_team, {})
    rows = [
        ("Recent performance", "Wins in last 10 games.", "recent", "higher"),
        ("Pace", "Estimated possessions from recent box-score profile.", "pace", "higher"),
        ("Net rating", "Recent average point differential.", "net", "higher"),
        ("Shooting efficiency", "Recent effective field goal percentage.", "shooting", "higher"),
        ("Rebounding", "Recent rebounds per game.", "rebounding", "higher"),
        ("Turnover rate", "Recent turnovers as a share of possessions.", "turnover", "lower"),
    ]
    output = []
    for label, tip, key, direction in rows:
        away_value = away.get(key, 0)
        home_value = home.get(key, 0)
        low = min(float(away_value), float(home_value), 0)
        high = max(float(away_value), float(home_value), 1)
        span = high - low or 1
        away_pct = round(((float(away_value) - low) / span) * 100)
        home_pct = round(((float(home_value) - low) / span) * 100)
        output.append(
            {
                "label": label,
                "tooltip": tip,
                "away_value": away_value,
                "home_value": home_value,
                "away_pct": away_pct,
                "home_pct": home_pct,
                "edge": away_team
                if (away_value > home_value if direction == "higher" else away_value < home_value)
                else home_team,
            }
        )
    output.append(
        {
            "label": "Head-to-head",
            "tooltip": "Reserved for direct matchup history.",
            "away_value": "TBD",
            "home_value": "TBD",
            "away_pct": 50,
            "home_pct": 50,
            "edge": None,
        }
    )
    return output


def playoff_summary(playoff_result):
    if not playoff_result:
        return None
    biggest_upset = None
    closest = None
    for round_data in playoff_result.rounds:
        for series in round_data["series"]:
            winner_wins = int(series["winner_wins"])
            loser_wins = int(series["loser_wins"])
            spread = winner_wins - loser_wins
            if closest is None or spread < closest["spread"]:
                closest = {"label": f"{series['winner']} over {series['loser']}", "score": f"{winner_wins}-{loser_wins}", "spread": spread}
            if biggest_upset is None and series["winner"] != series["home_court"]:
                biggest_upset = {"label": f"{series['winner']} over {series['home_court']}", "score": f"{winner_wins}-{loser_wins}"}
    return {
        "champion": playoff_result.champion,
        "biggest_upset": biggest_upset or {"label": "No lower home-court upsets", "score": "-"},
        "closest": closest or {"label": "-", "score": "-"},
    }


def playoff_team_options(standings):
    return [
        row["team"]
        for conference in ("West", "East")
        for row in standings[conference]
    ]


@app.route("/", methods=["GET", "POST"])
def index():
    active_tab = request.form.get("tab", request.args.get("tab", "game"))
    default_home = "PHX" if "PHX" in simulator.teams else simulator.teams[0]
    default_away = "DEN" if "DEN" in simulator.teams else simulator.teams[1]
    selected_home = request.form.get("home_team", default_home)
    selected_away = request.form.get("away_team", default_away)
    selected_season = DEFAULT_SEASON
    debug_seed_value = request.form.get("debug_seed", "").strip()
    selected_path_team = request.form.get("highlight_team", request.args.get("highlight_team", "")).strip()
    result = None
    playoff_result = None
    error = None

    if request.method == "POST":
        try:
            if active_tab == "playoffs":
                playoff_seed_value = request.form.get("playoff_seed", "").strip()
                playoff_seed = int(playoff_seed_value) if playoff_seed_value else random.randint(1, 999_999)
                playoff_result = playoff_simulator.simulate_playoffs(seed=playoff_seed)
            else:
                seed = int(debug_seed_value) if debug_seed_value else random.randint(1, 999_999)
                result = simulator.simulate_game(selected_home, selected_away, seed=seed)
        except Exception as exc:
            error = str(exc)

    standings = playoff_simulator.standings()
    playoff_teams = playoff_team_options(standings)
    if selected_path_team not in playoff_teams:
        selected_path_team = ""

    return render_template(
        "index.html",
        active_tab=active_tab,
        teams=simulator.teams,
        standings=standings,
        playoff_teams=playoff_teams,
        selected_home=selected_home,
        selected_away=selected_away,
        selected_season=selected_season,
        debug_seed_value=debug_seed_value,
        team_theme=TEAM_THEME,
        team_names=TEAM_NAMES,
        prediction=prediction_view_model(result),
        comparison_rows=comparison_rows(selected_away, selected_home),
        playoff_summary=playoff_summary(playoff_result),
        selected_path_team=selected_path_team,
        result=result,
        playoff_result=playoff_result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
