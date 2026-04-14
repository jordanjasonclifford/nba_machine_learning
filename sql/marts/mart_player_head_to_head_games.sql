SELECT
    b.player_name AS player,
    b.game_id,
    b.game_date,
    b.season,

    o.player_name AS opponent,

    CASE
        WHEN split_part(b.matchup, ' ', 1) = split_part(o.matchup, ' ', 1)
        THEN 'WITH'
        ELSE 'AGAINST'
    END AS context,

    -- player stats 
    b.pts AS player_pts,
    b.ast AS player_ast,
    b.reb AS player_reb,
    b.fgm AS player_fgm,
    b.fga AS player_fga,
    b.fg3m AS player_fg3m,
    b.fg3a AS player_fg3a,
    b.ftm AS player_ftm,
    b.fta AS player_fta,
    b.wl  AS player_result,

    -- opponent stats
    o.pts AS opp_pts,
    o.ast AS opp_ast,
    o.reb AS opp_reb,
    o.fgm AS opp_fgm,
    o.fga AS opp_fga,
    o.fg3m AS opp_fg3m,
    o.fg3a AS opp_fg3a,
    o.ftm AS opp_ftm,
    o.fta AS opp_fta

FROM fact_player_game b
JOIN fact_player_game o
  ON b.game_id = o.game_id
 AND b.player_name <> o.player_name

JOIN dim_allstar_cohort c
  ON c.player_name = o.player_name;