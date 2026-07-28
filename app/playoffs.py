from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.simulator import DEFAULT_SEASON, GameSimulator, SimulationResult


CONFERENCES = {
    "ATL": "East",
    "BKN": "East",
    "BOS": "East",
    "CHA": "East",
    "CHI": "East",
    "CLE": "East",
    "DET": "East",
    "IND": "East",
    "MIA": "East",
    "MIL": "East",
    "NYK": "East",
    "ORL": "East",
    "PHI": "East",
    "TOR": "East",
    "WAS": "East",
    "DAL": "West",
    "DEN": "West",
    "GSW": "West",
    "HOU": "West",
    "LAC": "West",
    "LAL": "West",
    "MEM": "West",
    "MIN": "West",
    "NOP": "West",
    "OKC": "West",
    "PHX": "West",
    "POR": "West",
    "SAC": "West",
    "SAS": "West",
    "UTA": "West",
}

PLAY_IN_SEED_OVERRIDES = {
    DEFAULT_SEASON: {
        "West": {
            7: "PHX",
            8: "POR",
            9: "LAC",
            10: "GSW",
        }
    }
}

HOME_COURT_OVERRIDES = {
    DEFAULT_SEASON: {
        # Manual correction for a known data/standings edge case in the 2025-26
        # simulation dataset. The simulator otherwise awards home court by wins.
        frozenset(("ORL", "PHI")): "PHI",
    }
}


@dataclass
class PlayoffResult:
    """Complete postseason simulation output consumed by both web frontends."""

    seed: int
    season: str
    standings: dict[str, list[dict[str, object]]]
    play_in: dict[str, list[dict[str, object]]]
    rounds: list[dict[str, object]]
    bracket: dict[str, dict[str, object]]
    champion: str


