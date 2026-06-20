from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func

from app.database import Base


class Item(Base):
    """A single item stored in the MySQL `items` table."""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    in_stock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
