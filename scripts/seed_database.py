"""
TG PRO QUANTUM - Database Seed Script
Creates admin account, demo users, sample campaigns, accounts, and more.

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

from datetime import datetime, timedelta, timezone
import secrets as _secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, AsyncSessionLocal, Base
from app.models.database import (
    Client, ClientStatus, ClientPlan,
    Campaign, CampaignStatus, CampaignMode,
    TelegramAccount, AccountStatus,
    AuditLog, License, LicenseTier, LicenseStatus,
)
from app.api.dependencies import hash_password
from app.utils.helpers import generate_api_key


async def seed(db: AsyncSession) -> None:
    # -- Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # -- Admin account
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
        print(f"Admin created -> id={admin.id}")
    else:
        admin = (await db.execute(select(Client).where(Client.email == "admin@example.com"))).scalar_one()
        print(f"Admin already exists (id={admin.id})")

    # -- Demo user accounts
    demo_users = [
        ("Demo User",   "user@example.com",  "User@123",  ClientPlan.pro),
        ("Alice Smith", "alice@example.com", "Alice@123", ClientPlan.pro),
        ("Bob Johnson", "bob@example.com",   "Bob@1234",  ClientPlan.starter),
        ("Carol White", "carol@example.com", "Carol@123", ClientPlan.enterprise),
    ]
    created_users = [admin]
    for name, email, password, plan in demo_users:
        existing = (await db.execute(select(Client).where(Client.email == email))).scalar_one_or_none()
        if not existing:
            user = Client(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                api_key=generate_api_key(),
                is_admin=False,
                status=ClientStatus.active,
                plan_type=plan,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            created_users.append(user)
            print(f"User created -> {email} (id={user.id})")
        else:
            created_users.append(existing)
            print(f"User {email} already exists (id={existing.id})")

    demo = created_users[1]

    # -- Sample campaigns for admin
    campaigns_data = [
        ("Welcome Campaign",    "Welcome to TG PRO QUANTUM!", CampaignStatus.completed, 4200, 130),
        ("Summer Sale",         "Exclusive summer deals!",    CampaignStatus.running,   1200, 40),
        ("Newsletter Q4 2024",  "Our Q4 newsletter.",        CampaignStatus.draft,     0,    0),
        ("Re-engagement Blast", "We miss you!",              CampaignStatus.paused,    650,  25),
        ("Flash Deal Promo",    "24-hour flash sale!",       CampaignStatus.failed,    300,  300),
    ]
    for cname, msg, status, sent, failed in campaigns_data:
        existing = (await db.execute(select(Campaign).where(
            Campaign.name == cname, Campaign.client_id == admin.id
        ))).scalar_one_or_none()
        if not existing:
            camp = Campaign(
                client_id=admin.id,
                name=cname,
                message_text=msg,
                status=status,
                mode=CampaignMode.once,
                delay_min=27.0,
                delay_max=33.0,
                sent_count=sent,
                failed_count=failed,
                total_targets=sent + failed + 500,
            )
            db.add(camp)
            await db.flush()
            print(f"Campaign '{cname}' created (id={camp.id})")

    # -- Demo user campaigns
    for cname, msg, status in [
        ("My First Campaign", "Hello from Demo User!", CampaignStatus.draft),
        ("Test Broadcast",    "Testing broadcast...",  CampaignStatus.completed),
    ]:
        existing = (await db.execute(select(Campaign).where(
            Campaign.name == cname, Campaign.client_id == demo.id
        ))).scalar_one_or_none()
        if not existing:
            camp = Campaign(
                client_id=demo.id,
                name=cname,
                message_text=msg,
                status=status,
                mode=CampaignMode.once,
                delay_min=27.0,
                delay_max=33.0,
            )
            db.add(camp)
            await db.flush()
            print(f"Demo campaign '{cname}' created")

    # -- Sample Telegram accounts
    for phone, name, status, health in [
        ("+10000000001", "alice_bot",   AccountStatus.active,   95.0),
        ("+10000000002", "bob_sender",  AccountStatus.active,   88.0),
        ("+10000000003", "charlie_tg",  AccountStatus.banned,   0.0),
        ("+10000000004", "delta_proxy", AccountStatus.inactive, 45.0),
        ("+10000000005", "echo_main",   AccountStatus.active,   72.0),
    ]:
        existing = (await db.execute(select(TelegramAccount).where(
            TelegramAccount.client_id == admin.id,
            TelegramAccount.phone == phone
        ))).scalar_one_or_none()
        if not existing:
            acc = TelegramAccount(
                client_id=admin.id,
                name=name,
                phone=phone,
                status=status,
                health_score=health,
            )
            db.add(acc)
            await db.flush()
            print(f"Account {phone} ({name}) created")

    # -- Sample licenses
    for user_obj, tier, max_acc, max_camp in [
        (admin,           LicenseTier.enterprise, 100, 50),
        (created_users[1], LicenseTier.pro,        20,  10),
    ]:
        existing = (await db.execute(select(License).where(
            License.client_id == user_obj.id
        ))).scalar_one_or_none()
        if not existing:
            lic = License(
                key=_secrets.token_urlsafe(32),
                client_id=user_obj.id,
                tier=tier,
                status=LicenseStatus.active,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                max_accounts=max_acc,
                max_campaigns=max_camp,
            )
            db.add(lic)
            await db.flush()
            print(f"License ({tier.value}) created for user id={user_obj.id}")

    # -- Audit log entries
    for client_id, action, resource_type, resource_id, details in [
        (admin.id, "seed",            "database", "1",   {"message": "Database seeded"}),
        (admin.id, "create_campaign", "campaign", "1",   {"name": "Welcome Campaign"}),
        (admin.id, "create_account",  "account",  "1",   {"phone": "+10000000001"}),
        (demo.id,  "register",        "client",   None,  {"email": "user@example.com"}),
        (demo.id,  "login",           "session",  None,  {"ip": "127.0.0.1"}),
    ]:
        db.add(AuditLog(
            client_id=client_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        ))

    await db.commit()
    print("\nDatabase seeding complete!")
    print("\nLogin credentials:")
    print("  Admin:  admin@example.com / Admin@123")
    print("  User 1: user@example.com  / User@123")
    print("  User 2: alice@example.com / Alice@123")
    print("  User 3: bob@example.com   / Bob@1234")


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
