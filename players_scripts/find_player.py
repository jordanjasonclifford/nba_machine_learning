from nba_api.stats.static import players

# Search by name
player = players.find_players_by_full_name("Zion Williamson")

print(player) # THIS PRINTS THE PLAYER'S ID, IMPORTANT FOR THE 'extract_player.py' FILE
# Example output:
# [{'id': 1629627, 'full_name': 'Zion Williamson', 'is_active': True}]