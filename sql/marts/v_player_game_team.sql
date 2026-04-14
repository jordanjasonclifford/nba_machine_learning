SELECT
  player_name,
  season,
  game_id,
  game_date,
  split_part(matchup, ' ', 1) AS player_team_abbr
FROM fact_player_game;