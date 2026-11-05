from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import create_app
from src.inference import Prediction
from src.routing import TicketService


class TestClassifier:
    mapping = {"track_refund": "REFUND"}
    version = "fixture:v1"

    def predict(self, text):
        return Prediction("track_refund", "REFUND", 0.99, 0.95, self.version)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "support.sqlite3"
        self.service = TicketService(TestClassifier())
        self.client = TestClient(create_app(self.db_path, self.service))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def create_ticket(self, text="Where is my refund?"):
        response = self.client.post("/tickets", json={"text": text})
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_health_taxonomy_and_prediction_without_persistence(self):
        self.assertEqual(self.client.get("/health").json()["model_version"], "fixture:v1")
        self.assertEqual(len(self.client.get("/taxonomy").json()["intents"]), 27)
        result = self.client.post("/predict", json={"text": "Where is my refund?"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["department"], "Finance")
        self.assertEqual(self.client.get("/analytics").json()["tickets"], 0)

    def test_ticket_persists_across_application_restart(self):
        ticket = self.create_ticket()
        self.assertEqual(self.client.get(f"/tickets/{ticket['id']}").json(), ticket)
        with TestClient(create_app(self.db_path, self.service)) as restarted:
            self.assertEqual(restarted.get(f"/tickets/{ticket['id']}").json(), ticket)
        with closing(sqlite3.connect(self.db_path)) as database:
            self.assertEqual(database.execute("SELECT COUNT(*) FROM tickets").fetchone()[0], 1)

    def test_feedback_is_append_only_and_original_prediction_unchanged(self):
        ticket = self.create_ticket("help")
        url = f"/tickets/{ticket['id']}/feedback"
        self.assertEqual(self.client.get("/tickets?needs_review=true").json()["total"], 1)
        for intent in ["get_refund", "track_refund"]:
            response = self.client.post(url, json={"corrected_intent": intent, "note": "Reviewed locally"})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["corrected_category"], "REFUND")
            self.assertEqual(response.json()["training_status"], "pending")
        history = self.client.get(url).json()
        self.assertEqual([item["corrected_intent"] for item in history], ["get_refund", "track_refund"])
        updated = self.client.get(f"/tickets/{ticket['id']}").json()
        self.assertEqual(updated["result"], ticket["result"])
        self.assertEqual(updated["feedback_count"], 2)
        self.assertEqual(updated["review_status"], "reviewed")
        self.assertEqual(self.client.get("/tickets?needs_review=true").json()["total"], 0)
        metrics = self.client.get("/analytics").json()
        self.assertEqual((metrics["reviewed_tickets"], metrics["feedback_entries"], metrics["pending_review"]), (1, 2, 0))

    def test_invalid_feedback_does_not_change_data(self):
        ticket = self.create_ticket()
        url = f"/tickets/{ticket['id']}/feedback"
        for body in [{"corrected_intent": "invented"}, {"corrected_intent": "get_refund", "corrected_department": "Invented team"},
                     {"corrected_intent": "get_refund", "corrected_priority": "Urgent"},
                     {"corrected_intent": "get_refund", "training_status": "approved"},
                     {"corrected_intent": "get_refund", "corrected_category": "ACCOUNT"}]:
            self.assertEqual(self.client.post(url, json=body).status_code, 422)
        self.assertEqual(self.client.get(url).json(), [])

    def test_invalid_ticket_bodies_do_not_persist_or_echo_text(self):
        for body in [{"text": "  "}, {"text": "x" * 10001}, {"text": "private-example", "unexpected": True}, {"text": 123}]:
            response = self.client.post("/tickets", json=body)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("private-example", response.text)
            self.assertTrue(all("input" not in item for item in response.json()["detail"]))
        self.assertEqual(self.client.get("/tickets").json()["total"], 0)

    def test_missing_ticket_and_invalid_pagination(self):
        ticket_id = str(uuid4())
        self.assertEqual(self.client.get(f"/tickets/{ticket_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/tickets/{ticket_id}/feedback").status_code, 404)
        self.assertEqual(self.client.post(f"/tickets/{ticket_id}/feedback", json={"corrected_intent": "get_refund"}).status_code, 404)
        self.assertEqual(self.client.get("/tickets/not-a-uuid").status_code, 422)
        self.assertEqual(self.client.get("/tickets?limit=101").status_code, 422)
        self.assertEqual(self.client.get("/tickets?offset=-1").status_code, 422)

    def test_pagination_and_review_filters(self):
        self.create_ticket()
        self.create_ticket("help")
        page = self.client.get("/tickets?limit=1&offset=1").json()
        self.assertEqual((page["total"], len(page["items"])), (2, 1))
        self.assertEqual(self.client.get("/tickets?needs_review=true").json()["total"], 1)
        self.assertEqual(self.client.get("/tickets?needs_review=false").json()["total"], 1)

    def test_sql_characters_in_ticket_and_feedback_are_data(self):
        text = "Where is my refund? '; DROP TABLE tickets; --"
        ticket = self.create_ticket(text)
        response = self.client.post(f"/tickets/{ticket['id']}/feedback", json={"corrected_intent": "get_refund", "note": "'; DROP TABLE feedback; --"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get("/tickets").json()["total"], 1)
        self.assertEqual(self.client.get(f"/tickets/{ticket['id']}").json()["text"], text)


if __name__ == "__main__":
    unittest.main()
