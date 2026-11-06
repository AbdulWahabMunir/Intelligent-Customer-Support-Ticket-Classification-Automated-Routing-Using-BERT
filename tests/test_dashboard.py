from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from app.api import create_app
from app.client import APIError
from src.data.inspect import ROOT
from src.inference import Prediction
from src.routing import TicketService


class DashboardClassifier:
    mapping = {"track_refund": "REFUND"}
    version = "dashboard-fixture:v1"

    def predict(self, text):
        return Prediction("track_refund", "REFUND", 0.99, 0.9, self.version)


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.client = TestClient(create_app(Path(self.directory.name) / "dashboard.sqlite3", TicketService(DashboardClassifier())))
        self.client.__enter__()
        client = self.client

        def request(instance, method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.status_code >= 400:
                raise APIError("Request failed")
            return response.json()

        self.transport = patch("app.client.SupportAPI.request", new=request)
        self.transport.start()
        self.app = AppTest.from_file(str(ROOT / "app/dashboard.py"), default_timeout=20)

    def tearDown(self):
        self.transport.stop()
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def test_empty_overview_and_first_ticket_navigation(self):
        app = self.app.run()
        self.assertFalse(app.exception)
        self.assertEqual([metric.value for metric in app.metric], ["0", "0", "0", "0"])
        click(app, "Create your first ticket")
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "New support ticket")

    def test_submit_review_and_preserve_original_prediction(self):
        app = self.app.run()
        app.radio(key="navigation").set_value("New ticket").run()
        app.text_area(key="ticket_text").set_value("help")
        click(app, "Classify and save ticket")
        self.assertFalse(app.exception)
        ticket = self.client.get("/tickets").json()["items"][0]
        original = ticket["result"]
        self.assertTrue(original["requires_review"])
        click(app, "Open ticket review")
        self.assertFalse(app.exception)
        app.selectbox(key=f"intent_{ticket['id']}").set_value("get_refund")
        app.text_area(key=f"note_{ticket['id']}").set_value("Customer is requesting a new refund")
        click(app, "Save review")
        self.assertFalse(app.exception)
        self.assertTrue(any("Review saved" in item.value for item in app.success))
        history = self.client.get(f"/tickets/{ticket['id']}/feedback").json()
        self.assertEqual(history[0]["corrected_intent"], "get_refund")
        self.assertEqual(history[0]["training_status"], "pending")
        self.assertEqual(self.client.get(f"/tickets/{ticket['id']}").json()["result"], original)
        app.selectbox(key="review_filter").set_value("Awaiting review").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No tickets" in item.value for item in app.info))

    def test_blank_submission_does_not_save(self):
        app = self.app.run()
        app.radio(key="navigation").set_value("New ticket").run()
        app.text_area(key="ticket_text").set_value("  ")
        click(app, "Classify and save ticket")
        self.assertFalse(app.exception)
        self.assertTrue(any("Enter a customer message" in item.value for item in app.error))
        self.assertEqual(self.client.get("/tickets").json()["total"], 0)

    def test_category_priority_and_search_widgets(self):
        self.client.post('/tickets', json={'text': 'Track my refund please'})
        self.client.post('/tickets', json={'text': 'URGENT track my refund please'})
        app = self.app.run()
        app.radio(key='navigation').set_value('Ticket review').run()
        app.selectbox(key='review_filter').set_value('All tickets').run()
        app.selectbox(key='category_filter').set_value('REFUND').run()
        app.selectbox(key='priority_filter').set_value('High').run()
        app.text_input(key='ticket_search').set_value('URGENT').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('1 matching tickets' in item.value for item in app.caption))

    def test_overview_charts_show_persisted_data(self):
        self.client.post("/tickets", json={"text": "Where is my refund?"})
        app = self.app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "1")
        self.assertTrue(any(item.value == "Recent tickets" for item in app.subheader))
        app.text_input(key="overview_search").set_value("Finance").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("1 of 1" in item.value for item in app.caption))
        app.text_input(key="overview_search").set_value("no-such-ticket").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("No tickets to display" in item.value for item in app.info))

    def test_api_failure_renders_actionable_error(self):
        with patch("app.client.SupportAPI.health", side_effect=APIError("Cannot reach the support API")):
            app = self.app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Cannot reach" in item.value for item in app.error))

    def test_hosted_password_gate_hides_workspace_until_authenticated(self):
        with patch.dict(os.environ, {"SUPPORT_DASHBOARD_PASSWORD": "test-only-long-password"}):
            app = self.app.run()
            self.assertFalse(app.exception)
            self.assertFalse(app.metric)
            app.text_input(key="access_password").set_value("incorrect")
            click(app, "Sign in")
            self.assertTrue(any("Password not recognized" in item.value for item in app.error))
            app.text_input(key="access_password").set_value("test-only-long-password")
            click(app, "Sign in")
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value, "0")


if __name__ == "__main__":
    unittest.main()
