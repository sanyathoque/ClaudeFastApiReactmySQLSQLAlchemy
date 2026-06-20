"""Database operations (Create, Read, Update, Delete).

Keeping the DB logic here keeps the route handlers in main.py thin and
makes the queries easy to reuse and test.
"""

from sqlalchemy.orm import Session

from app import models, schemas


def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[models.Item]:
    return db.query(models.Item).offset(skip).limit(limit).all()


def get_item(db: Session, item_id: int) -> models.Item | None:
    return db.query(models.Item).filter(models.Item.id == item_id).first()


def create_item(db: Session, item: schemas.ItemCreate) -> models.Item:
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)  # reload so generated fields (id, created_at) are populated
    return db_item


def update_item(
    db: Session, item_id: int, item: schemas.ItemUpdate
) -> models.Item | None:
    db_item = get_item(db, item_id)
    if db_item is None:
        return None
    # exclude_unset=True -> only overwrite the fields the client actually sent.
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, field, value)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> bool:
    db_item = get_item(db, item_id)
    if db_item is None:
        return False
    db.delete(db_item)
    db.commit()
    return True
