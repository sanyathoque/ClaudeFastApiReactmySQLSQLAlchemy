"""Database operations (Create, Read, Update, Delete).

Keeping the DB logic here keeps the route handlers in main.py thin and
makes the queries easy to reuse and test.
This is the "Repository Pattern" — a design pattern that abstracts data access
into a dedicated layer. Benefits:
  - Separation of concerns: HTTP handling (routes) is decoupled from DB logic
  - Testability: you can mock these functions in unit tests without a real DB
  - Reusability: multiple route handlers can call the same query function
  - Maintainability: if you switch from SQLAlchemy to raw SQL, only this file changes
"""

from sqlalchemy.orm import Session
# Session is SQLAlchemy's core unit-of-work abstraction.
# Think of it as a "workspace" or "transaction manager" for database operations:
#   - It tracks all objects you've loaded or created (the "identity map")
#   - It queues up INSERT/UPDATE/DELETE operations (the "unit of work")
#   - It manages database transactions (begin, commit, rollback)
#   - It's NOT a database connection itself, but it wraps one (via an Engine)
# When FastAPI creates a Session (typically via dependency injection with
# `sessionmaker` or `scoped_session`), it gives you a fresh transaction.
# All queries within the same Session share the same transaction context.

from app import models, schemas
# `models` = SQLAlchemy ORM classes that map Python classes to DB tables.
#   Example: models.Item is a class with `__tablename__ = "items"` and Column() definitions.
# `schemas` = Pydantic models used for data validation/serialization (request/response shapes).
#   These enforce API contracts: what fields are required, their types, defaults, etc.
# This separation (SQLAlchemy models vs Pydantic schemas) is crucial:
#   - models.Item knows how to talk to the database
#   - schemas.ItemCreate knows how to validate incoming JSON


def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[models.Item]:
    """
    READ (list) — Retrieve multiple items with pagination.
    
    db.query(models.Item):
        Creates a Query object for the Item table. This doesn't execute SQL yet;
        SQLAlchemy uses "lazy evaluation" — the query is built step by step and
        only executed when you iterate or call .all(), .first(), .count(), etc.
    
    .offset(skip):
        SQL: OFFSET skip — skips the first N rows.
        Used for pagination (e.g., skip=20 gets page 2 if limit=10).
    
    .limit(limit):
        SQL: LIMIT limit — caps the result set size.
        Prevents returning massive datasets and protects server resources.
    
    .all():
        Executes the SQL query and returns a list of Item model instances.
        If no rows match, returns [] (empty list), not None.
    """
    return db.query(models.Item).offset(skip).limit(limit).all()


def get_item(db: Session, item_id: int) -> models.Item | None:
    """
    READ (single) — Retrieve one item by its primary key.
    
    .filter(models.Item.id == item_id):
        Adds a WHERE clause: WHERE items.id = item_id
        .filter() is chainable — you can add multiple conditions with & (AND), | (OR).
        Note: == is overloaded by SQLAlchemy's Column object to produce SQL, not Python bool.
    
    .first():
        Executes the query and returns the first result, or None if no match.
        Uses LIMIT 1 under the hood for efficiency.
        Returns None (not an exception) when not found — this is the "EAFP" pattern
        (Easier to Ask Forgiveness than Permission), letting the caller decide
        whether to raise HTTP 404 or handle gracefully.
    """
    return db.query(models.Item).filter(models.Item.id == item_id).first()


def create_item(db: Session, item: schemas.ItemCreate) -> models.Item:
    """
    CREATE — Insert a new row into the database.
    
    item.model_dump():
        Pydantic v2 method (replaces old .dict() in v1).
        Converts the Pydantic model to a plain Python dict:
        {"name": "foo", "description": "bar", "price": 10.5, ...}
        This dict contains only the fields defined in schemas.ItemCreate.
    
    **item.model_dump():
        Unpacks the dict as keyword arguments to models.Item().
        Equivalent to: models.Item(name="foo", description="bar", price=10.5, ...)
        SQLAlchemy maps these kwargs to table columns.
    
    db.add(db_item):
        Stages the object for insertion. The Session now tracks this instance
        as "pending" — it's in the unit-of-work but NOT yet in the database.
        No SQL is executed here; the INSERT is queued.
    
    db.commit():
        FLUSHES pending changes to the database (generates and executes INSERT),
        then COMMITS the transaction. At this point:
        - The row exists in the DB
        - Auto-generated fields (id, created_at) are populated by the DB
        - The transaction is permanently saved
    
    db.refresh(db_item):
        RELOADS the object from the database. After commit, SQLAlchemy doesn't
        automatically know what the DB generated (e.g., auto-increment id, defaults,
        triggers). refresh() issues a SELECT to fetch the current DB state and
        populates those fields on the Python object.
        Without refresh(), db_item.id would still be None even though the DB assigned one.
    
    Returns the fully populated model instance (with generated fields like id).
    """
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)  # reload so generated fields (id, created_at) are populated
    return db_item


def update_item(
    db: Session, item_id: int, item: schemas.ItemUpdate
) -> models.Item | None:
    """
    UPDATE — Partially or fully modify an existing item.
    
    First, we fetch the existing item. If not found, return None.
    This lets the route handler return HTTP 404 instead of raising an exception here.
    
    item.model_dump(exclude_unset=True):
        This is the key to PARTIAL UPDATES (PATCH semantics):
        - exclude_unset=True tells Pydantic to omit fields the client didn't send
        - Example: if client sends only {"price": 20.0}, the dict is {"price": 20.0}
        - Without this, unset fields would default to None and overwrite existing data!
        This enables true PATCH behavior where you update only specified fields.
    
    for field, value in ... .items():
        Iterates over the provided fields and updates them dynamically.
        setattr(obj, attr, val) is Python's built-in for dynamic attribute assignment.
        This avoids writing repetitive if/else blocks for each field.
    
    db.commit():
        Since db_item is already tracked by the Session (from get_item()),
        SQLAlchemy detects the attribute changes and generates an UPDATE statement.
        The Session's "dirty" tracking knows exactly which fields changed,
        so it can optimize the UPDATE to only modified columns.
    
    db.refresh(db_item):
        Reloads to capture any DB-side changes (triggers, onupdate timestamps).
    """
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
    """
    DELETE — Remove a row from the database.
    
    We fetch first to verify existence. This is a "soft check" pattern:
    - Returns True if deleted successfully
    - Returns False if not found (caller can translate to HTTP 404)
    
    db.delete(db_item):
        Stages the object for deletion. The Session marks it as "pending delete."
        Like add(), this doesn't execute SQL immediately — it's queued in the unit-of-work.
        SQLAlchemy will generate DELETE FROM items WHERE id = ? on commit.
    
    db.commit():
        Executes the DELETE and commits the transaction.
        After commit, db_item is "detached" — still exists in Python memory but
        is no longer associated with the Session or DB. Accessing its attributes
        may still work due to the identity map, but it's considered expired.
    
    Returns bool to indicate success/failure, which is cleaner than raising
    exceptions from the DB layer and lets the API layer decide on HTTP semantics.
    """
    db_item = get_item(db, item_id)
    if db_item is None:
        return False
    db.delete(db_item)
    db.commit()
    return True
