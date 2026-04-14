 SELECT season,
    avg(ppg) AS cohort_ppg_avg,
    avg(apg) AS cohort_apg_avg,
    avg(rpg) AS cohort_rpg_avg
   FROM mart_player_season
  GROUP BY season;