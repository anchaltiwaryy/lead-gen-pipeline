"""Pre-filter: mark leads with unreachable domains as skipped before batch."""
import socket
import sys
sys.path.insert(0, ".")
from db import get_conn

conn = get_conn()
socket.setdefaulttimeout(2)

cur = conn.execute("SELECT id, company, company_domain FROM leads WHERE status='new' ORDER BY created_at LIMIT 100")
rows = cur.fetchall()

skipped = 0
kept = 0
for row in rows:
    domain = row["company_domain"]
    if not domain:
        conn.execute("UPDATE leads SET status='skipped' WHERE id=?", (row["id"],))
        skipped += 1
        continue
    try:
        socket.gethostbyname(domain)
        kept += 1
    except Exception:
        conn.execute("UPDATE leads SET status='skipped' WHERE id=?", (row["id"],))
        skipped += 1
        print(f"  [skip] {row['company']} ({domain}) - unreachable")

conn.commit()
from db import count_by_status
print(f"\nDone. Skipped {skipped} dead leads. {kept} reachable leads remain in 'new'.")
print("DB:", count_by_status(conn))
