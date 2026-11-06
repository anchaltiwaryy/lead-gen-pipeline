# Local-First Storage & Cloudflare R2 Backup

To maintain 100% privacy and zero repository bloat, `leads.db` is strictly git-ignored and synchronized via Cloudflare R2:

```bash
# Pull remote snapshot
python sync_r2.py pull

# Push updated snapshot
python sync_r2.py push
```
