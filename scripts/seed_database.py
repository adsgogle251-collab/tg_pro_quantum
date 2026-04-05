"""
TG PRO QUANTUM - Database Seed Script
Creates admin account, demo user, and sample data.

Usage:
    python scripts/seed_database.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure project root is on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, AsyncSessionLocal, Base
from app.models.database import (
    Client, ClientStatus, ClientPlan,
    Campaign, CampaignStatus, CampaignMode,
    AuditLog, License, LicenseTier, LicenseStatus,
)
from app.api.dependencies import hash_password
from app.utils.helpers import generate_api_key


async def seed(db: AsyncSession) -> None:
    # ── Create tables if they don't exist ────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # ── Admin account ─────────────────────────────────────────────────────────
    existing_admin = await db.execute(
        select(Client).where(Client.email == "admin@example.com")
    )
    if not existing_admin.scalar_one_or_none():
        admin = Client(
            name="Admin User",
            email="admin@example.com",
            hashed_password=hash_password("Admin@123"),
            api_key=generate_api_key(),
            is_admin=True,
            status=ClientStatus.active,
            plan_type=ClientPlan.enterprise,
        )
        db.add(admin)
        await db.flush()
        await db.refresh(admin)
        print(f"✅ Admin created  → email: admin@example.com  password: Admin@123  id: {admin.id}")
    else:
        admin_row = (await db.execute(select(Client).where(Client.email == "admin@example.com"))).scalar_one()
        admin = admin_row
        print(f"ℹ️  Admin already exists (id={admin.id})")

    # ── Demo user account ─────────────────────────────────────────────────────
    existing_user = await db.execute(
        select(Client).where(Client.email == "user@example.com")
    )
    if not existing_user.scalar_one_or_none():
        demo = Client(
            name="Demo User",
            email="user@example.com",
            hashed_password=hash_password("User@123"),
            api_key=generate_api_key(),
            is_admin=False,
            status=ClientStatus.active,
            plan_type=ClientPlan.pro,
        )
        db.add(demo)
        await db.flush()
        await db.refresh(demo)
        print(f"✅ Demo user created → email: user@example.com  password: User@123  id: {demo.id}")
    else:
        demo_row = (await db.execute(select(Client).where(Client.email == "user@example.com"))).scalar_one()
        demo = demo_row
        print(f"ℹ️  Demo user already exists (id={demo.id})")

    # ── Sample campaign ───────────────────────────────────────────────────────
    existing_campaign = await db.execute(
        select(Campaign).where(Campaign.name == "Welcome Campaign")
    )
    if not existing_campaign.scalar_one_or_none():
        campaign = Campaign(
            client_id=admin.id,
            name="Welcome Campaign",
            message_text="Welcome to TG PRO QUANTUM! 🚀",
            status=CampaignStatus.draft,
            mode=CampaignMode.once,
            delay_min=27.0,
            delay_max=33.0,
        )
        db.add(campaign)
        await db.flush()
        print(f"✅ Sample campaign created (id={campaign.id})")
    else:
        print("ℹ️  Sample campaign already exists")

    # ── Sample license ────────────────────────────────────────────────────────
    existing_license = await db.execute(
        select(License).where(License.client_id == admin.id)
    )
    if not existing_license.scalar_one_or_none():
        from datetime import datetime, timedelta, timezone
        import secrets as _secrets
        lic = License(
            key=_secrets.token_urlsafe(32),
            client_id=admin.id,
            tier=LicenseTier.enterprise,
            status=LicenseStatus.active,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            max_accounts=100,
            max_campaigns=50,
        )
        db.add(lic)
        await db.flush()
        print(f"✅ Sample license created (id={lic.id})")
    else:
        print("ℹ️  License for admin already exists")

    # ── Audit log entry ───────────────────────────────────────────────────────
    audit = AuditLog(
        client_id=admin.id,
        action="seed",
        resource="database",
        details={"message": "Database seeded via seed_database.py"},
    )
    db.add(audit)

    await db.commit()
    print("\n✅ Database seeding complete!")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
