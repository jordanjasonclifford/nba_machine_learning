SELECT
  player,
  season,
  opponent,
  context,
  COUNT(*) AS games,

  SUM(CASE WHEN player_result = 'W' THEN 1 ELSE 0 END) AS player_wins,
  SUM(CASE WHEN player_result = 'L' THEN 1 ELSE 0 END) AS player_losses,

  AVG(player_pts) AS player_pts_pg,
  AVG(player_reb) AS player_reb_pg,
  AVG(player_ast) AS player_ast_pg,

  CASE WHEN SUM(player_fga)=0 THEN NULL ELSE SUM(player_fgm)*1.0/SUM(player_fga) END AS player_fg_pct,
  CASE WHEN SUM(player_fg3a)=0 THEN NULL ELSE SUM(player_fg3m)*1.0/SUM(player_fg3a) END AS player_fg3_pct,
  CASE WHEN SUM(player_fta)=0 THEN NULL ELSE SUM(player_ftm)*1.0/SUM(player_fta) END AS player_ft_pct,

  AVG(opp_pts) AS opp_pts_pg,
  AVG(opp_reb) AS opp_reb_pg,
  AVG(opp_ast) AS opp_ast_pg,

  CASE WHEN SUM(opp_fga)=0 THEN NULL ELSE SUM(opp_fgm)*1.0/SUM(opp_fga) END AS opp_fg_pct,
  CASE WHEN SUM(opp_fg3a)=0 THEN NULL ELSE SUM(opp_fg3m)*1.0/SUM(opp_fg3a) END AS opp_fg3_pct,
  CASE WHEN SUM(opp_fta)=0 THEN NULL ELSE SUM(opp_ftm)*1.0/SUM(opp_fta) END AS opp_ft_pct

FROM mart_player_head_to_head_games
GROUP BY player, season, opponent, context;