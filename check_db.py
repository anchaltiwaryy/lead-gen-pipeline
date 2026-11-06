"""Quick health check of the local leads database.

Usage:
    python check_db.py
"""
from db import get_conn, count_by_status


def main() -> None:
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
        scraped = conn.execute(
            "SELECT status, COUNT(*) AS n FROM leads "
            "WHERE posting_text IS NOT NULL AND posting_text != '' GROUP BY status"
        ).fetchall()
        print(f"Total leads: {total}")
        print(f"By status:   {count_by_status(conn)}")
        print(f"Scraped (has posting_text) by status: { {r['status']: r['n'] for r in scraped} }")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
