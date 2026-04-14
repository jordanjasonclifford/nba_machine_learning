SELECT
  season,
  CASE
    WHEN matchup LIKE '%@%' THEN 'AWAY'
    ELSE 'HOME'
  END AS home_away,

  COUNT(*) AS games,
  SUM(CASE WHEN wl = 'W' THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN wl = 'L' THEN 1 ELSE 0 END) AS losses,

  AVG(pts) AS ppg,
  AVG(ast) AS apg,
  AVG(reb) AS rpg,

  CASE WHEN SUM(fga)=0 THEN NULL ELSE SUM(fgm)*1.0/SUM(fga) END AS fg_pct,
  CASE WHEN SUM(fg3a)=0 THEN NULL ELSE SUM(fg3m)*1.0/SUM(fg3a) END AS fg3_pct,
  CASE WHEN SUM(fta)=0 THEN NULL ELSE SUM(ftm)*1.0/SUM(fta) END AS ft_pct

FROM fact_player_game
GROUP BY player_name, season, home_away;