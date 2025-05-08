from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class SchemaRequest(BaseModel):
    name: str
    schema: Dict[str, Any]
    schema_type: str = "JSON"


class RetryConfig(BaseModel):
    """Configuration for retry behavior on failed requests."""

    max_attempts: int = Field(default=3, description="Maximum number of retry attempts")
    base_delay: float = Field(
        default=1.0, description="Base delay in seconds between retries"
    )
    max_delay: float = Field(
        default=30.0, description="Maximum delay in seconds between retries"
    )
    backoff_factor: float = Field(
        default=2.0, description="Exponential backoff multiplier"
    )
    retry_status_codes: list[int] = Field(
        default=[408, 429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger a retry",
    )

    @validator("max_attempts")
    def validate_max_attempts(cls, v):
        if v < 1:
            raise ValueError("max_attempts must be at least 1")
        return v


class ResponseData(BaseModel):
    """Model for standardized API response structure."""

    success: bool
    status_code: int
    content: Any
    error_message: Optional[str] = None
