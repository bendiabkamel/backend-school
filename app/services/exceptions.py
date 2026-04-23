"""Shared domain/service exceptions for API layer mapping."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-level service exceptions."""


class NotFoundError(DomainError):
    """Raised when an expected entity does not exist."""


class ValidationError(DomainError):
    """Raised when business constraints are violated."""


class PermissionDeniedError(DomainError):
    """Raised when caller does not have permission for an operation."""
