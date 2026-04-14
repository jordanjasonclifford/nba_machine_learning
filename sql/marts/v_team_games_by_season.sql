SELECT
  season,
  team_abbr,
  game_id,
  game_date,
  season_type,
  wl,
  pts, ast, reb, tov,
  fgm, fga, fg3m, fg3a, ftm, fta
FROM fact_team_game
WHERE season_type = 'Regular Season';