#!/usr/bin/env python3
"""Clear SQLite cache entries. Usage: python3 scripts/cache_clear.py [TICKER]"""
import os
import sqlite3
import sys

db = "cache.db"
if not os.path.exists(db):
    print("No cache.db found — nothing to clear.")
    sys.exit(0)

ticker = (sys.argv[1] if len(sys.argv) > 1 else "").upper().strip()
conn = sqlite3.connect(db)

if ticker:
    n = conn.execute("DELETE FROM cache WHERE key LIKE ?", (ticker + "%",)).rowcount
    print(f"Cleared {n} cache entries for {ticker}")
else:
    n = conn.execute("DELETE FROM cache").rowcount
    print(f"Cleared all {n} cache entries")

conn.commit()
conn.close()
