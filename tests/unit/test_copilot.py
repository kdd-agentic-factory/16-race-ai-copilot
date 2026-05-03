import unittest

from app.copilot import build_chat_response, build_command_center_response
from app.schemas import RaceCommandCenterChatRequest


class CopilotTests(unittest.TestCase):
    def test_chat_response_does_not_fabricate_telemetry(self):
        response = build_chat_response("Resume las anomalías de la última sesión")

        self.assertEqual(response.evidence[0].confidence, 0.0)
        self.assertIn("No telemetry evidence has been fabricated", response.evidence[0].summary)

    def test_setup_response_requires_approval(self):
        response = build_chat_response("Que setup recomiendas para alta temperatura de pista?")

        self.assertEqual(response.approval_status, "required")
        self.assertTrue(response.recommendations[0].approval_required)

    def test_command_center_chat_declares_integration_route(self):
        response = build_command_center_response(
            RaceCommandCenterChatRequest(
                query="Genera un informe pre-GP para el circuito de Jerez.",
                active_session_id="jerez-fp2",
                circuit="Jerez",
            )
        )

        tools = [tool_call.tool for tool_call in response.tool_calls]
        self.assertEqual(tools[0], "race_command_center.context.read")
        self.assertIn("rag_cag.retrieve", tools)
        self.assertIn("mcp_gateway.dispatch", tools)
        self.assertIn("agent_orchestrator.plan", tools)
        self.assertEqual(response.evidence[0].source, "race-command-center:context")
