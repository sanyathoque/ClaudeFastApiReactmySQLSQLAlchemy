from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the tables on startup if they don't exist yet.
    # (For real projects, prefer migrations with Alembic.)
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FastAPI + SQLAlchemy CRUD (MySQL)", lifespan=lifespan)

# CORS so a React frontend (e.g. http://localhost:3000 or :5173) can call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "FastAPI + SQLAlchemy + MySQL CRUD API", "docs": "/docs"}


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

@app.get("/items", response_model=list[schemas.ItemResponse])
def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Return all items, with optional ?skip= and ?limit= pagination."""
    return crud.get_items(db, skip=skip, limit=limit)


@app.get("/items/{item_id}", response_model=schemas.ItemResponse)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = crud.get_item(db, item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

@app.post("/items", response_model=schemas.ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db, item)


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

@app.put("/items/{item_id}", response_model=schemas.ItemResponse)
def replace_item(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    """Full update: all fields required (ItemCreate)."""
    updated = crud.update_item(db, item_id, schemas.ItemUpdate(**item.model_dump()))
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated


@app.patch("/items/{item_id}", response_model=schemas.ItemResponse)
def update_item(item_id: int, item: schemas.ItemUpdate, db: Session = Depends(get_db)):
    """Partial update: only the fields the client sends are changed."""
    updated = crud.update_item(db, item_id, item)
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

@app.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"success": True, "message": f"Item {item_id} deleted"}
