SELECT
  season,
  player_name,
  gp,
  ppg,
  pts_std,
  CASE
    WHEN ppg = 0 THEN NULL
    ELSE pts_std / ppg
  END AS pts_cv
FROM mart_player_season;