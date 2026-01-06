import sqlite3
from pathlib import Path

p = Path(__file__).resolve().parent / "database.sqlite"
con = sqlite3.connect(p)
cur = con.cursor()
cur.execute("select name from sqlite_master where type='table' order by name")
tables = [r[0] for r in cur.fetchall()]
print("tables", len(tables))
for t in tables:
    if "workflow" in t.lower() or "version" in t.lower():
        print(" -", t)
