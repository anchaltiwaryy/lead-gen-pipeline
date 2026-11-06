"""Cloudflare R2 serverless backup for the local-first SQLite database.

Zero-leak persistence: `leads.db` stays strictly local/git-ignored, and an
encrypted-at-rest snapshot is pulled from / pushed to a private Cloudflare R2
bucket (10GB free, $0 egress).

Usage:
    python sync_r2.py pull     # fetch leads.db snapshot before a pipeline run
    python sync_r2.py push     # upload leads.db snapshot after a run
    python sync_r2.py ls       # list bucket objects
"""
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from config import (
    DB_PATH,
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_BUCKET,
    R2_REGION,
    R2_SECRET_ACCESS_KEY,
)

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
SNAPSHOT_KEY = "leads.db"


def _client():
    if not (R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY):
        raise RuntimeError(
            "R2 credentials missing. Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY in .env"
        )
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        region_name=R2_REGION,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def pull(db_path: str = DB_PATH) -> str | None:
    """Download the latest snapshot to the local DB path (if remote exists)."""
    client = _client()
    try:
        client.head_object(Bucket=R2_BUCKET, Key=SNAPSHOT_KEY)
    except ClientError:
        print(f"[r2] no snapshot found for '{SNAPSHOT_KEY}'; nothing to pull.")
        return None
    # WAL sidecar files must be closed before a fresh copy.
    for suffix in ("-wal", "-shm"):
        side = f"{db_path}{suffix}"
        if os.path.exists(side):
            try:
                os.remove(side)
            except OSError:
                pass
    client.download_file(R2_BUCKET, SNAPSHOT_KEY, db_path)
    print(f"[r2] pulled '{SNAPSHOT_KEY}' -> {db_path} [{_now()}]")
    return db_path


def push(db_path: str = DB_PATH) -> str:
    """Upload the local DB to R2 (checkpoints the WAL first via close)."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Local database not found at {db_path}")
    client = _client()
    # Close any open connections / flush WAL by reconnecting once.
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.close()
    client.upload_file(db_path, R2_BUCKET, SNAPSHOT_KEY)
    print(f"[r2] pushed {db_path} -> '{SNAPSHOT_KEY}' [{_now()}]")
    return SNAPSHOT_KEY


def ls() -> list[dict]:
    client = _client()
    out = []
    for obj in client.list_objects_v2(Bucket=R2_BUCKET).get("Contents", []):
        out.append({"key": obj["Key"], "size": obj["Size"], "last_modified": str(obj["LastModified"])})
    return out


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "push"
    if action == "pull":
        pull()
    elif action == "push":
        push()
    elif action == "ls":
        for item in ls():
            print(item)
    else:
        print("Usage: python sync_r2.py [pull|push|ls]")
        sys.exit(1)


if __name__ == "__main__":
    main()