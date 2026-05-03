import unittest

from app.intent import classify_intent


class IntentTests(unittest.TestCase):
    def test_setup_intent_requires_orchestrator_approval_tool(self):
        intent = classify_intent("Que evidencia tenemos para cambiar dos clicks el rebote trasero?")

        self.assertEqual(intent.name, "setup_recommendation")
        self.assertIn("orchestrator.approval", intent.tools)
        self.assertTrue(intent.approval_required)

    def test_telemetry_intent_for_fp_delta(self):
        intent = classify_intent("Que ha cambiado entre FP1 y FP2 en la curva 5?")

        self.assertEqual(intent.name, "telemetry_analysis")
        self.assertIn("telemetry.compare", intent.tools)
