#!/usr/bin/env python3
"""Rank video options with Video Brain's fixed weights.

Input: a text file, one option per line:
    name | hook | fit | facts | lama | doable | reuse
Scores are 1-5. Lines starting with # are ignored.
Usage: python decide.py options.txt
"""
import sys

WEIGHTS = {"hook": 0.25, "fit": 0.15, "facts": 0.20, "lama": 0.20, "doable": 0.10, "reuse": 0.10}
KEYS = list(WEIGHTS)
GATES = ("facts", "lama")  # below 3 on either = never recommend


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python decide.py options.txt")
    try:
        lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
    except OSError as e:
        sys.exit(f"ERROR: cannot read {sys.argv[1]}: {e.strerror}")
    rows, errors = [], []
    for n, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 7:
            errors.append(f"line {n}: need 7 parts (name + 6 scores), got {len(parts)}")
            continue
        try:
            scores = [int(p) for p in parts[1:]]
        except ValueError:
            errors.append(f"line {n}: scores must be whole numbers 1-5 (no decimals)")
            continue
        if any(s < 1 or s > 5 for s in scores):
            errors.append(f"line {n}: scores must be 1-5")
            continue
        s = dict(zip(KEYS, scores))
        total = round(sum(s[k] * w for k, w in WEIGHTS.items()) * 20)  # 0-100
        blocked = [k for k in GATES if s[k] < 3]
        rows.append((parts[0], s, total, blocked))
    if errors:
        print("FIX options.txt:")
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    if not rows:
        sys.exit("ERROR: no options found")
    rows.sort(key=lambda r: (bool(r[3]), -r[2]))
    print("RANK | SCORE | OPTION | " + " ".join(k.upper() for k in KEYS) + " | NOTE")
    for i, (name, s, total, blocked) in enumerate(rows, 1):
        note = "BLOCKED (" + ", ".join(blocked) + " below 3)" if blocked else ""
        weakest = min((k for k in KEYS), key=lambda k: s[k])
        if not blocked:
            note = f"weakest: {weakest}"
        print(f"{i} | {total} | {name} | " + " ".join(str(s[k]) for k in KEYS) + f" | {note}")
    ok = [r for r in rows if not r[3]]
    if not ok:
        print("\nRESULT: all options BLOCKED. Fix facts/Lama issues or make new ideas.")
    elif len(ok) > 1 and ok[0][2] == ok[1][2]:
        print(f"\nRESULT: TIE between '{ok[0][0]}' and '{ok[1][0]}'. Ask Jayson to pick.")
    else:
        print(f"\nRESULT: WINNER = {ok[0][0]} ({ok[0][2]}/100)")


if __name__ == "__main__":
    main()
