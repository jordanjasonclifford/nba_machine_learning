SELECT
  season,
  player_name,
  gp,
  ppg,
  apg,
  rpg,
  mpg,
  pts_std,

  RANK() OVER (PARTITION BY season ORDER BY ppg DESC) AS rank_ppg,
  RANK() OVER (PARTITION BY season ORDER BY apg DESC) AS rank_apg,
  RANK() OVER (PARTITION BY season ORDER BY rpg DESC) AS rank_rpg

FROM mart_player_season;