from pathlib import Path
import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class CommunityFullTests(unittest.TestCase):
    def test_missing_secrets_do_not_start_a_backend(self):
        with patch('app.community_backend.start_backend') as start:
            app = AppTest.from_file(str(ROOT / 'community_full/streamlit_app.py'))
            app.secrets = {}
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            start.assert_not_called()

    def test_model_does_not_load_before_login(self):
        with patch.dict(os.environ, {}), patch('app.community_backend.start_backend') as start:
            app = AppTest.from_file(str(ROOT / 'community_full/streamlit_app.py'))
            app.secrets = {'DATABASE_URL': 'postgresql://example.invalid/db', 'SUPPORT_API_KEY': 'a' * 40,
                           'SUPPORT_DASHBOARD_PASSWORD': 'verification-password',
                           'MODEL_BUNDLE_URL': 'https://example.invalid/model.zip', 'MODEL_BUNDLE_SHA256': 'a' * 64}
            app.run(timeout=20)
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input[0].label, 'Workspace password')
            start.assert_not_called()
