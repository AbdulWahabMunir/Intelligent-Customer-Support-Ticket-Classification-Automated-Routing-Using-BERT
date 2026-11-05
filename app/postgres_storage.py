"""Durable PostgreSQL storage with the same ticket/feedback contract as SQLite."""
from contextlib import contextmanager

from app.storage import TicketStore


class Record(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def record_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    return lambda values: Record(zip(names, values))


class Connection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, parameters=()):
        # Only application-owned SQL uses this adapter; values remain bound parameters.
        return self.connection.execute(query.replace("?", "%s"), parameters)


class PostgresTicketStore(TicketStore):
    def __init__(self, url):
        self.url = url

    @contextmanager
    def connection(self):
        import psycopg
        with psycopg.connect(self.url, row_factory=record_factory, connect_timeout=15) as connection:
            yield Connection(connection)

    def initialize(self):
        statements = [
            """CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL, text TEXT NOT NULL,
                result_json TEXT NOT NULL, requires_review INTEGER NOT NULL CHECK(requires_review IN (0,1)),
                department TEXT NOT NULL, priority TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS feedback (
                sequence BIGSERIAL PRIMARY KEY, id TEXT UNIQUE NOT NULL,
                ticket_id TEXT NOT NULL REFERENCES tickets(id), created_at TEXT NOT NULL,
                corrected_intent TEXT NOT NULL, corrected_category TEXT NOT NULL,
                corrected_priority TEXT, corrected_department TEXT, note TEXT NOT NULL,
                reviewer TEXT, training_status TEXT NOT NULL DEFAULT 'pending' CHECK(training_status='pending'))""",
            "CREATE INDEX IF NOT EXISTS feedback_ticket_idx ON feedback(ticket_id, sequence)",
            "CREATE INDEX IF NOT EXISTS ticket_created_idx ON tickets(created_at DESC, id DESC)",
        ]
        with self.connection() as connection:
            for statement in statements:
                connection.execute(statement)
