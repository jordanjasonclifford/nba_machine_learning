SELECT
  t.season,
  t.team_abbr,
  t.game_id,
  t.game_date,
  t.season_type,

  p.player_name,

  CASE WHEN pg.game_id IS NULL THEN 0 ELSE 1 END AS player_played,
  CASE WHEN pg.game_id IS NULL THEN 'WITHOUT_PLAYER' ELSE 'WITH_PLAYER' END AS bucket, -- for ease of use in BI tools

  t.wl,
  t.pts, t.ast, t.reb, t.tov,
  t.fgm, t.fga, t.fg3m, t.fg3a, t.ftm, t.fta
FROM v_team_games_by_season t
JOIN (SELECT player_name FROM dim_allstar_cohort) p
  ON 1=1
LEFT JOIN v_player_game_team pg
  ON pg.player_name = p.player_name
 AND pg.game_id = t.game_id
 AND pg.player_team_abbr = t.team_abbr;