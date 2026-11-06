"""Export leads from leads.db to a CSV file and print a summary table.

Usage:
    python view_leads.py              # all leads
    python view_leads.py qualified    # only qualified leads
    python view_leads.py new          # only new leads
"""
import csv
import sys
import os
from db import get_conn

EXPORT_PATH = "leads_export.csv"
COLUMNS = [
    "id", "company", "company_domain", "role_title", "job_url",
    "fit_score", "fit_reason", "contact_name", "email",
    "email_confidence", "status", "created_at",
]


def export_leads(status_filter: str | None = None) -> str:
    conn = get_conn()
    if status_filter:
        cur = conn.execute(
            "SELECT * FROM leads WHERE status = ? ORDER BY fit_score DESC, created_at",
            (status_filter,),
        )
    else:
        cur = conn.execute("SELECT * FROM leads ORDER BY status, fit_score DESC, created_at")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not rows:
        print(f"No leads found{' with status=' + status_filter if status_filter else ''}.")
        return ""

    with open(EXPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    # Print a compact summary table to terminal
    print(f"\n{'='*110}")
    print(f"{'ID':>4}  {'Status':<12}  {'Score':>5}  {'Company':<25}  {'Role':<30}  {'Domain':<20}  {'Contact':<15}")
    print(f"{'-'*110}")
    for r in rows:
        print(
            f"{r.get('id',''):>4}  "
            f"{(r.get('status') or ''):<12}  "
            f"{(r.get('fit_score') or ''):>5}  "
            f"{(r.get('company') or '')[:25]:<25}  "
            f"{(r.get('role_title') or '')[:30]:<30}  "
            f"{(r.get('company_domain') or '')[:20]:<20}  "
            f"{(r.get('contact_name') or '')[:15]:<15}"
        )
    print(f"{'='*110}")

    # Summary counts
    from collections import Counter
    counts = Counter(r.get("status") for r in rows)
    print(f"\nTotal: {len(rows)} leads  |  " + "  |  ".join(f"{s}: {n}" for s, n in sorted(counts.items())))
    print(f"Exported to: {os.path.abspath(EXPORT_PATH)}\n")
    return os.path.abspath(EXPORT_PATH)


if __name__ == "__main__":
    filt = sys.argv[1] if len(sys.argv) > 1 else None
    export_leads(filt)
