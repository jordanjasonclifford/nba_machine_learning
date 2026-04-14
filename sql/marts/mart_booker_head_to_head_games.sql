SELECT
  game_id,
  game_date,
  season,
  opponent,
  context,
  player_pts AS booker_pts,
  player_ast AS booker_ast,
  player_reb AS booker_reb,
  player_fgm AS booker_fgm,
  player_fga AS booker_fga,
  player_fg3m AS booker_fg3m,
  player_fg3a AS booker_fg3a,
  player_ftm AS booker_ftm,
  player_fta AS booker_fta,
  player_result AS booker_result,
  opp_pts,
  opp_ast,
  opp_reb,
  opp_fgm,
  opp_fga,
  opp_fg3m,
  opp_fg3a,
  opp_ftm,
  opp_fta
FROM mart_player_head_to_head_games
WHERE player = 'Devin Booker'
ORDER BY season, game_date;