#Contains Pydantic schemas that define the structure and validation rules for incoming and outgoing API data.
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["healthy"], description="Current operational status of the API")
    service: str = Field(..., examples=["IntelliOps Research Intelligence Engine"])
    version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["development"])