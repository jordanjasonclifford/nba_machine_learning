DROP TABLE IF EXISTS fact_team_game;
DROP TABLE IF EXISTS fact_player_game;

-- Matches warehouse/fact_team_game.csv header exactly
CREATE TABLE fact_team_game (
  season_id           TEXT,
  team_id             BIGINT,
  team_abbreviation   TEXT,
  team_name           TEXT,
  game_id             TEXT,
  game_date           DATE,
  matchup             TEXT,
  wl                  TEXT,
  min                 NUMERIC,
  pts                 NUMERIC,
  fgm                 NUMERIC,
  fga                 NUMERIC,
  fg_pct              NUMERIC,
  fg3m                NUMERIC,
  fg3a                NUMERIC,
  fg3_pct             NUMERIC,
  ftm                 NUMERIC,
  fta                 NUMERIC,
  ft_pct              NUMERIC,
  oreb                NUMERIC,
  dreb                NUMERIC,
  reb                 NUMERIC,
  ast                 NUMERIC,
  stl                 NUMERIC,
  blk                 NUMERIC,
  tov                 NUMERIC,
  pf                  NUMERIC,
  plus_minus          NUMERIC,
  season              TEXT,
  season_type         TEXT,
  team_abbr           TEXT
);

-- Matches warehouse/fact_player_game.csv header exactly
CREATE TABLE fact_player_game (
  season_id         TEXT,
  player_id_raw     BIGINT,   -- "Player_ID" column from CSV
  game_id           TEXT,
  game_date         DATE,
  matchup           TEXT,
  wl                TEXT,
  min               NUMERIC,
  fgm               NUMERIC,
  fga               NUMERIC,
  fg_pct            NUMERIC,
  fg3m              NUMERIC,
  fg3a              NUMERIC,
  fg3_pct           NUMERIC,
  ftm               NUMERIC,
  fta               NUMERIC,
  ft_pct            NUMERIC,
  oreb              NUMERIC,
  dreb              NUMERIC,
  reb               NUMERIC,
  ast               NUMERIC,
  stl               NUMERIC,
  blk               NUMERIC,
  tov               NUMERIC,
  pf                NUMERIC,
  pts               NUMERIC,
  plus_minus        NUMERIC,
  video_available   NUMERIC,
  season            TEXT,
  player_id         BIGINT,   -- "PLAYER_ID" column from CSV
  player_name       TEXT
);
