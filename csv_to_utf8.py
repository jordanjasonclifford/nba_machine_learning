"""Convert the player warehouse CSV to UTF-8.

Some player names contain accented characters, and older CSV outputs may be
encoded as Windows-1252. This utility rewrites the file as UTF-8 so pandas and
notebooks can read names consistently across machines.
"""

import pathlib

src = pathlib.Path("warehouse/fact_player_game.csv")
dst = pathlib.Path("warehouse/fact_player_game_utf8.csv")

# Replace undecodable bytes instead of failing, because this script is for
# recovery/normalization rather than strict encoding validation.
text = src.read_text(encoding="cp1252", errors="replace")
dst.write_text(text, encoding="utf-8", newline="\n")

print("Wrote:", dst)
