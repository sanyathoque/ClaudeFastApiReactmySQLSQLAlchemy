# FastAPI + React + SQLAlchemy (MySQL)

A full-stack-style project. **This repo currently contains the backend only** —
a FastAPI REST API with SQLAlchemy ORM on a **MySQL** database. The React
frontend is intentionally left out for now; CORS is already enabled so a React
app can call this API later.

## Tech stack

- **FastAPI** — web framework
- **SQLAlchemy** — ORM
- **MySQL** — database (via the `pymysql` driver)
- **Pydantic** — request/response validation

## Project structure

```
.
├── app/
│   ├── __init__.py
│   ├── database.py     # engine, SessionLocal, Base, get_db dependency
│   ├── models.py       # SQLAlchemy ORM models (Item)
│   ├── schemas.py      # Pydantic schemas (ItemCreate, ItemUpdate, ItemResponse)
│   ├── crud.py         # database operations
│   └── main.py         # FastAPI app + routes
├── main.py             # uvicorn entry point
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

1. **Create the database** in MySQL:

   ```sql
   CREATE DATABASE fastapi_db;
   ```

2. **Configure the connection.** Copy `.env.example` to `.env` and set your
   MySQL credentials, or export `DATABASE_URL` directly:

   ```
   DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/fastapi_db
   ```

3. **Install dependencies:**

   ```bash
   python -m venv .venv
   # Windows:  .venv\Scripts\activate
   # macOS/Linux:  source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Run

```bash
python main.py
```

Tables are created automatically on startup. Open the interactive docs at
**http://localhost:8000/docs**.

## Endpoints

| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/`               | Health/welcome message               |
| GET    | `/items`          | List items (`?skip=`, `?limit=`)     |
| GET    | `/items/{id}`     | Get one item                         |
| POST   | `/items`          | Create an item                       |
| PUT    | `/items/{id}`     | Full update                          |
| PATCH  | `/items/{id}`     | Partial update                       |
| DELETE | `/items/{id}`     | Delete an item                       |

### Example: create an item

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Notebook", "description": "A5 dotted", "price": 7.5, "in_stock": true}'
```

## Notes

- Tables are auto-created on startup for convenience. For production, use
  [Alembic](https://alembic.sqlalchemy.org/) migrations instead.
- To use a different database (e.g. PostgreSQL or SQLite), just change
  `DATABASE_URL` — for SQLite use `sqlite:///./app.db` and drop the `pymysql`
  requirement.
