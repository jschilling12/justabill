import sqlite3
import uuid
from pathlib import Path

DB = Path(__file__).resolve().parent / "database.sqlite"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Find a user id to attribute as an author (fallback to literal string)
author = None
for table in ("user", "user_entity"):
    try:
        row = cur.execute(f"select id from {table} limit 1").fetchone()
        if row and row[0]:
            author = str(row[0])
            break
    except sqlite3.Error:
        continue
if not author:
    author = "import"

workflows = cur.execute(
    "select id, name, nodes, connections, description, versionId from workflow_entity"
).fetchall()

# Ensure versionId values are unique UUIDs (workflow_history.versionId is a PK).
used_version_ids: set[str] = set()
existing_version_ids = [str(w["versionId"]) for w in workflows]

# Mark duplicates/invalids for replacement
needs_new: dict[str, str] = {}  # workflow_id -> new_version_id
for w in workflows:
    wid = str(w["id"])
    vid = str(w["versionId"]) if w["versionId"] is not None else ""

    is_uuidish = len(vid) == 36 and vid.count("-") == 4
    is_duplicate = existing_version_ids.count(vid) > 1
    if (not is_uuidish) or is_duplicate or (vid in used_version_ids):
        new_vid = str(uuid.uuid4())
        needs_new[wid] = new_vid
        used_version_ids.add(new_vid)
    else:
        used_version_ids.add(vid)

# Apply workflow_entity updates
for wid, new_vid in needs_new.items():
    cur.execute(
        "update workflow_entity set versionId=? , activeVersionId=null, versionCounter=1 where id=?",
        (new_vid, wid),
    )

# Insert missing workflow_history rows for the current versionId
for w in workflows:
    wid = str(w["id"])
    row = cur.execute(
        "select id, versionId, nodes, connections, description from workflow_entity where id=?",
        (wid,),
    ).fetchone()
    if not row:
        continue

    version_id = str(row["versionId"])
    nodes = row["nodes"] or "[]"
    connections = row["connections"] or "{}"
    name = w["name"]
    description = row["description"]

    exists = cur.execute(
        "select 1 from workflow_history where versionId=? and workflowId=?",
        (version_id, wid),
    ).fetchone()
    if exists:
        continue

    cur.execute(
        "insert into workflow_history (versionId, workflowId, authors, nodes, connections, name, description, autosaved) values (?, ?, ?, ?, ?, ?, ?, false)",
        (version_id, wid, author, nodes, connections, name, description),
    )

con.commit()

print("Updated workflows needing new versionId:", len(needs_new))
print("Inserted workflow_history rows:", cur.execute("select count(*) from workflow_history").fetchone()[0])

con.close()
