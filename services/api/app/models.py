import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Repo(Base):
    __tablename__ = "repos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    source = Column(String, nullable=False)  # github or local
    status = Column(String, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())