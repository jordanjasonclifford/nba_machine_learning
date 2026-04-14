SELECT
  p.player_name,
  p.season,
  p.player_team_abbr AS team_abbr,

  COUNT(*) AS games_played,

  -- Team outcomes + team boxscore stats (in those games)
  SUM(CASE WHEN t.wl = 'W' THEN 1 ELSE 0 END) AS team_wins,
  SUM(CASE WHEN t.wl = 'L' THEN 1 ELSE 0 END) AS team_losses,

  AVG(t.pts) AS team_pts_pg,
  AVG(t.ast) AS team_ast_pg,
  AVG(t.reb) AS team_reb_pg,
  AVG(t.tov) AS team_tov_pg,

  CASE WHEN SUM(t.fga)=0 THEN NULL ELSE SUM(t.fgm)*1.0/SUM(t.fga) END AS team_fg_pct,
  CASE WHEN SUM(t.fg3a)=0 THEN NULL ELSE SUM(t.fg3m)*1.0/SUM(t.fg3a) END AS team_fg3_pct,
  CASE WHEN SUM(t.fta)=0 THEN NULL ELSE SUM(t.ftm)*1.0/SUM(t.fta) END AS team_ft_pct

FROM v_player_game_team p
JOIN fact_team_game t
  ON t.game_id = p.game_id
 AND t.team_abbr = p.player_team_abbr
GROUP BY p.player_name, p.season, p.player_team_abbr;