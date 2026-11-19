import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg2 import errors

from .database import close_pool, get_cursor
from .routers import analytics, customers, expenses, orders, payments, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_pool()


app = FastAPI(title="CreamOS API", lifespan=lifespan)

cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database rule violations are the caller's mistake, not a server crash.
@app.exception_handler(errors.ForeignKeyViolation)
async def foreign_key_violation(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "A referenced record does not exist."},
    )


@app.exception_handler(errors.CheckViolation)
async def check_violation(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "A value is outside its allowed range."},
    )


for module in (customers, products, orders, payments, expenses, analytics):
    app.include_router(module.router)


@app.get("/")
def home():
    return {"message": "CreamOS API is running"}


@app.get("/test-db")
def test_db():
    with get_cursor() as cursor:
        cursor.execute("SELECT 1;")

    return {"message": "PostgreSQL connection successful"}
