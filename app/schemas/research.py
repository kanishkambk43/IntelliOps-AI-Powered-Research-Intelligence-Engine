from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field

class ResearchRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=5, 
        max_length=1000,
        description="The engineering or research question to investigate.",
        examples=["Why did our payment service latency spike yesterday?"],
    )

class ResearchResponse(BaseModel):
    id: uuid.UUID
    query: str
    rewritten_query: str | None = None
    status: str
    result: str | None = None
    sources: list[str] = Field(default_factory=list)
    execution_time_seconds: float | None = Field(
        default=None, 
        description="How long the AI took to complete the task in seconds"
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)