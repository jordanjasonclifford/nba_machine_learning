SELECT
  player_name,
  season,
  team_abbr,
  player_played,
  bucket,

  COUNT(*) AS team_games,

  SUM(CASE WHEN wl = 'W' THEN 1 ELSE 0 END) AS team_wins,
  SUM(CASE WHEN wl = 'L' THEN 1 ELSE 0 END) AS team_losses,

  AVG(pts) AS team_pts_pg,
  AVG(ast) AS team_ast_pg,
  AVG(reb) AS team_reb_pg,
  AVG(tov) AS team_tov_pg,

  CASE WHEN SUM(fga)=0 THEN NULL ELSE SUM(fgm)*1.0/SUM(fga) END AS team_fg_pct,
  CASE WHEN SUM(fg3a)=0 THEN NULL ELSE SUM(fg3m)*1.0/SUM(fg3a) END AS team_fg3_pct,
  CASE WHEN SUM(fta)=0 THEN NULL ELSE SUM(ftm)*1.0/SUM(fta) END AS team_ft_pct

FROM v_team_games_player_flag
GROUP BY player_name, season, team_abbr, player_played, bucket;