class PlayoffSimulator:
    """Build and simulate a full NBA postseason using `GameSimulator`.

    This class does not train a separate playoff model. It creates standings,
    play-in matchups, best-of-seven series, and the NBA Finals, then delegates
    every individual game to `GameSimulator.simulate_game`.
    """

    def __init__(self, simulator: GameSimulator) -> None:
        self.simulator = simulator

    def standings(self) -> dict[str, list[dict[str, object]]]:
        """Create conference seed tables from the regular-season warehouse rows."""
        team = self.simulator.team

        # Each NBA game appears once per team in the fact table, so dedupe on
        # GAME_ID + TEAM_ABBREVIATION before calculating team records.
        regular = team[(team["SEASON"] == DEFAULT_SEASON) & (team["SEASON_TYPE"] == "Regular Season")].copy()
        regular = regular.drop_duplicates(["GAME_ID", "TEAM_ABBREVIATION"])

        # Plus-minus is used only as a simple tie-breaker after wins.
        records = (
            regular.groupby("TEAM_ABBREVIATION")
            .agg(
                wins=("WL", lambda s: int((s == "W").sum())),
                losses=("WL", lambda s: int((s == "L").sum())),
                plus_minus=("PLUS_MINUS", "mean"),
            )
            .reset_index()
            .rename(columns={"TEAM_ABBREVIATION": "team"})
        )
        records["conference"] = records["team"].map(CONFERENCES)
        records = records.dropna(subset=["conference"])
        records = records.sort_values(["conference", "wins", "plus_minus"], ascending=[True, False, False])
        records["seed"] = records.groupby("conference").cumcount() + 1

        output: dict[str, list[dict[str, object]]] = {}
        for conference in ["West", "East"]:
            conf = records[records["conference"] == conference].head(10)
            rows = conf[["seed", "team", "wins", "losses"]].to_dict("records")
            overrides = PLAY_IN_SEED_OVERRIDES.get(DEFAULT_SEASON, {}).get(conference, {})
            if overrides:
                # Overrides let the bracket mirror a desired play-in field when
                # partial or simulated season data produces a different seed order.
                by_team = {str(row["team"]): row for row in rows}
                overridden_teams = set(overrides.values())
                rows = [row for row in rows if str(row["team"]) not in overridden_teams]
                for seed, team in overrides.items():
                    if team in by_team:
                        row = dict(by_team[team])
                        row["seed"] = seed
                        rows.append(row)
                rows = sorted(rows, key=lambda row: int(row["seed"]))
            output[conference] = rows
        return output

    @staticmethod
    def _wins_lookup(standings: dict[str, list[dict[str, object]]]) -> dict[str, int]:
        """Flatten standings into a team -> wins lookup for home-court logic."""
        return {row["team"]: int(row["wins"]) for rows in standings.values() for row in rows}

    @staticmethod
    def _home_court(team_a: str, team_b: str, wins: dict[str, int]) -> str:
        """Choose the home-court team by override first, then regular-season wins."""
        override = HOME_COURT_OVERRIDES.get(DEFAULT_SEASON, {}).get(frozenset((team_a, team_b)))
        if override:
            return override
        if wins.get(team_a, 0) > wins.get(team_b, 0):
            return team_a
        if wins.get(team_b, 0) > wins.get(team_a, 0):
            return team_b
        return team_a

    def _simulate_single_game(
        self,
        team_a: str,
        team_b: str,
        wins: dict[str, int],
        rng: np.random.Generator,
    ) -> dict[str, object]:
        """Simulate one neutral playoff/play-in matchup with home court assigned."""
        home = self._home_court(team_a, team_b, wins)
        away = team_b if home == team_a else team_a
        result = self.simulator.simulate_game(home, away, seed=int(rng.integers(1, 999_999)))
        winner = home if result.score[home] > result.score[away] else away
        return {
            "home": home,
            "away": away,
            "home_score": result.score[home],
            "away_score": result.score[away],
            "winner": winner,
            "overtime_periods": result.overtime_periods,
        }

    def _simulate_series(
        self,
        team_a: str,
        team_b: str,
        wins: dict[str, int],
        rng: np.random.Generator,
    ) -> dict[str, object]:
        """Simulate a best-of-seven series using a 2-2-1-1-1 home pattern."""
        home_court = self._home_court(team_a, team_b, wins)
        other = team_b if home_court == team_a else team_a
        home_pattern = [home_court, home_court, other, other, home_court, other, home_court]
        series_wins = {team_a: 0, team_b: 0}
        games: list[dict[str, object]] = []

        for game_number, home in enumerate(home_pattern, start=1):
            away = team_b if home == team_a else team_a
            result: SimulationResult = self.simulator.simulate_game(home, away, seed=int(rng.integers(1, 999_999)))
            winner = home if result.score[home] > result.score[away] else away
            series_wins[winner] += 1

            # Store every game so the UI can show the path, not just the series
            # winner. This makes seeded runs inspectable and reproducible.
            games.append(
                {
                    "number": game_number,
                    "home": home,
                    "away": away,
                    "home_score": result.score[home],
                    "away_score": result.score[away],
                    "winner": winner,
                    "overtime_periods": result.overtime_periods,
                }
            )
            if series_wins[winner] == 4:
                break

        winner = team_a if series_wins[team_a] > series_wins[team_b] else team_b
        loser = team_b if winner == team_a else team_a
        return {
            "team_a": team_a,
            "team_b": team_b,
            "home_court": home_court,
            "winner": winner,
            "loser": loser,
            "winner_wins": series_wins[winner],
            "loser_wins": series_wins[loser],
            "games": games,
        }

    def _simulate_play_in(
        self,
        conference: str,
        standings: dict[str, list[dict[str, object]]],
        wins: dict[str, int],
        rng: np.random.Generator,
    ) -> tuple[dict[int, str], list[dict[str, object]]]:
        """Run the NBA play-in format and return the final 1-8 playoff field."""
        teams_by_seed = {int(row["seed"]): str(row["team"]) for row in standings[conference]}
        events: list[dict[str, object]] = []

        # Seeds 7 and 8 play for the seventh seed. The loser gets one more chance.
        seven_eight = self._simulate_single_game(teams_by_seed[7], teams_by_seed[8], wins, rng)
        seven_seed = str(seven_eight["winner"])
        loser_78 = teams_by_seed[8] if seven_seed == teams_by_seed[7] else teams_by_seed[7]
        events.append({"label": "7/8 Game", **seven_eight})

        # Seeds 9 and 10 play an elimination game. The winner faces the 7/8 loser.
        nine_ten = self._simulate_single_game(teams_by_seed[9], teams_by_seed[10], wins, rng)
        winner_910 = str(nine_ten["winner"])
        events.append({"label": "9/10 Game", **nine_ten})

        # The winner of this final play-in game becomes the eighth seed.
        eight_game = self._simulate_single_game(loser_78, winner_910, wins, rng)
        eight_seed = str(eight_game["winner"])
        events.append({"label": "8 Seed Game", **eight_game})

        field = {
            1: teams_by_seed[1],
            2: teams_by_seed[2],
            3: teams_by_seed[3],
            4: teams_by_seed[4],
            5: teams_by_seed[5],
            6: teams_by_seed[6],
            7: seven_seed,
            8: eight_seed,
        }
        return field, events

    def simulate_playoffs(self, seed: int | None = None) -> PlayoffResult:
        """Simulate play-in, conference playoffs, and NBA Finals."""
        seed = seed if seed is not None else random.randint(1, 999_999)
        rng = np.random.default_rng(seed)
        standings = self.standings()
        wins = self._wins_lookup(standings)
        play_in: dict[str, list[dict[str, object]]] = {}
        fields: dict[str, dict[int, str]] = {}
        rounds: list[dict[str, object]] = []
        bracket: dict[str, dict[str, object]] = {"West": {}, "East": {}}

        for conference in ["West", "East"]:
            fields[conference], play_in[conference] = self._simulate_play_in(conference, standings, wins, rng)

            # Standard NBA bracket order after play-in seeds are resolved.
            first_matchups = [
                (fields[conference][1], fields[conference][8]),
                (fields[conference][4], fields[conference][5]),
                (fields[conference][3], fields[conference][6]),
                (fields[conference][2], fields[conference][7]),
            ]
            first_series = [self._simulate_series(a, b, wins, rng) for a, b in first_matchups]
            first_round = {"name": f"{conference} First Round", "conference": conference, "series": first_series}
            rounds.append(first_round)
            bracket[conference]["first_round"] = first_round

            # Winners feed forward into conference semifinals.
            semis_matchups = [
                (first_series[0]["winner"], first_series[1]["winner"]),
                (first_series[2]["winner"], first_series[3]["winner"]),
            ]
            semis = [self._simulate_series(a, b, wins, rng) for a, b in semis_matchups]
            semifinals = {"name": f"{conference} Semifinals", "conference": conference, "series": semis}
            rounds.append(semifinals)
            bracket[conference]["semifinals"] = semifinals

            # One conference finals series per conference.
            finals = [self._simulate_series(str(semis[0]["winner"]), str(semis[1]["winner"]), wins, rng)]
            conference_finals = {"name": f"{conference} Finals", "conference": conference, "series": finals}
            rounds.append(conference_finals)
            bracket[conference]["finals"] = conference_finals

        # The two conference champions meet in a final best-of-seven series.
        west_champ = str(bracket["West"]["finals"]["series"][0]["winner"])
        east_champ = str(bracket["East"]["finals"]["series"][0]["winner"])
        nba_finals = [self._simulate_series(west_champ, east_champ, wins, rng)]
        nba_finals_round = {"name": "NBA Finals", "conference": "NBA", "series": nba_finals}
        rounds.append(nba_finals_round)
        bracket["NBA"] = {"finals": nba_finals_round}

        return PlayoffResult(
            seed=seed,
            season=DEFAULT_SEASON,
            standings=standings,
            play_in=play_in,
            rounds=rounds,
            bracket=bracket,
            champion=str(nba_finals[0]["winner"]),
        )
