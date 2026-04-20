"""
requery_unmatched.py

Re-attempts every player in unmatched_players.txt.
Cleans star ratings (****), draft years (2025), and handles
European accented names (Jokić -> Jokic) via Unicode normalization.
Saves CSVs to the correct 2026_Rosters_EOS/{TEAM}/ folder.
Writes anything still unresolved back to unmatched_players.txt.
"""

import os
import re
import unicodedata

# reuse everything from the main script
from batch_extract_rosters import (
    BASE_DIR, ROSTER_DIR, UNMATCHED,
    _all_players, output_path,
    get_active_seasons, extract_player,
)


# ------------------------------------------------------------------ #
#  Name cleaning
# ------------------------------------------------------------------ #

def clean_name(raw: str) -> str:
    name = re.sub(r"\*+", "", raw)          # remove *****
    name = re.sub(r"\b20\d{2}\b", "", name) # remove draft year e.g. 2025
    name = re.sub(r"\d+$", "", name)        # remove jersey number
    return name.strip()


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(c)
    )


# ------------------------------------------------------------------ #
#  Improved player lookup with accent fallback
# ------------------------------------------------------------------ #

def find_player(name: str):
    pool  = _all_players()
    lower = name.lower()
    lower_stripped = strip_accents(lower)

    # 1. exact match
    for p in pool:
        if p["full_name"].lower() == lower:
            return p

    # 2. exact match ignoring accents
    for p in pool:
        if strip_accents(p["full_name"].lower()) == lower_stripped:
            return p

    # 3. all name parts present (accent-stripped)
    parts = lower_stripped.split()
    matches = [
        p for p in pool
        if all(pt in strip_accents(p["full_name"].lower()) for pt in parts)
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        active = [p for p in matches if p.get("is_active")]
        if len(active) == 1:
            return active[0]
        print(f"  [ambiguous] '{name}' -> {[p['full_name'] for p in matches]}")
        return None

    # 4. last name only (unique, accent-stripped)
    last = parts[-1]
    last_matches = [
        p for p in pool
        if strip_accents(p["full_name"].lower()).endswith(last)
    ]
    if len(last_matches) == 1:
        return last_matches[0]

    return None


# ------------------------------------------------------------------ #
#  Main
# ------------------------------------------------------------------ #

def main():
    if not os.path.exists(UNMATCHED):
        print("unmatched_players.txt not found.")
        return

    with open(UNMATCHED, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]

    entries = []
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            entries.append((parts[0].strip(), parts[1].strip()))

    print(f"Found {len(entries)} unmatched players\n")

    still_unmatched = []

    for i, (team, raw_name) in enumerate(entries, 1):
        name = clean_name(raw_name)
        print(f"[{i}/{len(entries)}] {raw_name!r}  ->  cleaned: {name!r}  ({team})")

        out = output_path(name, team)
        if os.path.exists(out):
            print(f"  skip (CSV already exists)")
            continue

        info = find_player(name)
        if not info:
            print(f"  [unmatched] still could not resolve")
            still_unmatched.append(f"{team}\t{raw_name}")
            continue

        pid       = info["id"]
        full_name = info["full_name"]
        print(f"  -> {full_name}  (ID {pid})")

        out_canonical = output_path(full_name, team)
        if os.path.exists(out_canonical):
            print(f"  skip (CSV exists under canonical name)")
            continue

        seasons = get_active_seasons()
        print(f"  seasons: {seasons}")

        try:
            df = extract_player(pid, full_name, seasons)
            if df.empty:
                print(f"  [skip] no gamelog data returned")
            else:
                df.to_csv(out, index=False)
                print(f"  saved {len(df)} rows -> {out}")
        except Exception as e:
            print(f"  [error] {e}")
            still_unmatched.append(f"{team}\t{raw_name}")

    # overwrite unmatched_players.txt with only the ones still failing
    with open(UNMATCHED, "w", encoding="utf-8") as f:
        for line in still_unmatched:
            f.write(line + "\n")

    print(f"\nDone. {len(still_unmatched)} still unresolved -> {UNMATCHED}")


if __name__ == "__main__":
    main()
