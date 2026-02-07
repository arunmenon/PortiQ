"""Domain exception hierarchy for structured error responses (ADR-NF-007)."""

from __future__ import annotations


class AppException(Exception):
    """Base exception for all domain errors.

    Subclasses set ``code`` and ``status_code`` at the class level; callers
    provide ``message`` and an optional ``details`` list.
    """

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundException(AppException):
    code = "NOT_FOUND"
    status_code = 404


class ConflictException(AppException):
    code = "CONFLICT"
    status_code = 409


class ForbiddenException(AppException):
    code = "FORBIDDEN"
    status_code = 403


class UnauthorizedException(AppException):
    code = "UNAUTHORIZED"
    status_code = 401


class ValidationException(AppException):
    code = "VALIDATION_ERROR"
    status_code = 422


class BusinessRuleException(AppException):
    code = "BUSINESS_RULE_VIOLATION"
    status_code = 422


class RateLimitException(AppException):
    code = "RATE_LIMITED"
    status_code = 429
