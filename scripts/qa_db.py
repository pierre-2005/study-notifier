"""SQLite fixture context that commits/rolls back and always releases OS handles."""
from contextlib import contextmanager
@contextmanager
def closing_connection(connection):
    try:
        with connection:
            yield connection
    finally:
        connection.close()
