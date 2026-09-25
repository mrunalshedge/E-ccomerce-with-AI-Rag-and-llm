import enum
from datetime import UTC, datetime

from sqlalchemy import Enum


def utcnow() -> datetime:
    return datetime.now(UTC)


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """A PostgreSQL enum type that stores the members' values ("placed"), not their names ("PLACED")."""
    return Enum(enum_cls, name=name, values_callable=lambda members: [m.value for m in members])
