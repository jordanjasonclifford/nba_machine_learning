from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "warehouse"
MODELS = ROOT / "models"
DEFAULT_SEASON = "2025-26"


def ascii_name(value: object) -> str:
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")


@dataclass
class SimulationResult:
    score: dict[str, int]
    feed: list[dict[str, str]]
    box_score: list[dict[str, object]]
    home_team: str
    away_team: str
    season: str
    seed: int | None
    overtime_periods: int = 0


class GameSimulator:
    def __init__(self) -> None:
        self.team = pd.read_csv(WAREHOUSE / "fact_team_game.csv")
        self.team["GAME_DATE"] = pd.to_datetime(self.team["GAME_DATE"])
        self.player_weights = self._load_or_build_player_weights()
        self.player_pools: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
        self.teams = sorted(self.team["TEAM_ABBREVIATION"].dropna().unique().tolist())
        self.seasons = sorted(self.team["SEASON"].dropna().unique().tolist(), reverse=True)
        if DEFAULT_SEASON not in self.seasons:
            raise ValueError(f"Expected {DEFAULT_SEASON} season data in warehouse/fact_team_game.csv.")

    def _load_or_build_player_weights(self) -> pd.DataFrame:
        weights_path = MODELS / "player_event_weights.csv"
        if weights_path.exists():
            weights = pd.read_csv(weights_path)
            required = {
                "TEAM_ABBR",
                "PLAYER_NAME",
                "expected_min",
                "availability_weight",
                "scoring_weight",
                "free_throw_weight",
                "player_fg_pct",
                "player_fg3_pct",
                "player_ft_pct",
            }
            if required.issubset(weights.columns):
                return weights

        players = pd.read_csv(WAREHOUSE / "fact_player_game.csv")
        players["GAME_DATE"] = pd.to_datetime(players["GAME_DATE"])
        players["TEAM_ABBR"] = players["MATCHUP"].str[:3]
        season = players["SEASON"].max()
        recent = players[(players["SEASON"] == season) & (players["MIN"].fillna(0) > 0)].copy()

        agg = recent.groupby(["TEAM_ABBR", "PLAYER_ID", "PLAYER_NAME"], as_index=False).agg(
            {
                "GAME_DATE": "count",
                "MIN": ["sum", "mean"],
                "FGM": ["sum", "mean"],
                "FGA": ["sum", "mean"],
                "FG3M": ["sum", "mean"],
                "FG3A": ["sum", "mean"],
                "FTM": ["sum", "mean"],
                "FTA": ["sum", "mean"],
                "AST": ["sum", "mean"],
                "REB": ["sum", "mean"],
                "TOV": ["sum", "mean"],
                "PTS": ["sum", "mean"],
            }
        )
        agg.columns = ["_".join(col).strip("_") for col in agg.columns]
        agg = agg.rename(
            columns={
                "GAME_DATE_count": "GAMES",
                "MIN_mean": "MIN",
                "FGM_mean": "FGM",
                "FGA_mean": "FGA",
                "FG3M_mean": "FG3M",
                "FG3A_mean": "FG3A",
                "FTM_mean": "FTM",
                "FTA_mean": "FTA",
                "AST_mean": "AST",
                "REB_mean": "REB",
                "TOV_mean": "TOV",
                "PTS_mean": "PTS",
            }
        )

        agg["shot_raw"] = agg["FGA_sum"] + 0.44 * agg["FTA_sum"] + 0.25 * agg["AST_sum"]
        agg["scoring_raw"] = agg["shot_raw"]
        agg["three_raw"] = agg["FG3A_sum"]
        agg["free_throw_raw"] = agg["FTA_sum"]
        agg["assist_raw"] = agg["AST_sum"]
        agg["rebound_raw"] = agg["REB_sum"]
        agg["turnover_raw"] = agg["TOV_sum"]
        agg["minutes_raw"] = agg["MIN_sum"]
        agg["player_fg_pct"] = (agg["FGM_sum"] / agg["FGA_sum"].replace(0, np.nan)).fillna(0.45)
        agg["player_fg3_pct"] = (agg["FG3M_sum"] / agg["FG3A_sum"].replace(0, np.nan)).fillna(0.35)
        agg["player_ft_pct"] = (agg["FTM_sum"] / agg["FTA_sum"].replace(0, np.nan)).fillna(0.77)

        raw_cols = [
            "shot_raw",
            "scoring_raw",
            "three_raw",
            "free_throw_raw",
            "assist_raw",
            "rebound_raw",
            "turnover_raw",
            "minutes_raw",
        ]
        for col in raw_cols:
            weight_col = col.replace("_raw", "_weight")
            totals = agg.groupby("TEAM_ABBR")[col].transform("sum").replace(0, np.nan)
            agg[weight_col] = (agg[col] / totals).fillna(0)

        agg = agg.sort_values(["TEAM_ABBR", "MIN_sum"], ascending=[True, False])
        agg["rotation_rank"] = agg.groupby("TEAM_ABBR").cumcount() + 1
        agg["rotation_min_raw"] = np.where(agg["rotation_rank"] <= 10, agg["MIN"], 0.0)
        agg["locked_star_min"] = np.where(agg["rotation_rank"] <= 2, agg["MIN"].clip(upper=36), 0.0)
        locked_totals = agg.groupby("TEAM_ABBR")["locked_star_min"].transform("sum")
        remaining_team_min = (240 - locked_totals).clip(lower=0)
        bench_rotation_raw = np.where(
            (agg["rotation_rank"] > 2) & (agg["rotation_rank"] <= 10), agg["MIN"], 0.0
        )
        bench_totals = pd.Series(bench_rotation_raw, index=agg.index).groupby(agg["TEAM_ABBR"]).transform("sum")
        bench_totals = bench_totals.replace(0, np.nan)
        scaled_bench_min = bench_rotation_raw / bench_totals * remaining_team_min
        agg["expected_min"] = np.where(agg["rotation_rank"] <= 2, agg["locked_star_min"], scaled_bench_min)
        agg["expected_min"] = agg["expected_min"].round(1).fillna(0)
        agg["availability_weight"] = (
            agg["expected_min"] / agg.groupby("TEAM_ABBR")["expected_min"].transform("max")
        ).clip(lower=0.02)

        active_scoring = 0.60 * agg["PTS"] + 0.25 * (agg["FGA"] + 0.44 * agg["FTA"]) + 0.15 * agg["expected_min"]
        agg["scoring_raw"] = active_scoring.clip(lower=0) * agg["availability_weight"]
        agg["free_throw_raw"] = agg["FTA"].clip(lower=0) * agg["availability_weight"]
        for col in ["scoring_raw", "free_throw_raw"]:
            weight_col = col.replace("_raw", "_weight")
            totals = agg.groupby("TEAM_ABBR")[col].transform("sum").replace(0, np.nan)
            agg[weight_col] = (agg[col] / totals).fillna(0)

        MODELS.mkdir(exist_ok=True)
        agg.to_csv(weights_path, index=False)
        return agg

    def team_profile(self, team_abbr: str, season: str | None = None, last_n: int = 25) -> dict[str, float]:
        data = self.team[self.team["TEAM_ABBREVIATION"] == team_abbr].sort_values("GAME_DATE")
        if season:
            data = data[data["SEASON"] == season]
        data = data.tail(last_n)
        return {
            "pts": data["PTS"].mean(),
            "fg_pct": data["FG_PCT"].mean(),
            "fg3_rate": data["FG3A"].sum() / max(data["FGA"].sum(), 1),
            "fg3_pct": data["FG3_PCT"].mean(),
            "fta_rate": data["FTA"].sum() / max(data["FGA"].sum(), 1),
            "ft_pct": data["FT_PCT"].mean(),
            "tov_rate": data["TOV"].sum() / max(data["FGA"].sum() + data["FTA"].sum() + data["TOV"].sum(), 1),
        }

    def expected_minutes_lookup(self, team_abbr: str) -> dict[str, float]:
        pool = self.player_weights[self.player_weights["TEAM_ABBR"] == team_abbr].copy()
        if "expected_min" not in pool.columns:
            return {}
        pool["PLAYER_NAME"] = pool["PLAYER_NAME"].map(ascii_name)
        return dict(zip(pool["PLAYER_NAME"], pool["expected_min"]))

    def choose_player(self, team_abbr: str, weight_col: str, rng: np.random.Generator) -> str:
        key = (team_abbr, weight_col)
        if key not in self.player_pools:
            pool = self.player_weights[self.player_weights["TEAM_ABBR"] == team_abbr].copy()
            pool = pool[pool[weight_col] > 0]
            if pool.empty:
                self.player_pools[key] = (np.array([team_abbr]), np.array([1.0]))
            else:
                availability = pool.get("availability_weight", 1.0)
                probs = pool[weight_col].to_numpy(dtype=float) * np.asarray(availability, dtype=float)
                probs = probs / probs.sum()
                names = pool["PLAYER_NAME"].map(ascii_name).to_numpy()
                self.player_pools[key] = (names, probs)
        names, probs = self.player_pools[key]
        return str(rng.choice(names, p=probs))

    def choose_player_profile(
        self, team_abbr: str, weight_col: str, rng: np.random.Generator
    ) -> tuple[str, dict[str, object]]:
        name = self.choose_player(team_abbr, weight_col, rng)
        pool = self.player_weights[self.player_weights["TEAM_ABBR"] == team_abbr].copy()
        pool["PLAYER_NAME_ASCII"] = pool["PLAYER_NAME"].map(ascii_name)
        match = pool[pool["PLAYER_NAME_ASCII"] == name]
        profile = match.iloc[0].to_dict() if not match.empty else {}
        return name, profile

    @staticmethod
    def format_clock(seconds_remaining: int) -> str:
        quarter = 5 - int(np.ceil(seconds_remaining / 720))
        quarter = min(max(quarter, 1), 4)
        q_elapsed = 720 - ((seconds_remaining - 1) % 720 + 1)
        q_remaining = 720 - q_elapsed
        minutes = int(q_remaining // 60)
        seconds = int(q_remaining % 60)
        return f"Q{quarter} {minutes:02d}:{seconds:02d}"

    def simulate_game(
        self,
        home_team: str,
        away_team: str,
        season: str | None = None,
        seed: int | None = None,
    ) -> SimulationResult:
        if home_team == away_team:
            raise ValueError("Choose two different teams.")
        if home_team not in self.teams or away_team not in self.teams:
            raise ValueError("Unknown team abbreviation.")

        rng = np.random.default_rng(seed)
        season = DEFAULT_SEASON
        home_profile = self.team_profile(home_team, season)
        away_profile = self.team_profile(away_team, season)

        expected_total = np.nanmean([home_profile["pts"], away_profile["pts"]]) * 2
        possessions = int(np.clip(round(expected_total / 1.12), 176, 212))
        seconds_remaining = 48 * 60
        score = {home_team: 0, away_team: 0}
        feed: list[dict[str, str]] = []
        stat_cols = ["PTS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "OREB", "REB", "AST", "TOV"]
        box: dict[tuple[str, str], dict[str, object]] = {}
        expected_mins = {**self.expected_minutes_lookup(home_team), **self.expected_minutes_lookup(away_team)}

        def ensure_player(team_abbr: str, player_name: str) -> dict[str, object]:
            key = (team_abbr, player_name)
            if key not in box:
                box[key] = {
                    "TEAM": team_abbr,
                    "PLAYER": player_name,
                    "MIN": expected_mins.get(player_name, 0.0),
                    **{col: 0 for col in stat_cols},
                }
            return box[key]

        def add_stat(team_abbr: str, player_name: str, **stats: int) -> None:
            row = ensure_player(team_abbr, player_name)
            for stat, value in stats.items():
                row[stat] = int(row[stat]) + value

        def play_possession(offense: str, defense: str, profile: dict[str, float], clock: str) -> int:
            elapsed = int(rng.integers(7, 25))

            if rng.random() < profile["tov_rate"]:
                player = self.choose_player(offense, "turnover_weight", rng)
                add_stat(offense, player, TOV=1)
                feed.append({"clock": clock, "team": offense, "text": f"{player} turnover"})
                return elapsed

            if rng.random() < min(profile["fta_rate"] * 0.35, 0.16):
                shooter, shooter_profile = self.choose_player_profile(offense, "free_throw_weight", rng)
                ft_pct = shooter_profile.get("player_ft_pct", profile.get("ft_pct", 0.77))
                ft_pct = 0.77 if pd.isna(ft_pct) else float(ft_pct)
                made_fts = int(rng.binomial(2, ft_pct))
                score[offense] += made_fts
                add_stat(offense, shooter, PTS=made_fts, FTM=made_fts, FTA=2)
                feed.append({"clock": clock, "team": offense, "text": f"{shooter} makes {made_fts} of 2 free throws"})
                return int(rng.integers(12, 26))

            is_three = rng.random() < profile["fg3_rate"]
            shot_weight = "three_weight" if is_three else "scoring_weight"
            shooter, shooter_profile = self.choose_player_profile(offense, shot_weight, rng)
            if is_three:
                player_make = shooter_profile.get("player_fg3_pct", profile["fg3_pct"])
                make_prob = 0.55 * profile["fg3_pct"] + 0.45 * player_make
            else:
                player_make = shooter_profile.get("player_fg_pct", profile["fg_pct"])
                make_prob = min(0.55 * (profile["fg_pct"] + 0.06) + 0.45 * player_make, 0.68)
            make_prob = 0.45 if pd.isna(make_prob) else float(make_prob)
            made = rng.random() < make_prob

            if made:
                points = 3 if is_three else 2
                score[offense] += points
                assist = self.choose_player(offense, "assist_weight", rng)
                shot_name = "3PT shot" if is_three else "2PT shot"
                add_stat(offense, shooter, PTS=points, FGM=1, FGA=1, FG3M=int(is_three), FG3A=int(is_three))
                if assist != shooter and rng.random() < 0.62:
                    add_stat(offense, assist, AST=1)
                    text = f"{shooter} makes {shot_name} assisted by {assist}"
                else:
                    text = f"{shooter} makes {shot_name}"
                feed.append({"clock": clock, "team": offense, "text": text})
                return elapsed

            shot_name = "3PT shot" if is_three else "2PT shot"
            add_stat(offense, shooter, FGA=1, FG3A=int(is_three))
            feed.append({"clock": clock, "team": offense, "text": f"{shooter} misses {shot_name}"})
            if rng.random() < 0.24:
                rebounder = self.choose_player(offense, "rebound_weight", rng)
                add_stat(offense, rebounder, OREB=1, REB=1)
                feed.append({"clock": clock, "team": offense, "text": f"{rebounder} offensive rebound"})
            else:
                rebounder = self.choose_player(defense, "rebound_weight", rng)
                add_stat(defense, rebounder, REB=1)
            return elapsed

        last_possession_index = -1
        for possession in range(possessions):
            last_possession_index = possession
            offense = home_team if possession % 2 == 0 else away_team
            defense = away_team if offense == home_team else home_team
            profile = home_profile if offense == home_team else away_profile
            clock = self.format_clock(seconds_remaining)
            seconds_remaining = max(0, seconds_remaining - play_possession(offense, defense, profile, clock))
            if seconds_remaining <= 0:
                break

        overtime_periods = 0
        next_possession = last_possession_index + 1
        while score[home_team] == score[away_team]:
            overtime_periods += 1
            feed.append(
                {
                    "clock": "OT",
                    "team": "GAME",
                    "text": f"Overtime {overtime_periods} begins",
                }
            )
            ot_seconds_remaining = 5 * 60
            while ot_seconds_remaining > 0:
                offense = home_team if next_possession % 2 == 0 else away_team
                defense = away_team if offense == home_team else home_team
                profile = home_profile if offense == home_team else away_profile
                ot_label = "OT" if overtime_periods == 1 else f"{overtime_periods}OT"
                minutes = int(ot_seconds_remaining // 60)
                seconds = int(ot_seconds_remaining % 60)
                clock = f"{ot_label} {minutes:02d}:{seconds:02d}"
                ot_seconds_remaining = max(0, ot_seconds_remaining - play_possession(offense, defense, profile, clock))
                next_possession += 1

        if overtime_periods:
            for team_abbr in [away_team, home_team]:
                team_rows = [row for row in box.values() if row["TEAM"] == team_abbr and float(row["MIN"]) > 0]
                total_minutes = sum(float(row["MIN"]) for row in team_rows)
                if total_minutes:
                    for row in team_rows:
                        extra_minutes = (float(row["MIN"]) / total_minutes) * overtime_periods * 25
                        row["MIN"] = round(float(row["MIN"]) + extra_minutes, 1)

        box_score = pd.DataFrame(box.values())
        if not box_score.empty:
            box_score["FG"] = box_score["FGM"].astype(str) + "-" + box_score["FGA"].astype(str)
            box_score["FG3"] = box_score["FG3M"].astype(str) + "-" + box_score["FG3A"].astype(str)
            box_score["FT"] = box_score["FTM"].astype(str) + "-" + box_score["FTA"].astype(str)
            box_score = box_score.sort_values(["TEAM", "MIN", "PTS"], ascending=[True, False, False])
            box_score = box_score[["TEAM", "PLAYER", "MIN", "PTS", "REB", "AST", "FG", "FG3", "FT", "OREB", "TOV"]]

        return SimulationResult(
            score=score,
            feed=feed,
            box_score=box_score.to_dict("records"),
            home_team=home_team,
            away_team=away_team,
            season=season,
            seed=seed,
            overtime_periods=overtime_periods,
        )
