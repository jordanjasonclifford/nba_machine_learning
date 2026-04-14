 SELECT player_name,
    season,
    count(*) AS gp,
    avg(pts) AS ppg,
    avg(ast) AS apg,
    avg(reb) AS rpg,
    avg(min) AS mpg,
    stddev_pop(pts) AS pts_std
   FROM v_allstar_player_games
  GROUP BY player_name, season;