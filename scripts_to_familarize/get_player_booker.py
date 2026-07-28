"""Sandbox script for learning the nba_api player gamelog endpoint.

This is not part of the production simulator path. It simply fetches a small
Devin Booker sample so the expected endpoint shape is easy to inspect.
"""

from nba_api.stats.endpoints import playergamelog

gamelog = playergamelog.PlayerGameLog(
    player_id='1626164',  # Booker
    season='2025-26'
)

# Convert the endpoint response to a pandas DataFrame and preview the columns.
df = gamelog.get_data_frames()[0]
print(df.head())
