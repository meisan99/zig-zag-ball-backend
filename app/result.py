"""
Typed Result wrapper, in the same spirit as a C# Result<T>:
services return a Result instead of raising for expected failure cases
(not found, validation, conflict), so routers can decide the HTTP
response instead of relying on exception control flow.

Unexpected errors (DB down, bugs) still raise normally and are handled
by a global exception handler in main.py — Result is only for
*expected* business-logic outcomes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION = "VALIDATION"


@dataclass
class Result(Generic[T]):
    success: bool
    value: Optional[T] = None
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None

    @staticmethod
    def ok(value: T) -> "Result[T]":
        return Result(success=True, value=value)

    @staticmethod
    def fail(error_code: ErrorCode, error_message: str) -> "Result[T]":
        return Result(success=False, error_code=error_code, error_message=error_message)
