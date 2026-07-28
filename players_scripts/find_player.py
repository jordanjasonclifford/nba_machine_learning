"""Look up an nba_api player id by full name.

This is a small helper used before running `players_scripts/extract_player.py`.
The extracted id is the value that nba_api endpoints require for player gamelogs.
"""

from nba_api.stats.static import players

# Change this string to the player you want to resolve.
player = players.find_players_by_full_name("Zion Williamson")

print(player)  # Use the printed `id` value in `extract_player.py`.
# Example output:
# [{'id': 1629627, 'full_name': 'Zion Williamson', 'is_active': True}]
