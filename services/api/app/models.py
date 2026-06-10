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

class RepoFile(Base):
    __tablename__ = "repo_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), nullable=False)
    path = Column(String, nullable=False)
    language = Column(String)
    content_hash = Column(String)
    parsed_at = Column(DateTime(timezone=True), nullable=True)