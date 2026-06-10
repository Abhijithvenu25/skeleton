"""Data access layer (DB-only, no business logic)."""

from app.repositories.customer import CustomerRepository
from app.repositories.user import UserRepository

__all__ = ["CustomerRepository", "UserRepository"]
