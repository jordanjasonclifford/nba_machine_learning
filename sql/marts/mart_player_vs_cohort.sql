SELECT
  p.player_name,
  p.season,
  p.gp,
  p.ppg,
  p.apg,
  p.rpg,
  p.mpg,
  p.pts_std,

  e.cohort_ppg_avg,
  (p.ppg - e.cohort_ppg_avg) AS ppg_minus_cohort,
  CASE WHEN e.cohort_ppg_avg = 0 THEN NULL ELSE p.ppg / e.cohort_ppg_avg END AS ppg_relative_index,

  e.cohort_apg_avg,
  (p.apg - e.cohort_apg_avg) AS apg_minus_cohort,

  e.cohort_rpg_avg,
  (p.rpg - e.cohort_rpg_avg) AS rpg_minus_cohort

FROM mart_player_season p
JOIN mart_allstar_environment e
  ON e.season = p.season;