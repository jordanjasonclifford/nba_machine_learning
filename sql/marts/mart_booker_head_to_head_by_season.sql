SELECT
  season,
  opponent,
  context,
  games,
  player_wins AS booker_wins,
  player_losses AS booker_losses,
  player_pts_pg AS booker_pts_pg,
  player_reb_pg AS booker_reb_pg,
  player_ast_pg AS booker_ast_pg,
  player_fg_pct AS booker_fg_pct,
  player_fg3_pct AS booker_fg3_pct,
  player_ft_pct AS booker_ft_pct,
  opp_pts_pg,
  opp_reb_pg,
  opp_ast_pg,
  opp_fg_pct,
  opp_fg3_pct,
  opp_ft_pct
FROM mart_player_head_to_head_by_season
WHERE player = 'Devin Booker';