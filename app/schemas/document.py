# Defines the input/output rules for uploading company knowledge and running semantic vector searches
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# 1. Input when uploading a new document or incident report
class DocumentCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        examples=["Oct 2026 Checkout Service Outage"],
    )
    source: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["incident-report-oct-2026.md"],
    )
    content: str = Field(
        ...,
        min_length=10,
        examples=[
            "On October 14, 2026, the checkout service experienced a 400% latency spike "
            "because the Redis cache cluster ran out of memory at 5,000 requests/sec. "
            "Increasing maxmemory-policy to allkeys-lru resolved the outage."
        ],
    )


# 2. Input when searching the knowledge base by meaning
class DocumentSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        examples=["Why did the checkout service slow down?"],
    )
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of most similar document chunks to return",
    )


# 3. Output returned to the user (notice we DO NOT return the 384 raw numbers!)
class DocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    source: str #where the document came from.
    content: str #This is the core payload that the frontend UI or AI model reads, displays, or processes
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)