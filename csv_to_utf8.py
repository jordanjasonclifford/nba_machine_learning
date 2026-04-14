# due to the european player's names being in a different encoding, we need to convert the csvs to utf-8 before we can read them in pandas

import pathlib

src = pathlib.Path("warehouse/fact_player_game.csv")
dst = pathlib.Path("warehouse/fact_player_game_utf8.csv")

# Read as Windows-1252, replacing any un-decodable chars, then write UTF-8
text = src.read_text(encoding="cp1252", errors="replace")
dst.write_text(text, encoding="utf-8", newline="\n")

print("Wrote:", dst)