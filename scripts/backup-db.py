"""Create a consistent SQLite backup while the bridge is running.

Usage:
  python scripts/backup-db.py --output backups/messages-2026-10-16.db
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--database", default=os.getenv("DB_PATH", "data/messages.db"))
parser.add_argument("--output", required=True)
args = parser.parse_args()

source = Path(args.database)
destination = Path(args.output)
if not source.exists():
    raise SystemExit(f"database does not exist: {source}")
destination.parent.mkdir(parents=True, exist_ok=True)

with sqlite3.connect(source) as source_connection, sqlite3.connect(destination) as destination_connection:
    source_connection.backup(destination_connection)

print(f"backup created: {destination}")

