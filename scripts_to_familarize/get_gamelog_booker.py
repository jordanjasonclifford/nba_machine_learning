# This script is for testing and familiarization with the nba_api library, specifically for getting Devin Booker's career stats.
# a variation of this is found right on the documentation, viewable on https://github.com/swar/nba_api/tree/master


from nba_api.stats.endpoints import playercareerstats

# Devin Booker
career = playercareerstats.PlayerCareerStats(player_id='1626164')

df = career.season_totals_regular_season.get_data_frame()

print(df[['SEASON_ID', 'TEAM_ABBREVIATION', 'PTS']])