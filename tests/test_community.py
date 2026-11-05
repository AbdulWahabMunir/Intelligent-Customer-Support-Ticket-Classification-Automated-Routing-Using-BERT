import os
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class CommunityTests(unittest.TestCase):
    def test_missing_secrets_fail_without_starting_dashboard(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'community/streamlit_app.py'))
        app.secrets = {}
        app.run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(app.error)

    def test_complete_secrets_show_login_before_api_access(self):
        with patch.dict(os.environ, {}, clear=False):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'community/streamlit_app.py'))
            app.secrets = {'SUPPORT_API_URL': 'https://example.invalid', 'SUPPORT_API_KEY': 'a' * 40,
                           'SUPPORT_DASHBOARD_PASSWORD': 'verification-password'}
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.title[0].value, 'Support Desk')
            self.assertEqual(app.text_input[0].label, 'Workspace password')

    def test_public_runner_refuses_ephemeral_storage(self):
        from app.run_api import main
        with patch.dict(os.environ, {'SUPPORT_API_KEY': 'a' * 40, 'DATABASE_URL': ''}):
            with self.assertRaisesRegex(ValueError, 'external PostgreSQL'):
                main()
