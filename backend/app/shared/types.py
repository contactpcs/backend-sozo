"""Shared types and type aliases."""
from typing import TypeVar, Generic, TypeAlias
from uuid import UUID

# Type variables for generics
T = TypeVar("T")
ID: TypeAlias = UUID

# HTTP response types
PaginatedResponse = dict[str, any]
