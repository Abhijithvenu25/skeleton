"""Contact service."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.contact import Contact
from app.models.user import User
from app.schemas.crm.contact import ContactIn, ContactPatch
from app.services.crm._common import (
    apply_audit_create,
    apply_audit_soft_delete,
    apply_audit_update,
    commit,
    flush_and_refresh,
    paginate,
)


class ContactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        company_id: uuid.UUID | None = None,
    ) -> tuple[list[Contact], int]:
        where = [Contact.deleted_at.is_(None)]
        if company_id is not None:
            where.append(Contact.company_id == company_id)
        return await paginate(
            self.session,
            Contact,
            page=page,
            size=size,
            order_by=Contact.full_name,
            where=where,
        )

    async def get_by_id(self, contact_id: uuid.UUID) -> Contact:
        contact = await Contact.get_by_id(self.session, contact_id)
        if contact is None or contact.deleted_at is not None:
            raise NotFoundError(f"Contact {contact_id} not found")
        return contact

    async def create(self, payload: ContactIn, *, actor: User) -> Contact:
        contact = Contact(**payload.model_dump())
        apply_audit_create(contact, actor=actor)
        self.session.add(contact)
        await flush_and_refresh(self.session, contact)
        return contact

    async def update(
        self, contact_id: uuid.UUID, payload: ContactPatch, *, actor: User
    ) -> Contact:
        contact = await self.get_by_id(contact_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(contact, field, value)
        apply_audit_update(contact, actor=actor)
        await commit(self.session)
        return contact

    async def soft_delete(self, contact_id: uuid.UUID, *, actor: User) -> None:
        contact = await self.get_by_id(contact_id)
        apply_audit_soft_delete(contact, actor=actor)
        await commit(self.session)
