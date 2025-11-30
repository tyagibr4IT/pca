import asyncio
import argparse
from typing import Dict, Any
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.models.models import Tenant

REQUIRED_KEYS = ["tenantId", "clientId", "clientSecret"]
PLACEHOLDERS = {
    "tenantId": "REPLACE_ME_TENANT_ID",
    "clientId": "REPLACE_ME_CLIENT_ID",
    "clientSecret": "REPLACE_ME_CLIENT_SECRET",
}

def needs_repair(meta: Dict[str, Any]) -> bool:
    if not meta:
        return True
    provider = (meta.get("provider") or "").lower()
    if provider != "azure":
        return False
    # Missing any required key
    for k in REQUIRED_KEYS:
        if not meta.get(k):
            return True
    return False

async def repair(apply: bool, dry_run: bool):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Tenant))
        tenants = result.scalars().all()
        to_update = []
        for t in tenants:
            meta = t.metadata_json or {}
            if needs_repair(meta):
                # Only consider rows that are meant to be azure (by existing provider or name heuristic)
                provider = (meta.get("provider") or "").lower()
                name_lower = t.name.lower()
                if provider == "azure" or "azure" in name_lower:
                    new_meta = dict(meta)  # copy existing
                    new_meta.setdefault("provider", "azure")
                    for k in REQUIRED_KEYS:
                        if not new_meta.get(k):
                            new_meta[k] = PLACEHOLDERS[k]
                    to_update.append((t, meta, new_meta))
        print(f"Found {len(to_update)} azure tenant(s) needing repair")
        for orig, old_meta, new_meta in to_update:
            print(f" - ID {orig.id} Name '{orig.name}': old={old_meta} -> new={new_meta}")
        if apply and to_update and not dry_run:
            for t, old_meta, new_meta in to_update:
                t.metadata_json = new_meta
            await session.commit()
            print("Applied repairs.")
        else:
            print("No changes applied (use --apply to write, --no-dry-run to disable dry-run).")

async def main():
    parser = argparse.ArgumentParser(description="Repair Azure tenant metadata placeholders.")
    parser.add_argument("--apply", action="store_true", help="Persist changes to the database.")
    parser.add_argument("--no-dry-run", action="store_true", help="Disable dry-run (required with --apply).")
    args = parser.parse_args()
    await repair(apply=args.apply, dry_run=not args.no_dry_run)

if __name__ == "__main__":
    asyncio.run(main())
