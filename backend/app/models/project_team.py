"""Project team model placeholder."""

from sqlalchemy import Column, DateTime, Integer, func

from app.db.base_class import Base


class ProjectTeam(Base):
    __tablename__ = "project_teams"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
