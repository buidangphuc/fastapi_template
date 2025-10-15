"""Utilities for managing request identifiers across the application."""

from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

_DEFAULT_REQUEST_ID = "-"
_REQUEST_ID_CTX: ContextVar[str] = ContextVar("request_id", default=_DEFAULT_REQUEST_ID)


def generate_request_id() -> str:
    """Return a new UUID4 string for request tracing."""
    return str(uuid4())


def set_request_id(value: Optional[str]) -> str:
    """Store the request id in context, falling back to a generated value.

    Returns the normalized id to simplify reuse by callers.
    """
    request_id = value or generate_request_id()
    _REQUEST_ID_CTX.set(request_id)
    return request_id


def get_request_id() -> str:
    """Fetch the current request id from context."""
    return _REQUEST_ID_CTX.get()


def clear_request_id() -> None:
    """Reset the request id context to its default placeholder."""
    _REQUEST_ID_CTX.set(_DEFAULT_REQUEST_ID)
