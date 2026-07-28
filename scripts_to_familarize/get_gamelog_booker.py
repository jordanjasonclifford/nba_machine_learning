"""Sandbox script for learning the nba_api career stats endpoint.

This is a small documentation-style example for Devin Booker. It is useful for
understanding endpoint output, but the simulator uses the warehouse CSVs instead.
"""


from nba_api.stats.endpoints import playercareerstats

# Devin Booker
career = playercareerstats.PlayerCareerStats(player_id='1626164')

# The endpoint exposes regular-season career totals as a named result set.
df = career.season_totals_regular_season.get_data_frame()

print(df[['SEASON_ID', 'TEAM_ABBREVIATION', 'PTS']])
