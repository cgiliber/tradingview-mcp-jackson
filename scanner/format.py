#!/usr/bin/env python3
"""Format scanner JSON output as a brief table. Reads from stdin."""
import sys, json

lines = sys.stdin.read()
parts = lines.split('\n📊')
data = json.loads(parts[0])
for d in data:
    if 'error' not in d:
        alert = '⚡' if abs(d['change_pct']) > 1 else '  '
        dir = '📈' if d['change_pct'] > 0 else '📉'
        print(f'{alert} {dir} {d["mapped"]:14} {d["price"]:>12.2f}  {d["change_pct"]:>+.2f}%')
if len(parts) > 1:
    print(f'📊{parts[1]}')
