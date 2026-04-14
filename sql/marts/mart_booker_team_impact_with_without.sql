SELECT *
FROM mart_player_team_impact_with_without
WHERE player_name = 'Devin Booker' AND team_abbr = 'PHX'
ORDER BY season, bucket;