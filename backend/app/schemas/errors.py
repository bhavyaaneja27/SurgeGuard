from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standard JSON error structure conforming to PRD Section 12.1:
    { "error_code": "...", "message": "...", "details": ... }
    """
    error_code: str = Field(..., description="Machine-readable error identifier")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[Any] = Field(default=None, description="Optional error metadata or validation issues")
