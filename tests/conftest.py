"""Test setup.

The tests wipe and rebuild their database, so they only run against a
database named in TEST_DB_NAME (never DB_NAME):

    createdb creamos_test
    TEST_DB_NAME=creamos_test pytest

Connection details (host, port, user, password) come from the usual DB_*
variables / .env file.
"""

import os
from pathlib import Path

import pytest

TEST_DB_NAME = os.getenv("TEST_DB_NAME")

if not TEST_DB_NAME:
    pytest.skip(
        "Set TEST_DB_NAME to a throwaway database to run the tests.",
        allow_module_level=True,
    )

# Point the app at the test database before it is imported.
os.environ["DB_NAME"] = TEST_DB_NAME

from fastapi.testclient import TestClient  # noqa: E402

from backend.database import get_connection  # noqa: E402
from backend.main import app  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = (ROOT / "database" / "schema.sql").read_text(encoding="utf-8")
MIGRATION = (
    ROOT / "database" / "migrations" / "001_sync_schema_with_backend.sql"
).read_text(encoding="utf-8")


def run_sql(sql):
    connection = get_connection()
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(sql)
    finally:
        connection.close()


@pytest.fixture
def db():
    """A freshly created database for each test."""
    run_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    run_sql(SCHEMA)
    return run_sql


@pytest.fixture
def client(db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed(client):
    """One customer and one product (sells at 499, costs 120)."""
    client.post("/customers", json={
        "name": "Asha", "phone": "9000000001",
        "address": "Kochi", "pincode": "682001",
    })
    client.post("/products", json={
        "name": "Night Cream", "selling_price": 499, "cost_price": 120,
    })
    return client
