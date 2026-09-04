class AppError(Exception):
    """Base class for all application-specific errors."""


class NotFoundError(AppError):
    """A requested entity does not exist."""


class ValidationError(AppError):
    """Input failed a domain/application-level validation rule."""


class ExternalServiceError(AppError):
    """A call to an external dependency (proxy provider, target site, etc.) failed."""
