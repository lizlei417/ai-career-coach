"""Explicit migration command. DATABASE_URL must be a privileged server connection."""
from pathlib import Path
import os
import psycopg

with psycopg.connect(os.environ["DATABASE_URL"],prepare_threshold=None) as connection:
    for name in ("001_private.sql","002_storage.sql"):
        connection.execute(Path(__file__).with_name(name).read_text())
print("Private schema and bucket migrations applied.")
