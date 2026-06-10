"""Idempotent seed for local development: ensures an admin user exists."""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


async def seed() -> int:
    if not settings.is_local:
        print("Seed is only for local/dev envs", file=sys.stderr)
        return 1

    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == settings.seed_admin_email.lower())
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin user already exists: {existing.email}")
            return 0

        admin = User(
            email=settings.seed_admin_email.lower(),
            hashed_password=hash_password(settings.seed_admin_password),
            full_name="Admin",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Created admin user: {admin.email} (password: {settings.seed_admin_password})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(seed()))
