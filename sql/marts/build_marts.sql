-- Build Views
\i v_allstar_player_games.sql
\i v_player_game_team.sql
\i v_team_games_by_season.sql
\i v_team_games_player_flag.sql

-- Core player marts
\i mart_player_season.sql
\i mart_player_home_away.sql
\i mart_player_wins_losses.sql
\i mart_player_consistency.sql

-- Cohort comparisons
\i mart_player_vs_cohort.sql
\i mart_player_vs_cohort_percentiles.sql
\i mart_cohort_rank_by_season.sql

-- Opponent analysis
\i mart_player_vs_opponent_team.sql

-- Head-to-head marts
\i mart_player_head_to_head_games.sql
\i mart_player_head_to_head_by_season.sql
\i mart_player_head_to_head_summary.sql

-- Team impact
\i mart_player_team_impact_with_without.sql
\i mart_player_team_perf_when_played.sql

-- Booker specific marts
\i mart_booker_vs_cohort.sql
\i mart_booker_vs_cohort_percentiles.sql
\i mart_booker_head_to_head_games.sql
\i mart_booker_head_to_head_by_season.sql
\i mart_booker_head_to_head_summary.sql
\i mart_booker_home_away.sql
\i mart_booker_wins_losses.sql
\i mart_booker_team_impact_with_without.sql
\i mart_booker_vs_opponent_team.sql

-- Environment table
\i mart_allstar_environment.sql