import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "database.sqlite"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

workflow_id = "v6I1gSUzVngDtdvu"

print('workflow_entity:')
row = cur.execute("select id,name,active,versionId,activeVersionId,versionCounter from workflow_entity where id=?", (workflow_id,)).fetchone()
print(dict(row) if row else None)

print('\nworkflow_history schema:')
cols = cur.execute("pragma table_info(workflow_history)").fetchall()
for c in cols:
    print(dict(c))

print('\nworkflow_history rows for workflow:')
hrows = cur.execute("select * from workflow_history where workflowId=? order by createdAt desc limit 5", (workflow_id,)).fetchall()
print('count', cur.execute("select count(*) as c from workflow_history where workflowId=?", (workflow_id,)).fetchone()['c'])
for r in hrows:
    d = dict(r)
    # avoid dumping full nodes
    if 'nodes' in d and d['nodes'] is not None:
        d['nodes'] = f"<nodes {len(d['nodes'])} chars>"
    if 'connections' in d and d['connections'] is not None:
        d['connections'] = f"<connections {len(d['connections'])} chars>"
    print(d)

print('\nworkflow_publish_history rows:')
prows = cur.execute("select * from workflow_publish_history where workflowId=? order by createdAt desc limit 5", (workflow_id,)).fetchall()
print('count', cur.execute("select count(*) as c from workflow_publish_history where workflowId=?", (workflow_id,)).fetchone()['c'])
for r in prows:
    print(dict(r))
