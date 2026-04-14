WITH cohort AS (
  SELECT
    p.player_name,
    p.season,
    p.gp,
    p.ppg,
    p.apg,
    p.rpg,
    p.mpg
  FROM mart_player_season p
  JOIN dim_allstar_cohort c
    ON c.player_name = p.player_name
)
SELECT
  player_name,
  season,
  gp,
  ppg,
  apg,
  rpg,
  mpg,

  -- ranks (1 = best/highest)
  RANK() OVER (PARTITION BY season ORDER BY ppg DESC) AS ppg_rank,
  RANK() OVER (PARTITION BY season ORDER BY apg DESC) AS apg_rank,
  RANK() OVER (PARTITION BY season ORDER BY rpg DESC) AS rpg_rank,
  RANK() OVER (PARTITION BY season ORDER BY mpg DESC) AS mpg_rank,

  -- percentiles (0.00 = lowest, 1.00 = highest)
  PERCENT_RANK() OVER (PARTITION BY season ORDER BY ppg) AS ppg_percentile,
  PERCENT_RANK() OVER (PARTITION BY season ORDER BY apg) AS apg_percentile,
  PERCENT_RANK() OVER (PARTITION BY season ORDER BY rpg) AS rpg_percentile,
  PERCENT_RANK() OVER (PARTITION BY season ORDER BY mpg) AS mpg_percentile

FROM cohort;