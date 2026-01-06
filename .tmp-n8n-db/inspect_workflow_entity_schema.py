import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "database.sqlite"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

cols = cur.execute("pragma table_info(workflow_entity)").fetchall()
for c in cols:
    print(dict(c))

print('\nSample row columns:')
row = cur.execute("select * from workflow_entity limit 1").fetchone()
if row:
    print('keys', list(dict(row).keys()))
