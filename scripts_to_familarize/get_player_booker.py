# This script is for testing and familiarization with the nba_api library, specifically for getting Devin Booker's game logs.
# It is not meant to be a reusable script, but rather a sandbox for learning how to
# use the API to get the data we need for our analysis.

from nba_api.stats.endpoints import playergamelog

gamelog = playergamelog.PlayerGameLog(
    player_id='1626164',  # Booker
    season='2025-26'
)

df = gamelog.get_data_frames()[0]
print(df.head())