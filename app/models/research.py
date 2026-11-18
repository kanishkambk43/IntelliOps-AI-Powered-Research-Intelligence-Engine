#Keeps our database table structures (models) separated from our API JSON checklists (schemas).
from sqlalchemy import Column, String, Text, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid
from app.db.base import Base # or wherever your declarative Base is

class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(String, nullable=False)
    rewritten_query = Column(String, nullable=True)
    status = Column(String, default="processing")
    result = Column(Text, nullable=True)
    sources = Column(ARRAY(String), default=list)
    
    # --- ADD THIS NEW COLUMN ---
    execution_time_seconds = Column(Float, nullable=True) 
    
    created_at = Column(DateTime, default=datetime.utcnow)