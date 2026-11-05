"""SQLite persistence with immutable prediction snapshots and feedback history."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class TicketStore:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    requires_review INTEGER NOT NULL CHECK(requires_review IN (0,1)),
                    department TEXT NOT NULL,
                    priority TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    id TEXT UNIQUE NOT NULL,
                    ticket_id TEXT NOT NULL REFERENCES tickets(id),
                    created_at TEXT NOT NULL,
                    corrected_intent TEXT NOT NULL,
                    corrected_category TEXT NOT NULL,
                    corrected_priority TEXT,
                    corrected_department TEXT,
                    note TEXT NOT NULL,
                    reviewer TEXT,
                    training_status TEXT NOT NULL DEFAULT 'pending' CHECK(training_status = 'pending')
                );
                CREATE INDEX IF NOT EXISTS feedback_ticket_idx ON feedback(ticket_id, sequence);
                CREATE INDEX IF NOT EXISTS ticket_created_idx ON tickets(created_at DESC, id DESC);
            """)

    @staticmethod
    def decode_ticket(row):
        return {"id": row["id"], "created_at": row["created_at"], "text": row["text"],
                "result": json.loads(row["result_json"]), "feedback_count": row["feedback_count"],
                "review_status": "reviewed" if row["feedback_count"] else "needs_review" if row["requires_review"] else "not_required"}

    @staticmethod
    def ticket_query():
        return "SELECT t.*, (SELECT COUNT(*) FROM feedback f WHERE f.ticket_id=t.id) AS feedback_count FROM tickets t"

    def create_ticket(self, text, result):
        ticket_id = str(uuid4())
        with self.connection() as connection:
            connection.execute("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticket_id, timestamp(), text, json.dumps(result, allow_nan=False), int(result["requires_review"]),
                 result["department"], result["priority"]))
        return self.get_ticket(ticket_id)

    def get_ticket(self, ticket_id):
        with self.connection() as connection:
            row = connection.execute(self.ticket_query() + " WHERE t.id=?", (str(ticket_id),)).fetchone()
        return self.decode_ticket(row) if row else None

    def list_tickets(self, limit=20, offset=0, needs_review=None, category=None, priority=None, search=None):
        clauses, parameters = [], []
        if needs_review is True:
            clauses.append("t.requires_review=1 AND NOT EXISTS (SELECT 1 FROM feedback f WHERE f.ticket_id=t.id)")
        elif needs_review is False:
            clauses.append("(t.requires_review=0 OR EXISTS (SELECT 1 FROM feedback f WHERE f.ticket_id=t.id))")
        if category:
            # Category is a deterministic mapping from the stored original intent.
            clauses.append("t.result_json LIKE ?")
            parameters.append('%"category": "' + category + '"%')
        if priority:
            clauses.append("t.priority=?")
            parameters.append(priority)
        if search:
            clauses.append("LOWER(t.text) LIKE ? ESCAPE '!' ")
            parameters.append('%' + search.lower().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%')
        where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
        with self.connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM tickets t" + where, tuple(parameters)).fetchone()[0]
            rows = connection.execute(self.ticket_query() + where + " ORDER BY t.created_at DESC, t.id DESC LIMIT ? OFFSET ?", tuple(parameters) + (limit, offset)).fetchall()
        return {"items": [self.decode_ticket(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def add_feedback(self, ticket_id, values):
        feedback_id = str(uuid4())
        with self.connection() as connection:
            if not connection.execute("SELECT 1 FROM tickets WHERE id=?", (str(ticket_id),)).fetchone():
                return None
            connection.execute("""INSERT INTO feedback
                (id,ticket_id,created_at,corrected_intent,corrected_category,corrected_priority,corrected_department,note,reviewer)
                VALUES (?,?,?,?,?,?,?,?,?)""", (feedback_id, str(ticket_id), timestamp(), values["corrected_intent"],
                values["corrected_category"], values.get("corrected_priority"), values.get("corrected_department"),
                values["note"], values.get("reviewer")))
            row = connection.execute("SELECT * FROM feedback WHERE id=?", (feedback_id,)).fetchone()
        return {key: row[key] for key in row.keys() if key != "sequence"}

    def list_feedback(self, ticket_id):
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM feedback WHERE ticket_id=? ORDER BY sequence", (str(ticket_id),)).fetchall()
        return [{key: row[key] for key in row.keys() if key != "sequence"} for row in rows]

    def analytics(self):
        with self.connection() as connection:
            total = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            reviewed = connection.execute("SELECT COUNT(DISTINCT ticket_id) FROM feedback").fetchone()[0]
            pending = connection.execute("SELECT COUNT(*) FROM tickets t WHERE requires_review=1 AND NOT EXISTS (SELECT 1 FROM feedback f WHERE f.ticket_id=t.id)").fetchone()[0]
            feedback = connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            departments = {row[0]: row[1] for row in connection.execute("SELECT department, COUNT(*) FROM tickets GROUP BY department")}
            priorities = {row[0]: row[1] for row in connection.execute("SELECT priority, COUNT(*) FROM tickets GROUP BY priority")}
            examples = connection.execute("SELECT t.result_json, t.priority, t.department, f.corrected_intent, f.corrected_priority, f.corrected_department, f.created_at FROM tickets t JOIN feedback f ON f.ticket_id=t.id WHERE f.sequence=(SELECT MAX(f2.sequence) FROM feedback f2 WHERE f2.ticket_id=t.id)").fetchall()
        corrected, intents, days = 0, {}, {}
        for row in examples:
            original = json.loads(row['result_json'])['prediction']['intent']
            changed = original != row['corrected_intent'] or (row['corrected_priority'] is not None and row['priority'] != row['corrected_priority']) or (row['corrected_department'] is not None and row['department'] != row['corrected_department'])
            corrected += int(changed)
            if original != row['corrected_intent']:
                intents[original] = intents.get(original, 0) + 1
            day = row['created_at'][:10]
            days.setdefault(day, {'reviewed': 0, 'corrected': 0})
            days[day]['reviewed'] += 1
            days[day]['corrected'] += int(changed)
        return {"tickets": total, "reviewed_tickets": reviewed, "pending_review": pending,
                "feedback_entries": feedback, "original_departments": departments, "original_priorities": priorities,
                "corrected_tickets": corrected, "correction_rate": corrected / reviewed if reviewed else 0,
                "corrected_intents": intents, "review_activity_by_day": days}
