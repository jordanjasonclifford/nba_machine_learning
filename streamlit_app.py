from __future__ import annotations

import random
from math import exp

import pandas as pd
import streamlit as st

from app.playoffs import PlayoffSimulator
from app.simulator import DEFAULT_SEASON, GameSimulator, SimulationResult


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


@st.cache_resource(show_spinner="Loading NBA simulation data...")
def load_simulators() -> tuple[GameSimulator, PlayoffSimulator]:
    game_simulator = GameSimulator()
    return game_simulator, PlayoffSimulator(game_simulator)


def regular_season_rows(simulator: GameSimulator) -> pd.DataFrame:
    rows = simulator.team[
        (simulator.team["SEASON"] == DEFAULT_SEASON)
        & (simulator.team["SEASON_TYPE"] == "Regular Season")
    ].copy()
    return rows.drop_duplicates(["GAME_ID", "TEAM_ABBREVIATION"])


@st.cache_data(show_spinner=False)
def team_records(team_rows: pd.DataFrame) -> dict[str, dict[str, int]]:
    grouped = team_rows.groupby("TEAM_ABBREVIATION")
    return {
        team: {
            "wins": int((group["WL"] == "W").sum()),
            "losses": int((group["WL"] == "L").sum()),
        }
        for team, group in grouped
    }


def winner_from_result(result: SimulationResult) -> str:
    return result.home_team if result.score[result.home_team] > result.score[result.away_team] else result.away_team


def win_probability(result: SimulationResult) -> tuple[int, int]:
    margin = result.score[result.home_team] - result.score[result.away_team]
    home_prob = round(100 / (1 + exp(-margin / 8)))
    home_prob = max(8, min(92, home_prob))
    return 100 - home_prob, home_prob


def display_game_result(result: SimulationResult, records: dict[str, dict[str, int]]) -> None:
    away = result.away_team
    home = result.home_team
    winner = winner_from_result(result)
    away_prob, home_prob = win_probability(result)
    margin = abs(result.score[home] - result.score[away])
    confidence = "High" if margin >= 15 else "Medium" if margin >= 7 else "Toss-up"

    st.subheader(f"{TEAM_NAMES.get(away, away)} at {TEAM_NAMES.get(home, home)}")
    score_cols = st.columns([1, 1, 1])
    with score_cols[0]:
        away_record = records.get(away, {"wins": 0, "losses": 0})
        st.metric(away, result.score[away], f"{away_record['wins']}-{away_record['losses']}")
    with score_cols[1]:
        st.metric("Projected Winner", winner, confidence)
    with score_cols[2]:
        home_record = records.get(home, {"wins": 0, "losses": 0})
        st.metric(home, result.score[home], f"{home_record['wins']}-{home_record['losses']}")

    st.progress(away_prob / 100, text=f"{away}: {away_prob}% | {home}: {home_prob}%")
    seed_note = f"Seed {result.seed}"
    if result.overtime_periods:
        seed_note += f" | {result.overtime_periods} OT"
    st.caption(seed_note)

    box_score = pd.DataFrame(result.box_score)
    feed = pd.DataFrame(result.feed)
    box_tab, feed_tab = st.tabs(["Box Score", "Play-By-Play"])
    with box_tab:
        for team in [away, home]:
            st.markdown(f"**{team} Box Score**")
            team_box = box_score[box_score["TEAM"] == team].drop(columns=["TEAM"], errors="ignore")
            st.dataframe(team_box, hide_index=True, use_container_width=True)
    with feed_tab:
        st.dataframe(feed, hide_index=True, use_container_width=True)


def display_standings(standings: dict[str, list[dict[str, object]]]) -> None:
    cols = st.columns(2)
    for col, conference in zip(cols, ["West", "East"], strict=True):
        with col:
            st.markdown(f"**{conference} Seeds**")
            st.dataframe(pd.DataFrame(standings[conference]), hide_index=True, use_container_width=True)


