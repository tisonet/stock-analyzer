#!/usr/bin/env python3
"""List all SQLite cache entries with expiry status."""
import datetime
import os
import sqlite3

db = "cache.db"
if not os.path.exists(db):
    print("No cache.db found.")
else:
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT key, expires_at FROM cache ORDER BY key").fetchall()
    conn.close()
    if not rows:
        print("Cache is empty.")
    else:
        now = int(datetime.datetime.utcnow().timestamp())
        for key, exp in rows:
            remaining = exp - now
            if remaining > 0:
                status = f"expires in {remaining // 3600}h {(remaining % 3600) // 60}m"
            else:
                status = "EXPIRED"
            print(f"  {key:<25} {status}")
        print(f"\nTotal: {len(rows)} entries")
