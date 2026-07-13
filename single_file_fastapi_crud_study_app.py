"""
Single-file FastAPI + SQLAlchemy + Pydantic CRUD study app.

Why this file exists:
    The real project is modular:

        app/database.py
        app/models.py
        app/schemas.py
        app/crud.py
        app/main.py
        main.py

    That structure is good for real projects, but this file puts the whole
    backend in one place so you can memorize the full flow for interviews.

Memory sentence:
    FastAPI receives the request, Pydantic validates the data, Depends gives
    the route a database session, SQLAlchemy talks to the database, and
    FastAPI serializes the response.

Run:
    python single_file_fastapi_crud_study_app.py

Default database:
    sqlite:///./fastapi_study_app.db

Optional MySQL database:
    Set DATABASE_URL in .env:
    DATABASE_URL=mysql+pymysql://root:password@localhost:3306/fastapi_db

Open docs:
    http://localhost:8000/docs

Endpoints:
    GET    /              health check
    GET    /items         list items
    GET    /items/{id}    read one item
    POST   /items         create item
    PUT    /items/{id}    replace item
    PATCH  /items/{id}    partially update item
    DELETE /items/{id}    delete item

Example JSON:
    {
        "name": "Notebook",
        "description": "A5 dotted notebook",
        "price": 7.5,
        "in_stock": true
    }
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine, func
from sqlalchemy.orm import Session, declarative_base, sessionmaker


# ============================================================================
# 1. CONFIGURATION
# ============================================================================
# Interview idea:
#   Read configuration from environment variables. Do not hard-code real
#   usernames, passwords, or production database URLs in source code.

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fastapi_study_app.db")

engine_options = {"pool_pre_ping": True, "echo": False}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}


# ============================================================================
# 2. DATABASE CONNECTION
# ============================================================================
# Interview idea:
#   engine = database connection manager
#   SessionLocal = factory that creates database sessions
#   Base = parent class for SQLAlchemy ORM models

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that gives each request a DB session.

    Why yield?
        FastAPI runs the code before yield at the start of the request.
        It gives the yielded db session to the route.
        Then it runs the finally block after the request finishes.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# 3. SQLALCHEMY MODEL
# ============================================================================
# Interview idea:
#   The ORM model is a Python class that maps to a database table.
#   One Item object represents one row in the items table.

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False, default=0.0)
    in_stock = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ============================================================================
# 4. PYDANTIC SCHEMAS
# ============================================================================
# Interview idea:
#   SQLAlchemy models describe database rows.
#   Pydantic schemas describe API input and output.
#   Keep them separate.

class ItemBase(BaseModel):
    name: str
    description: str | None = None
    price: float = 0.0
    in_stock: bool = True


class ItemCreate(ItemBase):
    """POST and PUT use this schema. name is required."""


class ItemUpdate(BaseModel):
    """PATCH uses this schema. Every field is optional."""

    name: str | None = None
    description: str | None = None
    price: float | None = None
    in_stock: bool | None = None


class ItemResponse(ItemBase):
    """Responses include database-generated fields."""

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # This lets Pydantic read fields from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 5. CRUD FUNCTIONS
# ============================================================================
# Interview idea:
#   Keep database logic in functions so route handlers stay small.
#   This is often called a repository-style layer.

def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[Item]:
    return db.query(Item).offset(skip).limit(limit).all()


def get_item(db: Session, item_id: int) -> Item | None:
    return db.query(Item).filter(Item.id == item_id).first()


def create_item(db: Session, item: ItemCreate) -> Item:
    # model_dump() converts the Pydantic object to a dict.
    # ** unpacks that dict into keyword arguments for Item(...).
    db_item = Item(**item.model_dump())

    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def update_item(db: Session, item_id: int, item: ItemUpdate) -> Item | None:
    db_item = get_item(db, item_id)
    if db_item is None:
        return None

    # exclude_unset=True is the key PATCH idea:
    # update only fields that the client actually sent.
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


# ============================================================================
# 6. FASTAPI APP SETUP
# ============================================================================
# Interview idea:
#   FastAPI owns the HTTP layer.
#   It automatically validates request bodies with Pydantic.
#   It automatically generates OpenAPI docs at /docs.

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Good for learning. In production, use Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Single-file FastAPI SQLAlchemy CRUD Study App",
    lifespan=lifespan,
)


# CORS lets a browser frontend, such as React, call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 7. ROUTES
# ============================================================================
# Compare FastAPI to Flask:
#   Flask: manually parse JSON and manually validate.
#   FastAPI: function parameters and type hints drive validation automatically.

@app.get("/")
def read_root():
    return {"message": "Single-file FastAPI SQLAlchemy CRUD API", "docs": "/docs"}


@app.get("/items", response_model=list[ItemResponse])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List items with pagination.

    FastAPI reads skip and limit from query parameters:
        /items?skip=10&limit=50

    Because they are typed as int, FastAPI converts and validates them.
    """

    return get_items(db, skip=skip, limit=limit)


@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """Read one item by path parameter.

    FastAPI reads item_id from the URL:
        /items/42

    Because item_id is typed as int, FastAPI converts and validates it.
    """

    db_item = get_item(db, item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return db_item


@app.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item_route(item: ItemCreate, db: Session = Depends(get_db)):
    """Create an item.

    FastAPI automatically validates the JSON body against ItemCreate.
    If the body is invalid, FastAPI returns a validation error before this
    function runs.
    """

    return create_item(db, item)


@app.put("/items/{item_id}", response_model=ItemResponse)
def replace_item_route(
    item_id: int,
    item: ItemCreate,
    db: Session = Depends(get_db),
):
    """Replace an item.

    PUT means full replacement, so this route uses ItemCreate.
    That means name is required.
    """

    update_data = ItemUpdate(**item.model_dump())
    updated = update_item(db, item_id, update_data)

    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return updated


@app.patch("/items/{item_id}", response_model=ItemResponse)
def update_item_route(
    item_id: int,
    item: ItemUpdate,
    db: Session = Depends(get_db),
):
    """Partially update an item.

    PATCH means partial update, so this route uses ItemUpdate.
    All fields are optional.
    """

    updated = update_item(db, item_id, item)

    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")

    return updated


@app.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_item_route(item_id: int, db: Session = Depends(get_db)):
    deleted = delete_item(db, item_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"success": True, "message": f"Item {item_id} deleted"}


# ============================================================================
# 8. RUN SERVER
# ============================================================================
# Interview idea:
#   uvicorn is the ASGI server that runs FastAPI.

if __name__ == "__main__":
    uvicorn.run("single_file_fastapi_crud_study_app:app", host="0.0.0.0", port=8000, reload=True)
