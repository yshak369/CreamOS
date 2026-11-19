import os
import threading
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

_pool = None
_pool_lock = threading.Lock()


def _connection_settings():
    return {
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
    }


def get_pool():
    """Create the connection pool on first use (so importing the app never
    needs a running database)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=int(os.getenv("DB_POOL_MAX", "10")),
                    **_connection_settings(),
                )
    return _pool


def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def get_connection():
    """A standalone connection (not pooled). Prefer get_cursor()."""
    return psycopg2.connect(**_connection_settings())


@contextmanager
def get_cursor():
    """Yield a dict cursor inside one transaction.

    Commits when the block finishes, rolls back on any error, and always
    returns the connection to the pool.
    """
    pool = get_pool()
    connection = pool.getconn()
    broken = False
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            yield cursor
        connection.commit()
    except psycopg2.OperationalError:
        broken = True
        raise
    except Exception:
        connection.rollback()
        raise
    finally:
        pool.putconn(connection, close=broken or connection.closed != 0)
