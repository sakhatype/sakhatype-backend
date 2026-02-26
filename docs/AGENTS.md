# Project Documentation: Sakhatype Backend

## Project Instructions

Python 3.12 FastAPI backend. Uses **SQLAlchemy 2.0** (DeclarativeBase), **Pydantic v2** for data validation, and **python-jose** for JWT authentication. Designed for "Sakhatype," a typing performance tracking platform.

---

## Project Structure

- **`main.py`**: Entry point, FastAPI app initialization, CORS/Logging middleware, and API route definitions. [cite: main.py]
- **`models.py`**: SQLAlchemy ORM models (User, Word, TestResult) and database-level logic for user stats. [cite: models.py]
- **`schemas.py`**: Pydantic models for request validation, response serialization, and regex-based field validation. [cite: schemas.py]
- **`crud.py`**: Database abstraction layer; handles all SELECT/INSERT operations and leaderboard logic. [cite: crud.py]
- **`auth.py`**: Security utilities: Argon2 password hashing, JWT token creation, and current user dependency. [cite: auth.py]
- **`database.py`**: SQLAlchemy engine setup, session factory, and database connection lifecycle (`get_db`). [cite: database.py]
- **`config.py`**: Environment variable management using `pydantic-settings`. [cite: config.py]

---

## Code Style

- **Versioning**: Utilizes `FastAPI`, `SQLAlchemy>=2.0`, `Pydantic v2`, and `passlib[argon2]`. [cite: main.py, database.py, schemas.py, auth.py]
- **Naming Conventions**: Uses `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants, and `PascalCase` for classes/Models. [cite: models.py, schemas.py, crud.py]
- **Type Hinting**: All function signatures include explicit type hints for parameters and return types. [cite: crud.py, auth.py]
- **Imports**: Organized by standard library, third-party packages, and local modules. [cite: main.py, crud.py]
- **Error Handling**: API routes return specific `HTTPException` status codes (e.g., 401 for auth, 404 for not found, 409 for conflicts). [cite: main.py, schemas.py]

---

## Logging

- **Implementation**: Uses a per-module logger initialized with `logging.getLogger(__name__)`. [cite: main.py]
- **Middleware**: Includes `CustomLogMiddleware` to intercept `/api/` requests and log user identity (from JWT), HTTP methods, path, and status codes. [cite: main.py]
- **Database Errors**: Critical connection failures and integrity errors are caught and logged during the application lifespan. [cite: main.py]

---

## Deploy

- **Docker**: Recommended base image is `python:3.12-slim` using a non-root user.
- **Environment**: Requires `DATABASE_URL`, `SECRET_KEY`, and `ALLOWED_ORIGINS` to be defined (loaded via `pydantic-settings`). [cite: config.py]
- **Local Run**: Application can be served via `uvicorn` using the FastAPI instance in `main.py`. [cite: main.py]
