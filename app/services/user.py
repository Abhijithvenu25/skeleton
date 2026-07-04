"""User CRUD service. Public — no auth required (superadmin-only in the UI).

Mirrors AuthService / RoleService patterns: pre-check -> write ->
IntegrityError -> ConflictError. The global IntegrityError handler in
app.core.exceptions already maps `ix_users_email` -> "Email already
registered"; the explicit catches here produce the same message but
let us raise cleanly without going through the global handler.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from sqlalchemy import func, or_, select, delete
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- Internals ----------------------------------------------------------

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        user = await User.get_by_id(self.session, user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    @staticmethod
    def _dedupe_role_ids(role_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
        """Detect duplicate role_ids and raise BadRequestError if found.

        Helper exposed for callers that want explicit duplicate
        detection (currently only `create`). Keeping it static so the
        rule is independently testable. Returns the input as a list
        when clean.
        """
        seen: set[uuid.UUID] = set()
        dups: list[uuid.UUID] = []
        for rid in role_ids:
            if rid in seen and rid not in dups:
                dups.append(rid)
            seen.add(rid)
        if dups:
            raise BadRequestError(f"Duplicate role_ids in request: {[str(r) for r in dups]}")
        return list(role_ids)

    async def _validate_role_ids_exist(self, role_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
        """Bulk-fetch the Role rows for `role_ids` and return the IDs that
        were found, or raise NotFoundError on the first missing ID.

        A single SELECT keeps this O(1) round-trips regardless of how
        many grants the admin is making in one call.
        """
        if not role_ids:
            return []
        stmt = select(Role.id).where(Role.id.in_(role_ids))
        found = set(await self.session.scalars(stmt))
        missing = [r for r in role_ids if r not in found]
        if missing:
            raise NotFoundError(f"Roles not found: {[str(r) for r in missing]}")
        return list(role_ids)

    # ---- CRUD ---------------------------------------------------------------

    async def list(
        self, skip: int, limit: int, search: str | None = None
    ) -> tuple[list[User], int]:
        """(items, total). search is a case-insensitive substring match
        on email OR full_name."""
        where = None
        if search:
            pattern = f"%{search.strip()}%"
            where = or_(User.email.ilike(pattern), User.full_name.ilike(pattern))

        count_stmt = select(func.count()).select_from(User)
        list_stmt = select(User).order_by(User.created_at.desc())
        if where is not None:
            count_stmt = count_stmt.where(where)
            list_stmt = list_stmt.where(where)

        total = int(await self.session.scalar(count_stmt) or 0)
        result = await self.session.scalars(list_stmt.offset(skip).limit(limit))
        rows: list[User] = list(result.all())
        return rows, total

    async def get(self, user_id: uuid.UUID) -> User:
        return await self._get_or_404(user_id)

    async def create(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        phone: str | None,
        user_image: str | None,
        is_active: bool,
        is_superuser: bool,
        role_ids: Sequence[uuid.UUID],
    ) -> User:
        normalized = email.lower()
        if await User.get_by_email(self.session, normalized) is not None:
            raise ConflictError("Email already registered")

        # Reject duplicates explicitly so the client gets a clear 400
        # rather than the natural IntegrityError -> 409 path.
        role_ids = self._dedupe_role_ids(role_ids)

        user = User(
            email=normalized,
            hashed_password=hash_password(password),
            full_name=full_name,
            phone=phone,
            user_image=user_image,
            is_active=is_active,
            is_superuser=is_superuser,
        )
        self.session.add(user)
        try:
            # flush() to assign user.id without committing, so we can
            # catch the email-unique race without rolling back a
            # half-built row.
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("Email already registered") from exc

        # Validate all role_ids exist before inserting any grants. This
        # rolls back the user insert if any role is missing — a partial
        # insert state with no FK target is harder to reason about.
        if role_ids:
            try:
                role_ids = await self._validate_role_ids_exist(role_ids)
            except NotFoundError:
                await self.session.rollback()
                raise

            now = self._now()
            self.session.add_all(
                UserRole(
                    user_id=user.id,
                    role_id=rid,
                    granted_at=now,
                    granted_by_id=None,
                )
                for rid in role_ids
            )
            try:
                await self.session.commit()
            except IntegrityError as exc:
                await self.session.rollback()
                raise ConflictError(f"User already has role(s): {role_ids}") from exc
        else:
            await self.session.commit()

        await self.session.refresh(user)
        # Re-prime the selectin-loaded `roles` relationship so the response
        # reflects the just-inserted grants without a second round-trip.
        await self.session.refresh(user, attribute_names=["roles"])
        return user

    async def update(
        self,
        user_id: uuid.UUID,
        *,
        email: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
        user_image: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
        role_ids: Sequence[uuid.UUID] | None = None,
    ) -> User:
        user = await self._get_or_404(user_id)
        if email is not None:
            normalized_email = email.lower()
            if normalized_email != user.email:
                existing = await User.get_by_email(self.session, normalized_email)
                if existing is not None:
                    raise ConflictError("Email already registered")
                user.email = normalized_email
        if full_name is not None:
            user.full_name = full_name
        if password is not None:
            user.hashed_password = hash_password(password)
        if user_image is not None:
            user.user_image = user_image
        if is_active is not None:
            user.is_active = is_active
        if is_superuser is not None:
            user.is_superuser = is_superuser
            
        if role_ids is not None:
            role_ids = self._dedupe_role_ids(role_ids)
            await self._validate_role_ids_exist(role_ids)
            
            await self.session.execute(delete(UserRole).where(UserRole.user_id == user.id))
            
            if role_ids:
                now = self._now()
                self.session.add_all(
                    UserRole(
                        user_id=user.id,
                        role_id=rid,
                        granted_at=now,
                        granted_by_id=None,
                    )
                    for rid in role_ids
                )

        await self.session.commit()
        await self.session.refresh(user)
        if role_ids is not None:
            await self.session.refresh(user, attribute_names=["roles"])
        return user
