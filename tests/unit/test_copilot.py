import unittest

from app.copilot import build_chat_response


class CopilotTests(unittest.TestCase):
    def test_chat_response_does_not_fabricate_telemetry(self):
        response = build_chat_response("Resume las anomalías de la última sesión")

        self.assertEqual(response.evidence[0].confidence, 0.0)
        self.assertIn("No telemetry evidence has been fabricated", response.evidence[0].summary)

    def test_setup_response_requires_approval(self):
        response = build_chat_response("Que setup recomiendas para alta temperatura de pista?")

        self.assertEqual(response.approval_status, "required")
        self.assertTrue(response.recommendations[0].approval_required)