def display_playoff_result(playoff_result) -> None:
    st.subheader(f"Projected NBA Champion: {playoff_result.champion}")
    st.caption(f"Season {playoff_result.season} | Seed {playoff_result.seed}")

    play_in_tab, bracket_tab = st.tabs(["Play-In", "Bracket"])
    with play_in_tab:
        for conference in ["West", "East"]:
            st.markdown(f"**{conference} Play-In**")
            st.dataframe(pd.DataFrame(playoff_result.play_in[conference]), hide_index=True, use_container_width=True)

    with bracket_tab:
        for round_data in playoff_result.rounds:
            is_finals = round_data["name"] == "NBA Finals"
            with st.expander(str(round_data["name"]), expanded=is_finals):
                for series in round_data["series"]:
                    label = (
                        f"{series['team_a']} vs {series['team_b']} - "
                        f"{series['winner']} wins {series['winner_wins']}-{series['loser_wins']}"
                    )
                    st.markdown(f"**{label}**")
                    st.caption(f"Home court: {series['home_court']}")
                    st.dataframe(pd.DataFrame(series["games"]), hide_index=True, use_container_width=True)


def game_tab(simulator: GameSimulator) -> None:
    records = team_records(regular_season_rows(simulator))
    default_home = "PHX" if "PHX" in simulator.teams else simulator.teams[0]
    default_away = "DEN" if "DEN" in simulator.teams else simulator.teams[1]

    away_team, home_team = st.columns(2)
    with away_team:
        selected_away = st.selectbox("Away Team", simulator.teams, index=simulator.teams.index(default_away))
    with home_team:
        selected_home = st.selectbox("Home Team", simulator.teams, index=simulator.teams.index(default_home))

    use_manual_seed = st.toggle("Use manual game seed")
    manual_seed = st.number_input("Game seed", min_value=1, max_value=999_999, value=42, disabled=not use_manual_seed)
    st.caption("Seed is optional. Use the same seed to replay the exact same game result, play-by-play, and box score.")

    if st.button("Simulate Game", type="primary", use_container_width=True):
        seed = int(manual_seed) if use_manual_seed else random.randint(1, 999_999)
        try:
            result = simulator.simulate_game(selected_home, selected_away, seed=seed)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["game_result"] = result

    result = st.session_state.get("game_result")
    if result:
        display_game_result(result, records)
    else:
        st.info("Pick two teams and simulate a single game.")


def playoffs_tab(playoff_simulator: PlayoffSimulator) -> None:
    standings = playoff_simulator.standings()
    display_standings(standings)

    use_manual_seed = st.toggle("Use manual playoff seed")
    manual_seed = st.number_input("Playoff seed", min_value=1, max_value=999_999, value=42, disabled=not use_manual_seed)
    st.caption("Seed is optional. Use the same seed to replay the exact same play-in games, series results, and champion.")

    if st.button("Simulate Playoffs", type="primary", use_container_width=True):
        seed = int(manual_seed) if use_manual_seed else random.randint(1, 999_999)
        try:
            playoff_result = playoff_simulator.simulate_playoffs(seed=seed)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["playoff_result"] = playoff_result

    playoff_result = st.session_state.get("playoff_result")
    if playoff_result:
        display_playoff_result(playoff_result)
    else:
        st.info("Simulate the full postseason from the generated standings and play-in field.")


def main() -> None:
    st.set_page_config(page_title="NBA Game Simulator", page_icon="basketball", layout="wide")
    st.caption("Courtside Modeling")
    st.title("Game Simulator")

    simulator, playoff_simulator = load_simulators()
    game, playoffs = st.tabs(["Game Simulator", "The Road to the Finals"])
    with game:
        st.header("Game Simulator")
        game_tab(simulator)
    with playoffs:
        st.header("The Road to the Finals")
        playoffs_tab(playoff_simulator)


if __name__ == "__main__":
    main()
