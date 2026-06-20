from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Shared fields used by both create and read.
class ItemBase(BaseModel):
    name: str
    description: str | None = None
    price: float = 0.0
    in_stock: bool = True


# Request body for creating an item (POST).
class ItemCreate(ItemBase):
    pass


# Request body for a partial update (PATCH) - every field is optional.
class ItemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    in_stock: bool | None = None


# What the API sends back. from_attributes lets Pydantic read ORM objects.
class ItemResponse(ItemBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
