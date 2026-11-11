#Separates our API input/output validation rules (schemas) from our database table (models).
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# 1. What the user is allowed to send us when asking a question
class ResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        examples=["Why did our payment service latency spike yesterday?"],
        description="The research question or problem statement to investigate",
    )


# 2. What our API sends back to the user
class ResearchResponse(BaseModel):
    id: uuid.UUID
    query: str
    status: str
    result: str | None = None
    created_at: datetime

    # Allows Pydantic to read data directly from a SQLAlchemy database object
    model_config = ConfigDict(from_attributes=True)