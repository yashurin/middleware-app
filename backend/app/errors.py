from typing import Optional


class ForwardError(Exception):
    """Base exception for data forwarding errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        original_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.original_exception = original_exception
        super().__init__(self.message)


class AuthenticationError(ForwardError):
    """Exception raised for authentication-related errors."""

    pass


class MaxRetriesExceededError(ForwardError):
    """Exception raised when maximum retry attempts are exceeded."""

    pass
