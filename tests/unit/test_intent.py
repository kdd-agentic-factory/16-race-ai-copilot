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

    def test_part_design_intent_requires_approval(self):
        intent = classify_intent("Que pieza especifica podriamos disenar para mejorar la refrigeracion del freno delantero?")

        self.assertEqual(intent.name, "part_design")
        self.assertIn("skills.part_design", intent.tools)
        self.assertTrue(intent.approval_required)

    def test_spin_patterns_use_pattern_discovery(self):
        intent = classify_intent("Busca patrones de spin similares en sesiones anteriores")

        self.assertEqual(intent.name, "pattern_discovery")
        self.assertIn("patterns.search", intent.tools)
